"""
#4568 验证：Execution Events 死代码已移除

Execution Events (EXECUTIONCONFIRMATION/REJECTION/TIMEOUT/CANCELLATION) 从未被
事件系统消费，_ExecutionLogNamespace 也无调用方。此测试确认移除干净。
"""
import pytest


class TestExecutionEventsRemoved:
    """验证 EVENT_TYPES 中不再包含 Execution Events 枚举成员"""

    def test_no_execution_confirmation(self):
        from ginkgo.enums import EVENT_TYPES
        assert not hasattr(EVENT_TYPES, "EXECUTIONCONFIRMATION")

    def test_no_execution_rejection(self):
        from ginkgo.enums import EVENT_TYPES
        assert not hasattr(EVENT_TYPES, "EXECUTIONREJECTION")

    def test_no_execution_timeout(self):
        from ginkgo.enums import EVENT_TYPES
        assert not hasattr(EVENT_TYPES, "EXECUTIONTIMEOUT")

    def test_no_execution_cancellation(self):
        from ginkgo.enums import EVENT_TYPES
        assert not hasattr(EVENT_TYPES, "EXECUTIONCANCELLATION")


class TestExecutionLogMethodsRemoved:
    """验证 GinkgoLogger 不再包含 execution event 日志方法"""

    @pytest.fixture
    def logger(self):
        from ginkgo.libs import GLOG
        return GLOG

    def test_no_log_execution_rejected_event(self, logger):
        assert not hasattr(logger, "log_execution_rejected_event")

    def test_no_log_execution_timeout_event(self, logger):
        assert not hasattr(logger, "log_execution_timeout_event")

    def test_no_log_execution_confirm_event(self, logger):
        assert not hasattr(logger, "log_execution_confirm_event")

    def test_no_log_execution_cancel_event(self, logger):
        assert not hasattr(logger, "log_execution_cancel_event")


class TestExecutionLogNamespaceRemoved:
    """验证 _ExecutionLogNamespace 类已移除"""

    def test_no_execution_log_namespace(self):
        from ginkgo.libs.core import logger as logger_module
        assert not hasattr(logger_module, "_ExecutionLogNamespace")
