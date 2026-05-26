"""Smoke test for MappingService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.mapping_service import MappingService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.mapping_service not importable")
class TestMappingServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_ep = MagicMock()
        mock_pf = MagicMock()
        mock_eh = MagicMock()
        mock_param = MagicMock()
        svc = MappingService(
            engine_portfolio_mapping_crud=mock_ep,
            portfolio_file_mapping_crud=mock_pf,
            engine_handler_mapping_crud=mock_eh,
            param_crud=mock_param,
        )
        return svc, mock_ep, mock_pf, mock_eh, mock_param

    def test_instantiation(self):
        svc, *_ = self._make_svc()
        assert svc is not None

    def test_cleanup_orphaned_mappings_callable(self):
        svc, mock_ep, *_ = self._make_svc()
        mock_session = MagicMock()
        mock_ep.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_ep.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.execute.return_value.rowcount = 0
        result = svc.cleanup_orphaned_mappings()
        assert result is not None

    def test_create_engine_portfolio_mapping_callable(self):
        svc, mock_ep, *_ = self._make_svc()
        mock_ep.find.return_value = []
        mock_ep.add_batch.return_value = [MagicMock()]
        result = svc.create_engine_portfolio_mapping("e1", "p1")
        assert result is not None

    def test_get_engine_portfolio_mapping_callable(self):
        svc, mock_ep, *_ = self._make_svc()
        mock_ep.find.return_value = []
        result = svc.get_engine_portfolio_mapping(engine_uuid="e1")
        assert result is not None

    def test_create_portfolio_file_binding_callable(self):
        svc, _, mock_pf, _, _ = self._make_svc()
        mock_pf.find.return_value = []
        mock_pf.add_batch.return_value = [MagicMock()]
        result = svc.create_portfolio_file_binding(
            portfolio_uuid="p1", file_uuid="f1",
            file_name="test", file_type=MagicMock(value=6),
        )
        assert result is not None
