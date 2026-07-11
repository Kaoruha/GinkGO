"""Tests for HeartbeatManager -- #4863"""
import json

import pytest
from unittest.mock import MagicMock

from ginkgo.workers.execution_node.heartbeat_manager import HeartbeatManager


def _make_node(portfolios, node_id="nodeX", running=True, paused=False):
    """构造 ExecutionNode 的 MagicMock，portfolios 用真 dict 避免 json 递归。"""
    node = MagicMock()
    node.node_id = node_id
    node.portfolios = portfolios  # 真 dict
    node.is_running = running
    node.is_paused = paused
    node.heartbeat_ttl = 30
    node.total_event_count = 0
    node.backpressure_count = 0
    node.dropped_event_count = 0
    redis_client = MagicMock()
    node._get_redis_client.return_value = redis_client
    return node, redis_client


@pytest.mark.tdd
class TestUpdateNodeMetricsReportsLoadedPortfolioIds:
    """#4863: update_node_metrics 必须把 node.portfolios 的 id 列表上报到
    node:metrics:{id} Hash 的 `loaded_portfolio_ids` 字段（JSON 编码）。

    这是 reconcile 链路的数据源——Scheduler 读该字段才能判定「plan 分配了
    但节点没加载」，重发 Kafka 加载命令。只有 portfolio_count（数量）不够：
    scheduler 无法知道是 *哪些* pid 没加载。
    """

    def test_writes_loaded_portfolio_ids_as_json_list(self):
        """node.portfolios 含 2 个 pid → metrics.loaded_portfolio_ids = JSON 列表。"""
        node, redis_client = _make_node({"pid-1": object(), "pid-2": object()})
        hm = HeartbeatManager(node)

        hm.update_node_metrics()

        redis_client.hset.assert_called_once()
        kwargs = redis_client.hset.call_args.kwargs
        assert "loaded_portfolio_ids" in kwargs["mapping"]
        loaded = json.loads(kwargs["mapping"]["loaded_portfolio_ids"])
        assert sorted(loaded) == ["pid-1", "pid-2"]

    def test_empty_portfolios_writes_empty_list(self):
        """node.portfolios={} → loaded_portfolio_ids = JSON 空列表（非空串）。"""
        node, redis_client = _make_node({})
        hm = HeartbeatManager(node)

        hm.update_node_metrics()

        kwargs = redis_client.hset.call_args.kwargs
        assert json.loads(kwargs["mapping"]["loaded_portfolio_ids"]) == []
