"""PortfolioMappingService 跨库孤儿补偿测试 (#5559)

create_from_graph_editor 先写 MongoDB 后 sync MySQL，下游失败时
MongoDB 文档成孤儿。验证补偿事务：sync 失败 → 反向删 Mongo。

update_from_graph_editor / remove_file 同类非原子问题留 follow-up（本 PR 聚焦 create）。
"""
import pytest
from unittest.mock import MagicMock, patch


def _make_service():
    """实例化 service（4 个依赖均 MagicMock，无需 DB）"""
    from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService
    return PortfolioMappingService(
        mapping_crud=MagicMock(),
        param_service=MagicMock(),
        mongo_driver=MagicMock(),
        file_service=MagicMock(),
    )


class TestDeleteGraphFromMongo:
    """Slice 1: _delete_graph_from_mongo helper（补偿原语）"""

    def test_calls_delete_one_with_doc_id(self):
        """调 collection.delete_one({_id: doc_id})"""
        svc = _make_service()
        mock_collection = MagicMock()
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)
        svc._mongo_driver.get_collection.return_value = mock_collection

        result = svc._delete_graph_from_mongo("doc-123")

        svc._mongo_driver.get_collection.assert_called_with("portfolio_graph_data")
        mock_collection.delete_one.assert_called_once_with({"_id": "doc-123"})
        assert result is True

    def test_returns_false_when_nothing_deleted(self):
        """文档不存在时 delete_count=0 返 False（幂等：对不存在 _id 无害）"""
        svc = _make_service()
        mock_collection = MagicMock()
        mock_collection.delete_one.return_value = MagicMock(deleted_count=0)
        svc._mongo_driver.get_collection.return_value = mock_collection

        result = svc._delete_graph_from_mongo("missing-doc")

        assert result is False


class TestCreateCompensationOnSyncFailure:
    """Slice 2: create_from_graph_editor sync 失败补偿

    @retry 重试 3 次，每次 sync 失败都补偿删当前 mongo_id。
    mock _save_graph_to_mono 返固定 doc_id，故补偿每次删同值。
    """

    def test_deletes_mongo_when_mapping_sync_fails(self):
        """步骤4 sync Mapping 失败 → 补偿删 Mongo + 返 error"""
        svc = _make_service()
        with patch.object(svc, "_save_graph_to_mongo", return_value="doc-123"), \
             patch.object(svc, "_sync_mappings_from_files", side_effect=RuntimeError("mysql down")), \
             patch.object(svc, "_extract_files_from_graph", return_value=[]), \
             patch.object(svc, "_extract_params_from_graph", return_value=[]), \
             patch.object(svc, "_delete_graph_from_mongo") as mock_delete:
            result = svc.create_from_graph_editor(
                portfolio_uuid="p1", graph_data={"nodes": []}, name="t"
            )
        # 补偿删 Mongo 被调（每次重试都删 doc-123）
        assert mock_delete.called
        assert all(call.args == ("doc-123",) for call in mock_delete.call_args_list)
        # 最终返 error
        assert not result.is_success()

    def test_deletes_mongo_when_param_sync_fails(self):
        """步骤5 sync MParam 失败（步骤4成功）→ 补偿删 Mongo"""
        svc = _make_service()
        with patch.object(svc, "_save_graph_to_mongo", return_value="doc-456"), \
             patch.object(svc, "_sync_mappings_from_files", return_value=MagicMock()), \
             patch.object(svc, "_sync_params_from_nodes", side_effect=RuntimeError("param sync fail")), \
             patch.object(svc, "_extract_files_from_graph", return_value=[]), \
             patch.object(svc, "_extract_params_from_graph", return_value=[]), \
             patch.object(svc, "_delete_graph_from_mongo") as mock_delete:
            result = svc.create_from_graph_editor(
                portfolio_uuid="p1", graph_data={"nodes": []}, name="t"
            )
        assert mock_delete.called
        assert all(call.args == ("doc-456",) for call in mock_delete.call_args_list)
        assert not result.is_success()

    def test_no_delete_on_success(self):
        """全部成功 → 不调补偿删（回归保护）"""
        svc = _make_service()
        with patch.object(svc, "_save_graph_to_mongo", return_value="doc-ok"), \
             patch.object(svc, "_sync_mappings_from_files", return_value=MagicMock()), \
             patch.object(svc, "_sync_params_from_nodes", return_value=MagicMock()), \
             patch.object(svc, "_extract_files_from_graph", return_value=[]), \
             patch.object(svc, "_extract_params_from_graph", return_value=[]), \
             patch.object(svc, "_delete_graph_from_mongo") as mock_delete:
            result = svc.create_from_graph_editor(
                portfolio_uuid="p1", graph_data={"nodes": []}, name="t"
            )
        assert result.is_success()
        mock_delete.assert_not_called()
