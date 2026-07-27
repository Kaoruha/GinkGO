"""
RedisService function_cache 回归测试（ADR-025 §4 Redis 收尾）。

回归背景：
  crud.get 已走 CacheMapper.decode 把 wire 还原成 dict；旧 get_function_cache /
  get_function_cache_stats 再对该 dict 执行 json.loads → TypeError，被外层 except
  吞成「命中路径 return None / WARN+continue」→ function_cache 命中即静默失效。

本文件以纯 mock（不依赖真实 Redis 连接）验证修复后命中路径正常返回 result / 正常计数。

Run: pytest tests/unit/data/services/test_redis_function_cache.py -v -o "addopts="
"""
from unittest.mock import MagicMock

import pytest

from ginkgo.data.services.redis_service import RedisService


def _make_service():
    """绕 __init__（避免 Redis 连接握手），注入 mock crud_repo + logger。"""
    svc = RedisService.__new__(RedisService)
    svc._crud_repo = MagicMock()
    svc._logger = MagicMock()
    return svc


@pytest.mark.unit
class TestFunctionCacheDoubleJsonLoadsRegression:
    """回归：crud.get 返 dict 后不得再 json.loads（二次解码 TypeError 静默吞）。"""

    def test_get_function_cache_returns_result_when_crud_get_is_dict(self):
        """命中路径：crud.get 返 dict（已 decode）→ 返 result，不抛 TypeError、不返 None。"""
        svc = _make_service()
        svc._crud_repo.get.return_value = {
            "result": {"alpha": 1.5},
            "func_name": "f",
            "timestamp": 1700000000.0,
        }

        got = svc.get_function_cache("f", "k")

        # 修复前恒 None：json.loads(dict) 抛 TypeError → except → return None
        assert got == {"alpha": 1.5}

    def test_get_function_cache_miss_returns_none(self):
        """未命中：crud.get 返 None → 返 None（行为守卫，不受 bug 影响）。"""
        svc = _make_service()
        svc._crud_repo.get.return_value = None

        assert svc.get_function_cache("f", "k") is None

    def test_get_function_cache_stats_counts_when_crud_get_is_dict(self):
        """stats 命中路径：crud.get 返 dict → 正常计数，不 WARN+continue。"""
        svc = _make_service()
        svc._crud_repo.keys.return_value = ["k1"]
        svc._crud_repo.get.return_value = {
            "result": {"x": 1},
            "func_name": "f",
            "timestamp": 1700000000.0,
        }

        stats = svc.get_function_cache_stats()

        assert stats["total_entries"] == 1
        assert stats["by_function"]["f"]["count"] == 1
        assert stats["by_function"]["f"]["size_estimate"] > 0
        # 修复前：json.loads(dict) → 内层 except WARN+continue → by_function 恒空
        assert svc._logger.WARN.call_count == 0
