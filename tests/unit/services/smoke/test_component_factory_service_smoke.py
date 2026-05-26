"""Smoke test for ComponentFactoryService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

# Import with fallback
try:
    from ginkgo.trading.services.component_factory_service import ComponentFactoryService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.trading.services.component_factory_service not importable")
class TestComponentFactoryServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def test_instantiation(self):
        """Service 可实例化"""
        with patch("ginkgo.trading.services.component_factory_service.GLOG"):
            svc = ComponentFactoryService()
        assert svc is not None

    def test_initialize_callable(self):
        """initialize() 可调用"""
        with patch("ginkgo.trading.services.component_factory_service.GLOG"):
            with patch("ginkgo.trading.services.component_factory_service.container") as mock_container:
                mock_component_svc = MagicMock()
                mock_container.component_service.return_value = mock_component_svc
                # Stub base-class imports inside _initialize_base_class_mapping
                with patch.dict("sys.modules", {
                    "ginkgo.trading.strategies": MagicMock(BaseStrategy=type("BaseStrategy", (), {})),
                    "ginkgo.trading.analysis.analyzers": MagicMock(BaseAnalyzer=type("BaseAnalyzer", (), {})),
                    "ginkgo.trading.selectors": MagicMock(BaseSelector=type("BaseSelector", (), {})),
                    "ginkgo.trading.sizers": MagicMock(BaseSizer=type("BaseSizer", (), {})),
                    "ginkgo.trading.risk_managementss": MagicMock(BaseRiskManagement=type("BaseRiskManagement", (), {})),
                }):
                    svc = ComponentFactoryService()
                    result = svc.initialize()
                    assert isinstance(result, bool)

    def test_create_component_callable(self):
        """create_component() 可调用"""
        with patch("ginkgo.trading.services.component_factory_service.GLOG"):
            svc = ComponentFactoryService()
            svc._component_service = MagicMock()
            svc._component_service.get_instance_by_file.return_value = MagicMock()
            result = svc.create_component("file-id", "mapping-id", MagicMock(value=6))
            # Returns a component or None -- just verify no crash

    def test_create_components_by_portfolio_callable(self):
        """create_components_by_portfolio() 可调用"""
        with patch("ginkgo.trading.services.component_factory_service.GLOG"):
            svc = ComponentFactoryService()
            svc._component_service = MagicMock()
            svc._component_service.get_trading_system_components_by_portfolio.return_value = []
            result = svc.create_components_by_portfolio("portfolio-id", MagicMock(value=6))
            assert isinstance(result, list)

    def test_validate_component_code_callable(self):
        """validate_component_code() 可调用"""
        with patch("ginkgo.trading.services.component_factory_service.GLOG"):
            svc = ComponentFactoryService()
            svc._component_service = MagicMock()
            svc._component_service.validate_component_code.return_value = {"success": True}
            result = svc.validate_component_code("print('hello')", MagicMock(value=6))
            assert isinstance(result, dict)

    def test_get_component_requirements_callable(self):
        """get_component_requirements() 可调用"""
        with patch("ginkgo.trading.services.component_factory_service.GLOG"):
            svc = ComponentFactoryService()
            # With empty _base_class_mapping, should return error dict
            result = svc.get_component_requirements(MagicMock(value=6))
            assert isinstance(result, dict)
