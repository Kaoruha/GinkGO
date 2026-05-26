"""Smoke test for DataPreparer -- #3823"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import with fallback
try:
    from ginkgo.trading.services._assembly.data_preparer import DataPreparer
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.trading.services._assembly.data_preparer not importable")
class TestDataPreparerSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def test_instantiation_no_args(self):
        """Service 可无参实例化"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer()
        assert preparer is not None

    def test_instantiation_with_deps(self):
        """Service 可注入依赖实例化"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer(
                engine_service=MagicMock(),
                portfolio_service=MagicMock(),
                file_service=MagicMock(),
                analyzer_record_crud=MagicMock(),
            )
        assert preparer is not None

    def test_prepare_engine_data_callable(self):
        """prepare_engine_data() 可调用"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            mock_engine_svc = MagicMock()
            # Simulate no portfolios found
            mock_engine_svc.get_portfolios.return_value = MagicMock(success=False, data=None)
            preparer = DataPreparer(engine_service=mock_engine_svc)
            result = preparer.prepare_engine_data("engine-id")
            # Returns ServiceResult
            assert hasattr(result, "success")

    def test_cleanup_historic_records_callable(self):
        """cleanup_historic_records() 可调用"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            mock_crud = MagicMock()
            preparer = DataPreparer(analyzer_record_crud=mock_crud)
            # Should not crash
            preparer.cleanup_historic_records("engine-id", {"pf-1": {}, "pf-2": {}})

    def test_get_sample_config_callable(self):
        """get_sample_config() 可调用"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer()
            result = preparer.get_sample_config("historic")
            assert isinstance(result, dict)
            assert "engine" in result

    def test_save_sample_config_callable(self, tmp_path):
        """save_sample_config() 可调用"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer()
            output_file = tmp_path / "sample_config.yaml"
            result = preparer.save_sample_config(str(output_file), "historic")
            assert hasattr(result, "success")
