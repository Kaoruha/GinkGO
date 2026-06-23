"""
请求限流中间件
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import os
import time
import uuid

from core.logging import logger
from core.redis_client import get_redis

# Issue #3847: 防止 IP 记录无限累积
_MAX_IPS = 10000
_FULL_CLEANUP_INTERVAL = 1000


def _load_trusted_proxies() -> set:
    """#5475: 从 TRUSTED_PROXIES 环境变量加载可信反向代理 IP（逗号分隔）。

    部署在 nginx/反向代理后时配置，例如 TRUSTED_PROXIES=10.0.0.1,10.0.0.2。
    空（默认）= fail-closed，不信任任何 X-Forwarded-For，只用 TCP 直连 IP。
    """
    raw = os.environ.get("TRUSTED_PROXIES", "")
    return {p.strip() for p in raw.split(",") if p.strip()}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """请求限流中间件。

    计数优先存 Redis（滑动窗口 ZSET），实现跨重启/多进程一致的限流；
    Redis 不可用时 fallback 回进程内 dict（开发环境），请求处理永不中断。
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        trusted_proxies=None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
        self._request_count = 0
        # #5475: 仅直连 IP 属于此集合时才采信 X-Forwarded-For（防伪造绕过限流）。
        # 默认从 TRUSTED_PROXIES 环境变量读；显式传入（测试）优先。
        if trusted_proxies is None:
            trusted_proxies = _load_trusted_proxies()
        self.trusted_proxies = set(trusted_proxies)

    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)

        if await self.check_and_record(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests"
            )

        # _full_cleanup 仅作用于 fallback 内存 dict（Redis 路径下 dict 恒空）
        self._request_count += 1
        if self._request_count % _FULL_CLEANUP_INTERVAL == 0:
            self._full_cleanup()

        return await call_next(request)

    async def check_and_record(self, client_ip: str) -> bool:
        """检查并记录请求。返回 True 表示该请求应被限流。

        优先 Redis（持久化 + 多进程一致），任何 Redis 异常 fallback 回内存。
        fallback 路径复用既有同步 is_rate_limited/record_request/_cleanup_current_ip。
        """
        redis_result = await self._redis_check_and_record(client_ip)
        if redis_result is not None:
            return redis_result
        # Redis 不可用 → 内存 fallback（AC4 + 热路径安全网）
        if self.is_rate_limited(client_ip):
            return True
        self.record_request(client_ip)
        self._cleanup_current_ip(client_ip)
        return False

    async def _redis_check_and_record(self, client_ip: str) -> Optional[bool]:
        """Redis 滑动窗口检查 + 记录。

        返回值：True=限流 / False=放行（已记录）/ None=Redis 不可用（调用方 fallback）。
        语义对齐内存版：先查窗口内既有请求数，达阈值则限流且不记录本次；
        否则记录本次（唯一 member 防 ZADD 覆盖）。
        """
        try:
            redis = await get_redis()
        except Exception as e:
            logger.warning(f"Rate limit Redis unavailable, fallback to in-memory: {e}")
            return None

        key = f"ratelimit:{client_ip}"
        now = time.time()
        window_start = now - self.window_seconds
        try:
            # 清窗口外 → 数窗口内 → 不足阈值才记录本次
            await redis.zremrangebyscore(key, 0, window_start)
            count = await redis.zcard(key)
            if count >= self.max_requests:
                return True
            await redis.zadd(key, {uuid.uuid4().hex: now})
            await redis.expire(key, self.window_seconds + 1)
            return False
        except Exception as e:
            logger.warning(f"Rate limit Redis op failed, fallback to in-memory: {e}")
            return None

    def get_client_ip(self, request: Request) -> str:
        # #5475: 先取 TCP 直连 IP，仅当它来自可信反向代理时才采信 XFF/X-Real-IP
        # 头（这些头可被任意客户端伪造）；否则用直连 IP（fail-closed，不可伪造）。
        direct_ip = request.client.host if request.client else None
        if direct_ip and direct_ip in self.trusted_proxies:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0].strip()
            real_ip = request.headers.get("X-Real-IP")
            if real_ip:
                return real_ip.strip()
        if direct_ip:
            return direct_ip
        return "unknown"

    def is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        records = self.requests.get(client_ip)
        if not records:
            return False
        return sum(1 for ts in records if ts > window_start) >= self.max_requests

    def record_request(self, client_ip: str):
        if client_ip not in self.requests:
            if len(self.requests) >= _MAX_IPS:
                self._full_cleanup()
            self.requests[client_ip] = []
        self.requests[client_ip].append(time.time())

    def _cleanup_current_ip(self, client_ip: str):
        """清理当前 IP 的过期记录"""
        records = self.requests.get(client_ip)
        if not records:
            return
        window_start = time.time() - self.window_seconds
        self.requests[client_ip] = [ts for ts in records if ts > window_start]
        if not self.requests[client_ip]:
            del self.requests[client_ip]

    def _full_cleanup(self):
        """全量清理所有 IP 的过期记录"""
        now = time.time()
        window_start = now - self.window_seconds
        expired = [
            ip for ip, records in self.requests.items()
            if not any(ts > window_start for ts in records)
        ]
        for ip in expired:
            del self.requests[ip]
