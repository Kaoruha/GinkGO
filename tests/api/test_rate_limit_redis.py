"""#5466: Rate limit 中间件 Redis 持久化 + 内存 fallback 测试。

AC:
1. 计数入 Redis（Redis 路径下内存 dict 保持空）
2. 重启留存（新实例共享 Redis 计数）
3. 多进程一致（多实例共享同一 Redis）
4. Redis 不可用时 fallback 内存（请求处理不中断）
"""
import asyncio

import pytest


class _FakeRedis:
    """最小 in-memory Redis，仅实现 ZSET 滑动窗口所需命令。"""

    def __init__(self):
        self._zsets = {}  # key -> {member: score}

    async def zremrangebyscore(self, key, min_score, max_score):
        s = self._zsets.setdefault(key, {})
        for m in [m for m, v in s.items() if min_score <= v <= max_score]:
            del s[m]

    async def zcard(self, key):
        return len(self._zsets.get(key, {}))

    async def zadd(self, key, mapping):
        self._zsets.setdefault(key, {}).update(mapping)

    async def expire(self, key, ttl):
        return True


def _make_middleware(max_requests=3, window_seconds=60):
    from middleware.rate_limit import RateLimitMiddleware
    return RateLimitMiddleware(app=None, max_requests=max_requests, window_seconds=window_seconds)


def test_fallback_to_in_memory_when_redis_unavailable(monkeypatch):
    """AC4: Redis 不可用时，fallback 到内存，限流仍生效且不中断。"""
    import middleware.rate_limit as rl

    async def _boom():
        raise ConnectionError("Redis down")

    monkeypatch.setattr(rl, "get_redis", _boom)
    mw = _make_middleware(max_requests=3, window_seconds=60)

    # 3 次放行，第 4 次限流 —— 全走内存 fallback，无异常抛出
    results = [asyncio.run(mw.check_and_record("10.0.0.1")) for _ in range(4)]
    assert results == [False, False, False, True]


def test_redis_path_limits_and_dict_stays_empty(monkeypatch):
    """AC1: Redis 路径下限流生效，且进程内 dict 保持空（证明用了 Redis）。"""
    import middleware.rate_limit as rl

    fake = _FakeRedis()
    monkeypatch.setattr(rl, "get_redis", _async_value(fake))
    mw = _make_middleware(max_requests=3, window_seconds=60)

    results = [asyncio.run(mw.check_and_record("10.0.0.2")) for _ in range(4)]
    assert results == [False, False, False, True]
    # 关键判别：Redis 被使用，内存 dict 不应累积
    assert mw.requests == {}


def test_redis_counters_shared_across_instances(monkeypatch):
    """AC2+AC3: 新实例（重启/多进程）共享 Redis 计数 → 立即触发限流。"""
    import middleware.rate_limit as rl

    shared_fake = _FakeRedis()
    monkeypatch.setattr(rl, "get_redis", _async_value(shared_fake))

    mw1 = _make_middleware(max_requests=3, window_seconds=60)
    # 实例 1 耗尽配额
    [asyncio.run(mw1.check_and_record("10.0.0.3")) for _ in range(3)]

    # 实例 2 模拟「重启 / 另一进程」，共享同一 Redis
    mw2 = _make_middleware(max_requests=3, window_seconds=60)
    limited = asyncio.run(mw2.check_and_record("10.0.0.3"))
    assert limited is True
    assert mw2.requests == {}


def _async_value(value):
    async def _ret():
        return value
    return _ret
