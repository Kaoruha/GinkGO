"""
#4569 验证：Execution Events 死代码补完移除

Execution Events 子系统从未被事件系统消费（枚举命名不匹配导致预存 bug）。
#4567 移除了 enum 值和 logger 方法，#4569 补完移除事件类、re-export、handler。
"""
import pytest


class TestExecutionEventsEnumRemoved:
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
    """验证 _ExecutionLogNamespace 类和 GLOG.execution 属性已移除"""

    def test_no_execution_log_namespace_class(self):
        from ginkgo.libs.core import logger as logger_module
        assert not hasattr(logger_module, "_ExecutionLogNamespace")

    def test_no_execution_attribute(self):
        from ginkgo.libs import GLOG
        assert not hasattr(GLOG, "execution")


class TestExecutionEventModuleRemoved:
    """验证 execution_confirmation.py 模块已删除"""

    def test_module_not_importable(self):
        with pytest.raises(ImportError):
            import ginkgo.trading.events.execution_confirmation  # noqa: F401


class TestExecutionEventReexportsRemoved:
    """验证 events/__init__.py 不再导出 EventExecution* 类"""

    def test_no_execution_confirmed_in_events(self):
        import ginkgo.trading.events as events
        assert not hasattr(events, "EventExecutionConfirmed")

    def test_no_execution_rejected_in_events(self):
        import ginkgo.trading.events as events
        assert not hasattr(events, "EventExecutionRejected")

    def test_no_execution_timeout_in_events(self):
        import ginkgo.trading.events as events
        assert not hasattr(events, "EventExecutionTimeout")

    def test_no_execution_canceled_in_events(self):
        import ginkgo.trading.events as events
        assert not hasattr(events, "EventExecutionCanceled")


class TestPortfolioManagementServiceHandlersRemoved:
    """验证 PortfolioManagementService 不再包含 execution event handler 方法"""

    def test_no_handle_execution_confirmed(self):
        from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
        assert not hasattr(PortfolioManagementService, "handle_execution_confirmed")

    def test_no_handle_execution_rejected(self):
        from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
        assert not hasattr(PortfolioManagementService, "handle_execution_rejected")

    def test_no_handle_execution_timeout(self):
        from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
        assert not hasattr(PortfolioManagementService, "handle_execution_timeout")

    def test_no_handle_execution_canceled(self):
        from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
        assert not hasattr(PortfolioManagementService, "handle_execution_canceled")

    def test_no_register_event_handlers(self):
        from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
        assert not hasattr(PortfolioManagementService, "register_event_handlers")
