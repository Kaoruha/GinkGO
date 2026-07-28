"""
RedisService function-cache 回归测试(纯 mock,不依赖 Redis 连接)。

覆盖 set/get/get_stats function-cache 链路。核心回归点:
get_function_cache 旧实现 ``json.loads(crud.get 返回的 dict)`` —— crud.get 已
CacheMapper.decode 返回 dict,二次 json.loads(dict) 抛 TypeError 被外层 except 吞成
None,导致**缓存命中也返 None**(function-cache 形同虚设)。修复后直接用 dict。

性能: 单进程 mock,无 DB/Redis IO。
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.redis_service import RedisService  # noqa: E402


@pytest.fixture
def fc_service():
    """RedisService 注入 mock crud_repo(模拟 RedisCRUD.get 已 decode 返 dict 的行为)。"""
    crud = MagicMock()
    crud.set.return_value = True
    service = RedisService(redis_crud=crud)
    return service, crud


class TestFunctionCacheRoundTrip:
    """function-cache set/get/stats 回归(ADR-025 ④;修二次 json.loads bug)。"""

    @pytest.mark.unit
    def test_get_function_cache_hit_returns_result(self, fc_service):
        """命中路径必须返回真实 result,而非 None。

        旧代码:crud.get 返 dict → json.loads(dict) 抛 TypeError → except 吞 None。
        本断言在旧代码下 FAIL(get_function_cache 返 None ≠ {"value": 42}),即 bug 铁证。
        """
        service, crud = fc_service
        crud.get.return_value = {
            "result": {"value": 42},
            "timestamp": 1.0,
            "func_name": "fn",
        }

        val = service.get_function_cache("fn", "key")

        assert val == {"value": 42}, "命中缓存应返回 result,旧二次 json.loads bug 会返 None"

    @pytest.mark.unit
    def test_get_function_cache_miss_returns_none(self, fc_service):
        """未命中(crud.get 返 None)应返 None。"""
        service, crud = fc_service
        crud.get.return_value = None

        assert service.get_function_cache("fn", "key") is None

    @pytest.mark.unit
    def test_set_then_get_round_trip_complex_result(self, fc_service):
        """set 存复杂 result(datetime 经 default=str 兜底)→ crud.get decode → get 取回。

        验证 set 的 default=str 兜底链路 + get 不二次 loads。
        """
        service, crud = fc_service
        result = {"ts": datetime(2026, 7, 28, 10, 0), "n": 7}

        ok = service.set_function_cache("fn", "key", result=result, expiration_seconds=60)
        assert ok is True
        assert crud.set.called

        # crud.set 收到的是 json str(default=str 序列化);模拟 crud.get 读回(decode 成 dict)
        stored_json = crud.set.call_args[0][1]
        assert isinstance(stored_json, str), "set 应以 str 交 crud.set(default=str 兜底)"
        crud.get.return_value = json.loads(stored_json)  # RedisCRUD.get 已 decode

        val = service.get_function_cache("fn", "key")
        assert val is not None, "round-trip 取回不应为 None"
        assert val["n"] == 7

    @pytest.mark.unit
    def test_get_function_cache_stats_no_typeerror(self, fc_service):
        """stats 遍历缓存条目不得因二次 json.loads 抛 TypeError(旧 bug 同源)。

        旧代码:crud.get 返 dict → json.loads(dict) TypeError → 内层 except continue,
        stats 全空。修复后应正确聚合。
        """
        service, crud = fc_service
        crud.keys.return_value = ["k1", "k2"]
        crud.get.side_effect = [
            {"result": 1, "timestamp": 100.0, "func_name": "fn_a"},
            {"result": 2, "timestamp": 200.0, "func_name": "fn_a"},
        ]

        stats = service.get_function_cache_stats()

        assert stats["total_entries"] == 2
        assert stats["by_function"]["fn_a"]["count"] == 2
        assert stats["oldest_entry"] == 100.0
        assert stats["newest_entry"] == 200.0
