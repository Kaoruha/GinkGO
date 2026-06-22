# Issue: NodeGraphCreate schema 缺 portfolio_uuid 字段
# Upstream: api.schemas.node_graph.NodeGraphCreate
# Downstream: api.api.node_graph.create_node_graph (:145 读 data.portfolio_uuid)
# Role: 验证创建节点图 schema 接受 portfolio_uuid，使路由能关联到 portfolio

"""
NodeGraphCreate schema 字段测试

验证 NodeGraphCreate 包含可选 portfolio_uuid 字段——创建路由
(api.api.node_graph:145) 读 data.portfolio_uuid 关联 portfolio，
schema 缺该字段会 AttributeError 致创建失败。
"""

import sys
from pathlib import Path

# api 是 namespace package（无 __init__.py），pytest 下 sys.path 干扰致
# `from api.schemas.node_graph` 解析失败（No module named 'api.schemas'）。
# 直插 schemas 目录 + 按模块名导入（node_graph.py 无 api 内部依赖，独立可加载）。
# 仿 test_node_graph_file_type.py 模式，避开 namespace 包解析陷阱。
_schemas_dir = str(Path(__file__).resolve().parents[2] / "api" / "schemas")
if _schemas_dir not in sys.path:
    sys.path.insert(0, _schemas_dir)

from node_graph import NodeGraphCreate


def _graph_data():
    """最小合法 graph_data（空 nodes/edges）"""
    return {"nodes": [], "edges": []}


class TestNodeGraphCreatePortfolioUuid:
    """#5387: NodeGraphCreate schema 的 portfolio_uuid 字段"""

    def test_accepts_portfolio_uuid(self):
        """schema 接受 portfolio_uuid 字段并保留值"""
        schema = NodeGraphCreate(
            name="test",
            graph_data=_graph_data(),
            portfolio_uuid="portfolio-abc-123",
        )
        assert schema.portfolio_uuid == "portfolio-abc-123"

    def test_portfolio_uuid_defaults_none(self):
        """不传 portfolio_uuid 时默认 None（向后兼容，路由兜底生成 uuid）"""
        schema = NodeGraphCreate(name="test", graph_data=_graph_data())
        assert schema.portfolio_uuid is None
