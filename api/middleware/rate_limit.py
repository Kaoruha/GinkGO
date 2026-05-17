"""
请求限流中间件
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict
import time

from core.logging import logger

# Issue #3847: 防止 IP 记录无限累积
_MAX_IPS = 10000
_FULL_CLEANUP_INTERVAL = 1000


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于内存的请求限流中间件（开发环境）"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
        self._request_count = 0

    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)

        if self.is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests"
            )

        self.record_request(client_ip)
        self._cleanup_current_ip(client_ip)

        self._request_count += 1
        if self._request_count % _FULL_CLEANUP_INTERVAL == 0:
            self._full_cleanup()

        return await call_next(request)

    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

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
