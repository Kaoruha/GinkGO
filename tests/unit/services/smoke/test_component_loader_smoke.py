"""Smoke test for ComponentLoader -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

# Import with fallback
try:
    from ginkgo.trading.services._assembly.component_loader import ComponentLoader
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.trading.services._assembly.component_loader not importable")
class TestComponentLoaderSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def test_instantiation_no_args(self):
        """Service 可无参实例化"""
        with patch("ginkgo.trading.services._assembly.component_loader.GLOG"):
            loader = ComponentLoader()
        assert loader is not None

    def test_instantiation_with_deps(self):
        """Service 可注入依赖实例化"""
        with patch("ginkgo.trading.services._assembly.component_loader.GLOG"):
            mock_file_svc = MagicMock()
            mock_logger = MagicMock()
            loader = ComponentLoader(file_service=mock_file_svc, logger=mock_logger)
        assert loader is not None

    def test_perform_component_binding_callable_empty(self):
        """perform_component_binding() 可调用 -- 无组件场景"""
        with patch("ginkgo.trading.services._assembly.component_loader.GLOG"):
            mock_logger = MagicMock()
            mock_portfolio = MagicMock()
            mock_portfolio.uuid = "test-portfolio-id"
            loader = ComponentLoader(file_service=MagicMock(), logger=mock_logger)
            # Empty components -- should return False (no strategies)
            result = loader.perform_component_binding(
                portfolio=mock_portfolio,
                components={"strategies": [], "selectors": [], "sizers": [], "risk_managers": [], "analyzers": []},
                logger=mock_logger,
            )
            assert isinstance(result, bool)
            assert result is False  # no strategies -> False

    def test_perform_component_binding_callable_with_strategy(self):
        """perform_component_binding() 可调用 -- 有策略但无 selector"""
        with patch("ginkgo.trading.services._assembly.component_loader.GLOG"):
            mock_logger = MagicMock()
            mock_portfolio = MagicMock()
            mock_portfolio.uuid = "test-portfolio-id"
            loader = ComponentLoader(file_service=MagicMock(), logger=mock_logger)
            # Has strategies but no selector -- returns False
            result = loader.perform_component_binding(
                portfolio=mock_portfolio,
                components={"strategies": [{"file_id": "f1", "type": 6, "mapping_uuid": "m1"}], "selectors": [], "sizers": [], "risk_managers": [], "analyzers": []},
                logger=mock_logger,
            )
            assert isinstance(result, bool)
