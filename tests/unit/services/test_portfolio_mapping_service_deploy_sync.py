# Related: #6279
# deploy 克隆丢组件绑定根因: _copy_graph 调 create_from_graph_editor,
# 其 _sync_mappings_from_files 会删除"图中不存在"的既有映射,
# 而 CLI bind-component 绑定的 strategy/sizer 不在 Mongo 图里 → 被删 → paper Strategies:0。
# 修复: create_from_graph_editor 增 sync_mysql 开关, deploy 图拷贝传 False (MySQL 已由 deploy step5 权威复制)。
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock
from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService


def _make_svc():
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


def _existing_mapping(file_id, type_value):
    """构造一条已存在的 MySQL mapping (模拟 deploy step5 已复制的绑定)"""
    m = MagicMock()
    m.file_id = file_id
    m.uuid = f"map_{file_id}"
    m.type = type_value
    m.name = file_id
    return m


class TestCreateFromGraphEditorSyncMysqlFlag:
    """#6279: sync_mysql 开关控制是否回写 MySQL mapping/param"""

    def test_sync_mysql_false_does_not_delete_mappings_absent_from_graph(self):
        """sync_mysql=False 时, deploy step5 已建的映射(图外)不被图同步删除"""
        svc, mock_mapping, mock_param, mock_mongo, _ = _make_svc()
        # 目标组合已有 4 条映射 (selector/strategy/sizer/risk, deploy step5 权威复制)
        mock_mapping.find_by_portfolio.return_value = [
            _existing_mapping("f_selector", 4),
            _existing_mapping("f_strategy", 6),
            _existing_mapping("f_sizer", 5),
            _existing_mapping("f_risk", 3),
        ]
        # 源 Mongo 图只有 selector+risk 两节点 (CLI 绑定的 strategy/sizer 不在图)
        graph_data = {
            "nodes": [
                {"id": "n1", "type": "SELECTOR", "data": {"file_id": "f_selector"}},
                {"id": "n2", "type": "RISKMANAGER", "data": {"file_id": "f_risk"}},
            ],
            "edges": [],
        }
        mock_mongo.get_collection.return_value.update_one.return_value = MagicMock()

        svc.create_from_graph_editor(
            portfolio_uuid="target_pid",
            graph_data=graph_data,
            name="deploy_target",
            sync_mysql=False,
        )

        # 关键断言: 图外的 strategy/sizer 映射绝不被删除 (否则 paper Strategies:0)
        mock_mapping.delete_mapping.assert_not_called()
        # sync_mysql=False 时连参数删除都不该触发
        mock_param.remove_by_mapping.assert_not_called()

    def test_sync_mysql_true_default_still_deletes_absent_mappings(self):
        """sync_mysql=True (默认, 图编辑器语义) 仍删除图外映射 — 不破坏既有行为"""
        svc, mock_mapping, mock_param, mock_mongo, _ = _make_svc()
        mock_mapping.find_by_portfolio.return_value = [
            _existing_mapping("f_keep", 4),
            _existing_mapping("f_orphan", 6),  # 图里没有 → 应删
        ]
        graph_data = {
            "nodes": [
                {"id": "n1", "type": "SELECTOR", "data": {"file_id": "f_keep"}},
            ],
            "edges": [],
        }
        mock_mongo.get_collection.return_value.update_one.return_value = MagicMock()

        svc.create_from_graph_editor(
            portfolio_uuid="p1",
            graph_data=graph_data,
            name="edited",
            # 不传 sync_mysql → 默认 True
        )

        # 图编辑器语义: 孤立映射应被删
        mock_mapping.delete_mapping.assert_called_once()
        args, _ = mock_mapping.delete_mapping.call_args
        assert args[1] == "f_orphan", f"应删除图外映射 f_orphan, 实删 {args}"
