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
