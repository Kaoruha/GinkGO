"""
请求限流中间件
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict
from collections import defaultdict
import time

from core.logging import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于内存的请求限流中间件（开发环境）"""

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # 存储每个IP的请求记录 {ip: [(timestamp, count), ...]}
        self.requests: Dict[str, list] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # 获取客户端IP
        client_ip = self.get_client_ip(request)

        # 检查是否超过限制
        if self.is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests"
            )

        # 记录请求
        self.record_request(client_ip)

        # 清理过期记录
        self.cleanup_old_requests()

        return await call_next(request)

    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 尝试从 X-Forwarded-For 获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        # 尝试从 X-Real-IP 获取
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用客户端地址
        if request.client:
            return request.client.host

        return "unknown"

    def is_rate_limited(self, client_ip: str) -> bool:
        """检查是否超过限流"""
        now = time.time()
        window_start = now - self.window_seconds

        # 获取时间窗口内的请求数
        requests_in_window = [
            ts for ts in self.requests[client_ip]
            if ts > window_start
        ]

        return len(requests_in_window) >= self.max_requests

    def record_request(self, client_ip: str):
        """记录请求"""
        self.requests[client_ip].append(time.time())

    def cleanup_old_requests(self):
        """清理过期请求记录"""
        now = time.time()
        window_start = now - self.window_seconds

        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                ts for ts in self.requests[ip]
                if ts > window_start
            ]

            # 如果没有记录了，删除该IP
            if not self.requests[ip]:
                del self.requests[ip]
