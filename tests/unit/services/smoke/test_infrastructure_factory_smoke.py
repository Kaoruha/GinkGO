"""Smoke test for InfrastructureFactory -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

# Import with fallback
try:
    from ginkgo.trading.services._assembly.infrastructure_factory import InfrastructureFactory
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.trading.services._assembly.infrastructure_factory not importable")
class TestInfrastructureFactorySmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def test_instantiation(self):
        """Factory 可实例化"""
        factory = InfrastructureFactory()
        assert factory is not None

    def test_resolve_execution_mode_callable(self):
        """resolve_execution_mode() 可调用"""
        result = InfrastructureFactory.resolve_execution_mode({"execution_mode": "backtest"})
        # Returns an EXECUTION_MODE enum member
        assert result is not None

    def test_resolve_execution_mode_none_input(self):
        """resolve_execution_mode(None) 不崩溃"""
        result = InfrastructureFactory.resolve_execution_mode(None)
        assert result is not None

    def test_resolve_execution_mode_string_mapping(self):
        """resolve_execution_mode() 支持字符串映射"""
        result = InfrastructureFactory.resolve_execution_mode({"execution_mode": "live"})
        assert result is not None

    def test_create_feeder_for_mode_callable(self):
        """create_feeder_for_mode() 可调用"""
        with patch("ginkgo.trading.services._assembly.infrastructure_factory.GLOG"):
            from ginkgo.enums import EXECUTION_MODE
            result = InfrastructureFactory.create_feeder_for_mode(EXECUTION_MODE.BACKTEST)
            assert result is not None

    def test_create_base_engine_callable(self):
        """create_base_engine() 可调用"""
        with patch("ginkgo.trading.services._assembly.infrastructure_factory.GLOG"):
            mock_engine_data = {
                "name": "TestEngine",
                "execution_mode": "backtest",
                "backtest_start_date": "2023-01-01",
                "backtest_end_date": "2023-12-31",
                "task_id": "test-task",
            }
            result = InfrastructureFactory.create_base_engine(
                engine_data=mock_engine_data,
                engine_id="test-engine-id",
                logger=MagicMock(),
            )
            # May return an engine instance or None depending on imports
            # Just verify no crash

    def test_setup_data_feeder_for_engine_callable(self):
        """setup_data_feeder_for_engine() 可调用"""
        with patch("ginkgo.trading.services._assembly.infrastructure_factory.GLOG"):
            mock_engine = MagicMock()
            result = InfrastructureFactory.setup_data_feeder_for_engine(
                engine=mock_engine,
                logger=MagicMock(),
                engine_data={"execution_mode": "backtest"},
            )
            assert isinstance(result, bool)
