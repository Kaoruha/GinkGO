"""
#5742 / #5734 — get_portfolio_graph 读优先级

表象：GET /node-graphs/{pid} 返回 {nodes:[], edges:[]}，但同 portfolio 的
      mappings 端点返回 4 条绑定记录。
根因：get_portfolio_graph 用 find_one(sort=[("metadata.source",1), ...])
      不限 source 升序取第一个。"AUTO_GENERATED"(A) 排在 "GRAPH_EDITOR"(G) 前
      被命中，而 portfolio 初建无 mappings 时 _sync 存的正是 AUTO 空图
      ({nodes:[],edges:[]}, source=AUTO_GENERATED)。后续即使有 GRAPH_EDITOR
      非空图，排序仍让 AUTO 空图抢占。
契约：
  - 存在非空图时必须返回非空图（空图不得抢占）
  - 多个非空图时 GRAPH_EDITOR（用户手动编辑）优先于 AUTO_GENERATED
  - 无任何图文档时仍 fallback 到 _sync（不破坏原行为）
"""
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
    mock_collection = MagicMock()
    mock_mongo.get_collection.return_value = mock_collection
    return svc, mock_mapping, mock_mongo, mock_collection


def _doc(source: str, nodes: list, _id: str = "x"):
    return {
        "_id": _id,
        "portfolio_uuid": "p1",
        "graph_data": {"nodes": nodes, "edges": []},
        "metadata": {"source": source},
    }


class TestGetPortfolioGraphReadPriority:
    """get_portfolio_graph 必须按非空 + GRAPH_EDITOR 优先选图 (#5742)"""

    def test_non_empty_graph_preferred_over_empty_auto(self):
        """AUTO 空图 + GRAPH_EDITOR 非空图共存 → 返 GRAPH_EDITOR 非空"""
        svc, _, _, mock_collection = _make_svc()
        auto_empty = _doc("AUTO_GENERATED", nodes=[], _id="a1")
        editor_full = _doc("GRAPH_EDITOR", nodes=[{"id": "n1"}], _id="e1")
        # 模拟当前 sort 命中空图的行为 + find 取所有
        mock_collection.find_one.return_value = auto_empty
        mock_collection.find.return_value = [auto_empty, editor_full]

        result = svc.get_portfolio_graph("p1")

        assert result.is_success(), f"应成功: {getattr(result, 'error', None)}"
        nodes = result.data["graph_data"]["nodes"]
        assert len(nodes) == 1, "应返回非空图（GRAPH_EDITOR），空图不得抢占"

    def test_graph_editor_preferred_among_non_empty(self):
        """两个非空图 → GRAPH_EDITOR 优先于其他 source"""
        svc, _, _, mock_collection = _make_svc()
        auto_full = _doc("AUTO_GENERATED", nodes=[{"id": "auto_n"}], _id="a1")
        editor_full = _doc("GRAPH_EDITOR", nodes=[{"id": "editor_n"}], _id="e1")
        mock_collection.find.return_value = [auto_full, editor_full]  # AUTO 在前

        result = svc.get_portfolio_graph("p1")

        assert result.is_success()
        nodes = result.data["graph_data"]["nodes"]
        assert nodes[0]["id"] == "editor_n", "非空图中 GRAPH_EDITOR 应优先"

    def test_no_docs_falls_back_to_sync(self):
        """Mongo 无任何图文档 → 触发 _sync_graph_from_mappings（不破坏原行为）"""
        svc, mock_mapping, _, mock_collection = _make_svc()
        mock_collection.find.return_value = []
        # sync 后再查返一个生成图
        synced = _doc("AUTO_GENERATED", nodes=[{"id": "synced_n"}], _id="s1")
        mock_collection.find_one.return_value = synced

        result = svc.get_portfolio_graph("p1")

        assert result.is_success()
        # fallback 触发了 sync（查了 mappings）
        mock_mapping.find_by_portfolio.assert_called()
