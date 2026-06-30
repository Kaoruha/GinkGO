"""
PortfolioMappingService 图生命周期操作测试 -- #6085

覆盖新增的 delete_graph / duplicate_graph 方法（行为通过公开接口验证，依赖 mock）。
风格对齐 tests/unit/services/smoke/test_portfolio_mapping_service_smoke.py。
"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService
    from ginkgo.data.services.base_service import ServiceResult
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="portfolio_mapping_service not importable")
class TestPortfolioMappingGraphLifecycle:
    """delete_graph / duplicate_graph 行为测试"""

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

    # ---------- delete_graph ----------

    def test_delete_graph_removes_all_mappings_and_mongo_doc(self):
        """delete_graph 对每个 mapping 删参数+删映射，并删 Mongo 图文档"""
        svc, mock_mapping, mock_param, mock_mongo, _ = self._make_svc()

        m1 = MagicMock(uuid="m1", file_id="f1")
        m2 = MagicMock(uuid="m2", file_id="f2")
        mock_mapping.find_by_portfolio.return_value = [m1, m2]
        mock_collection = MagicMock()
        mock_mongo.get_collection.return_value = mock_collection

        result = svc.delete_graph("portfolio-1")

        assert result.is_success()
        # 删了两个 mapping 的参数
        mock_param.remove_by_mapping.assert_any_call("m1")
        mock_param.remove_by_mapping.assert_any_call("m2")
        # 删了两个 mapping
        mock_mapping.delete_mapping.assert_any_call("portfolio-1", "f1")
        mock_mapping.delete_mapping.assert_any_call("portfolio-1", "f2")
        # 删了 Mongo 文档
        mock_mongo.get_collection.assert_called_with("portfolio_graph_data")
        mock_collection.delete_many.assert_called_once_with({"portfolio_uuid": "portfolio-1"})

    # ---------- duplicate_graph ----------

    def test_duplicate_graph_copies_source_to_new_uuid(self):
        """duplicate_graph 读源图并以新 uuid 创建副本，新 uuid 不等于源"""
        svc, *_ = self._make_svc()
        graph_data = {"nodes": [{"id": "n1"}], "edges": []}

        with patch.object(svc, "get_portfolio_graph",
                          return_value=ServiceResult.success(data={"graph_data": graph_data})) as mock_get, \
             patch.object(svc, "create_from_graph_editor",
                          return_value=ServiceResult.success(
                              data={"mongo_id": "mongo-1", "mappings_count": 1})) as mock_create:
            result = svc.duplicate_graph("source-1", name="copy")

        assert result.is_success()
        mock_get.assert_called_once_with("source-1")
        # create 以「新 uuid」调用，不能等于源
        _, kwargs = mock_create.call_args
        new_uuid = kwargs["portfolio_uuid"]
        assert new_uuid != "source-1"
        assert kwargs["graph_data"] == graph_data
        assert kwargs["name"] == "copy"
        # 返回里带新 uuid 且与传入 create 的一致
        assert result.data["new_portfolio_uuid"] == new_uuid
        assert result.data["source_uuid"] == "source-1"

    def test_duplicate_graph_returns_error_when_source_missing(self):
        """源图不存在时 duplicate_graph 返回失败，且不创建副本"""
        svc, *_ = self._make_svc()
        with patch.object(svc, "get_portfolio_graph",
                          return_value=ServiceResult.error("not found")) as mock_get, \
             patch.object(svc, "create_from_graph_editor") as mock_create:
            result = svc.duplicate_graph("missing-1", name="copy")

        assert not result.is_success()
        mock_get.assert_called_once_with("missing-1")
        mock_create.assert_not_called()
