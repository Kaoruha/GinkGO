"""Smoke test for PortfolioMappingService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.portfolio_mapping_service not importable")
class TestPortfolioMappingServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_mapping = MagicMock()
        mock_param = MagicMock()
        mock_mongo = MagicMock()
        mock_file = MagicMock()
        svc = PortfolioMappingService(
            mapping_crud=mock_mapping,
            param_service=mock_param,
            mongo_driver=mock_mongo,
            file_service=mock_file,
        )
        return svc, mock_mapping, mock_param, mock_mongo, mock_file

    def test_instantiation(self):
        svc, *_ = self._make_svc()
        assert svc is not None

    def test_add_file_callable(self):
        svc, mock_mapping, mock_param, mock_mongo, _ = self._make_svc()
        mock_mapping_obj = MagicMock()
        mock_mapping_obj.uuid = "m1"
        mock_mapping.add.return_value = mock_mapping_obj
        mock_mongo.get_collection.return_value.find_one.return_value = None
        mock_mongo.get_collection.return_value.update_one.return_value = MagicMock()
        result = svc.add_file(
            portfolio_uuid="p1",
            file_id="f1",
            file_type=MagicMock(name="STRATEGY"),
        )
        assert result is not None

    def test_remove_file_callable(self):
        svc, mock_mapping, mock_param, mock_mongo, _ = self._make_svc()
        mock_mapping.find.return_value = []
        mock_mapping.delete_mapping.return_value = True
        mock_mongo.get_collection.return_value.find_one.return_value = None
        result = svc.remove_file(portfolio_uuid="p1", file_id="f1")
        assert result is not None

    def test_get_portfolio_graph_callable(self):
        svc, mock_mapping, mock_param, mock_mongo, _ = self._make_svc()
        mock_collection = MagicMock()
        mock_mongo.get_collection.return_value = mock_collection
        mock_collection.find_one.return_value = {
            "graph_data": {"nodes": [], "edges": []},
            "metadata": {},
        }
        result = svc.get_portfolio_graph(portfolio_uuid="p1")
        assert result is not None

    def test_get_portfolio_mappings_callable(self):
        svc, mock_mapping, mock_param, _, _ = self._make_svc()
        mock_mapping.find_by_portfolio.return_value = []
        result = svc.get_portfolio_mappings(portfolio_uuid="p1")
        assert result is not None
