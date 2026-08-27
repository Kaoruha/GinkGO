"""Smoke tests for livecore.utils -- #3870"""
import pytest
from unittest.mock import MagicMock

try:
    from ginkgo.livecore.utils.decorators import safe_job_wrapper
    HAS_DECORATORS = True
except ImportError:
    HAS_DECORATORS = False

try:
    from ginkgo.livecore.utils.heartbeat import HeartbeatMixin
    HAS_HEARTBEAT = True
except ImportError:
    HAS_HEARTBEAT = False


@pytest.mark.skipif(not HAS_DECORATORS, reason="decorators not available")
class TestSafeJobWrapper:
    def test_success(self):
        @safe_job_wrapper
        def good_func():
            return 42
        result = good_func()
        assert result == 42

    def test_catches_exception(self):
        @safe_job_wrapper
        def bad_func():
            raise ValueError("test error")
        # Should not raise, just log
        result = bad_func()
        # Returns None on failure (or the function returns nothing)

    # ===== 口径细化：job 返回 dict 时按内容判定 status 并存档 result 列 =====

    def _make_owner(self):
        """构造带 _record_trigger/_complete_record 的宿主，捕获记录调用"""

        class Owner:
            def __init__(self):
                self.calls = []

            def _record_trigger(self, name):
                return "uuid-1"

            def _complete_record(self, uuid, status, duration_ms=0, error=None, result=None):
                self.calls.append(
                    {"uuid": uuid, "status": status, "error": error, "result": result}
                )

        return Owner()

    def test_dict_result_ok_false_records_failed_with_result(self):
        """job 返回 {"ok": False} 应记 failed 并存档 result/error（模拟内部吞异常后上报）"""
        owner = self._make_owner()

        @safe_job_wrapper
        def swallowed_fail(self):
            # 模拟 job 内部吞掉异常后按结果上报（首参 self 与真实 job 一致）
            return {"ok": False, "sent": 3, "total": 100, "error": "kafka down"}

        result = swallowed_fail(owner)
        assert result == {"ok": False, "sent": 3, "total": 100, "error": "kafka down"}
        assert len(owner.calls) == 1
        call = owner.calls[0]
        assert call["status"] == "failed"
        assert call["error"] == "kafka down"
        assert call["result"]["total"] == 100

    def test_dict_result_ok_true_records_success_with_result(self):
        """派发数量等明细随 success 一起写入 result 列"""
        owner = self._make_owner()

        @safe_job_wrapper
        def dispatched_ok(self):
            return {"ok": True, "sent": 5000, "total": 5000}

        dispatched_ok(owner)
        assert len(owner.calls) == 1
        call = owner.calls[0]
        assert call["status"] == "success"
        assert call["error"] is None
        assert call["result"]["sent"] == 5000

    def test_none_return_still_success(self):
        """不返回 dict 的 job 保持旧行为：未抛异常即 success，无 result 存档"""
        owner = self._make_owner()

        @safe_job_wrapper
        def plain_job(self):
            pass

        plain_job(owner)
        assert len(owner.calls) == 1
        assert owner.calls[0]["status"] == "success"
        assert owner.calls[0]["result"] is None


@pytest.mark.skipif(not HAS_HEARTBEAT, reason="HeartbeatMixin not available")
class TestHeartbeatMixin:
    def test_is_abstract(self):
        from abc import ABC
        assert issubclass(HeartbeatMixin, ABC)

    def test_requires_abstract_methods(self):
        # Must implement _get_component_name, _get_heartbeat_key, _get_redis_client, _is_running
        with pytest.raises(TypeError):
            HeartbeatMixin()

    def test_concrete_subclass(self):
        class TestComponent(HeartbeatMixin):
            def _get_component_name(self):
                return "test_component"
            def _get_heartbeat_key(self):
                return "heartbeat:test"
            def _get_redis_client(self):
                return None
            def _is_running(self):
                return False

        comp = TestComponent()
        assert comp._get_component_name() == "test_component"
        assert comp._is_running() is False
        details = comp._get_heartbeat_details()
        assert isinstance(details, dict)
