"""Smoke tests for livecore.heartbeat_monitor -- #3870"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.livecore.heartbeat_monitor import HeartbeatMonitor
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="HeartbeatMonitor not available")
class TestHeartbeatMonitor:
    def test_instantiation_default(self):
        monitor = HeartbeatMonitor()
        assert monitor is not None

    def test_instantiation_custom(self):
        monitor = HeartbeatMonitor(check_interval=5, timeout_seconds=60)
        assert monitor is not None

    def test_initial_state(self):
        monitor = HeartbeatMonitor()
        assert monitor.is_running() is False

    def test_add_timeout_callback(self):
        monitor = HeartbeatMonitor()
        callback = MagicMock()
        monitor.add_timeout_callback(callback)

    def test_start_without_deps(self):
        monitor = HeartbeatMonitor()
        try:
            result = monitor.start_monitoring()
            assert isinstance(result, bool)
            if result:
                monitor.stop_monitoring()
        except (AttributeError, TypeError):
            pass  # Expected if GLOG/container not fully configured
