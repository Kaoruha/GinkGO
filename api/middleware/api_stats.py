"""
API 请求统计中间件（内存聚合，开发环境）

记录每个请求的状态码与响应时间，按日/月窗口聚合供 /api-stats 端点读取。
进程内计数，不落库（与 rate_limit.py 同属「开发环境」内存模式），重启归零。
"""
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware


class ApiStatsCollector:
    """进程内 API 请求统计聚合器（按当日/当月窗口）。"""

    def __init__(self):
        self.reset()

    def reset(self):
        """归零统计（也用于测试 + 跨日/跨月重置）。"""
        now = datetime.now(timezone.utc)
        self._today_key = now.strftime("%Y-%m-%d")
        self._month_key = now.strftime("%Y-%m")
        self._today_calls = 0
        self._month_calls = 0
        self._success_count = 0
        self._total_calls = 0
        self._total_response_time = 0.0
        self._response_time_count = 0

    def _rollover_if_needed(self):
        """跨日/跨月时重置对应窗口（惰性检查，读/写时都调用）。"""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        month = now.strftime("%Y-%m")
        if today != self._today_key:
            self._today_key = today
            self._today_calls = 0
        if month != self._month_key:
            self._month_key = month
            self._month_calls = 0

    def record(self, status_code: int, response_time_ms: float) -> None:
        """记录一次请求：计数 + 状态码分类 + 响应时间累加。"""
        self._rollover_if_needed()
        self._today_calls += 1
        self._month_calls += 1
        self._total_calls += 1
        if 200 <= status_code < 300:
            self._success_count += 1
        self._total_response_time += response_time_ms
        self._response_time_count += 1

    def get_stats(self) -> dict:
        """返回当前聚合统计（与 APIStats 模型字段对齐）。"""
        self._rollover_if_needed()
        success_rate = (
            self._success_count / self._total_calls * 100
            if self._total_calls
            else 0.0
        )
        avg_response_time = (
            self._total_response_time / self._response_time_count
            if self._response_time_count
            else 0.0
        )
        return {
            "today_calls": self._today_calls,
            "month_calls": self._month_calls,
            "success_rate": round(success_rate, 1),
            "avg_response_time": round(avg_response_time, 1),
        }


# 模块级单例：中间件 record / 端点 get_stats 共享同一实例。
collector = ApiStatsCollector()


class ApiStatsMiddleware(BaseHTTPMiddleware):
    """记录每个请求的状态码 + 响应时间到 ApiStatsCollector。"""

    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed_ms = (time.time() - start) * 1000
        try:
            collector.record(response.status_code, elapsed_ms)
        except Exception:
            # 统计失败不得影响请求本身
            pass
        return response
