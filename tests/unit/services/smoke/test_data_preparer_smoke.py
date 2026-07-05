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

try:
    from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
    HAS_CRUD = True
except ImportError:
    HAS_CRUD = False


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
            # spec=AnalyzerRecordCRUD 防止 MagicMock auto-create 掩盖缺失方法 (#4954)
            mock_crud = MagicMock(spec=AnalyzerRecordCRUD) if HAS_CRUD else MagicMock()
            preparer = DataPreparer(analyzer_record_crud=mock_crud)
            # Should not crash
            preparer.cleanup_historic_records("engine-id", {"pf-1": {}, "pf-2": {}})

    def test_cleanup_historic_records_calls_remove_with_filters(self):
        """cleanup_historic_records() 必须对每个 portfolio 调 remove(filters=...) (#4954)

        历史 bug: 调用了 CRUD 上不存在的 delete_filtered -> AttributeError 被
        except 吞掉只 warn -> 旧记录不清理。spec= 让缺失方法在测试中真 raise，
        断言 remove 调用让 except 吞异常也无法蒙混。
        """
        if not HAS_CRUD:
            pytest.skip("AnalyzerRecordCRUD not importable")
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            mock_crud = MagicMock(spec=AnalyzerRecordCRUD)
            preparer = DataPreparer(analyzer_record_crud=mock_crud)
            preparer.cleanup_historic_records(
                "engine-1", {"pf-1": {}, "pf-2": {}, "pf-3": {}}
            )
            # 每个 portfolio 应触发一次 remove
            assert mock_crud.remove.call_count == 3
            # 每次调用 filters 必须含 portfolio_id + engine_id
            for call in mock_crud.remove.call_args_list:
                filters = call.kwargs.get("filters") or (call.args[0] if call.args else None)
                assert filters is not None
                assert "portfolio_id" in filters
                assert "engine_id" in filters
                assert filters["engine_id"] == "engine-1"
            # 确认 delete_filtered 这种不存在的方法未被调用（防回归）
            assert not hasattr(mock_crud, "delete_filtered")

    def test_get_sample_config_callable(self):
        """get_sample_config() 可调用"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer()
            result = preparer.get_sample_config("historic")
            assert isinstance(result, dict)
            assert "engine" in result

    def test_get_sample_config_live_fallback_historic(self):
        """ADR-003: live sample 已移除，get_sample_config('live') fallback 到 historic"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer()
            live_config = preparer.get_sample_config("live")
            historic_config = preparer.get_sample_config("historic")
            assert live_config == historic_config

    def test_save_sample_config_callable(self, tmp_path):
        """save_sample_config() 可调用"""
        with patch("ginkgo.trading.services._assembly.data_preparer.GLOG"):
            preparer = DataPreparer()
            output_file = tmp_path / "sample_config.yaml"
            result = preparer.save_sample_config(str(output_file), "historic")
            assert hasattr(result, "success")
