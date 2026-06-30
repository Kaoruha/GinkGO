"""TDD tests for cache_with_expiration: per-function isolation, LRU, configurable size.

目标：修复 #3863 — 全局共享 OrderedDict + FIFO 驱逐 + 无参分支内存泄漏。
"""
import time

import pytest

from ginkgo.libs.utils.common import cache_with_expiration


def test_max_cache_size_configurable():
    """max_cache_size 可配置：超出时驱逐最旧条目（行为：miss 后重新计算）。"""
    call_count = [0]

    @cache_with_expiration(expiration_seconds=60, max_cache_size=2)
    def func(x):
        call_count[0] += 1
        return x * 2

    func(1)  # cache: [1], calls=1
    func(2)  # cache: [1,2], calls=2
    func(3)  # cache: [2,3] (1 被驱逐), calls=3

    # func(1) 被驱逐，重新调用应 miss → 重新计算
    func(1)
    assert call_count[0] == 4, "max_cache_size=2 应在 3 个不同 key 后驱逐最旧条目"


def test_per_function_isolated_cache():
    """每个被装饰函数有独立缓存：A 的大量调用不应驱逐 B 的条目。"""
    calls_b = [0]

    @cache_with_expiration(expiration_seconds=60, max_cache_size=3)
    def func_a(x):
        return x

    @cache_with_expiration(expiration_seconds=60, max_cache_size=3)
    def func_b(x):
        calls_b[0] += 1
        return x * 10

    func_b(1)  # B 插入，calls_b=1
    # A 用大量不同 key 填满；全局共享时会把 B 的条目挤掉
    for i in range(100):
        func_a(i)

    func_b(1)  # 独立缓存 → hit (calls_b=1)；全局共享 → miss (calls_b=2)
    assert calls_b[0] == 1, "func_a 的缓存驱逐了 func_b 的条目（全局共享 cache_data bug）"


def test_lru_eviction_keeps_recently_accessed():
    """LRU：缓存满时驱逐最久未访问的条目（非最旧插入项）。"""
    calls = {}

    @cache_with_expiration(expiration_seconds=60, max_cache_size=2)
    def func(x):
        calls[x] = calls.get(x, 0) + 1
        return x

    func(1)  # 插入 1
    func(2)  # 插入 2，满
    func(1)  # 命中 1（LRU 应提升其优先级）
    func(3)  # 插入 3，满 → LRU 驱逐最久未访问的 key=2；FIFO 会驱逐 key=1

    # key=1 被访问过应保留（必须在 key=2 重插干扰前验证）
    before1 = calls.get(1, 0)
    func(1)
    assert calls.get(1, 0) == before1, "key=1 被访问过应保留（LRU），却被驱逐（FIFO）"

    # key=2 应已被 LRU 驱逐 → miss
    before2 = calls.get(2, 0)
    func(2)
    assert calls.get(2, 0) == before2 + 1, "key=2 应被 LRU 驱逐，但命中了（FIFO 未升级为 LRU）"


def test_paramless_decorator_evicts_on_overflow():
    """无参 @cache_with_expiration 也应有 max_cache_size 驱逐（默认 64），不无限增长（#3863 内存泄漏）。"""
    calls = [0]

    @cache_with_expiration  # 无参直接装饰（base_feeder.py:56 等在用）
    def func(x):
        calls[0] += 1
        return x

    for i in range(100):  # 不同 key，默认 max_cache_size=64
        func(i)
    # 100 次不同 key → 每次 miss → calls=100

    func(0)  # 无驱逐 → hit(100)；有驱逐 → key=0 已被驱逐 → miss(101)
    assert calls[0] == 101, "无参分支未驱逐旧条目（默认 max_cache_size=64），key=0 应已被驱逐（内存泄漏）"
