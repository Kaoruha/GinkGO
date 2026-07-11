"""Tests for HeartbeatChecker (scheduler) -- #4863"""
import pytest
from unittest.mock import MagicMock

from ginkgo.livecore.scheduler.heartbeat import HeartbeatChecker


@pytest.mark.tdd
class TestGetNodeMetricsParsesLoadedPortfolioIds:
    """#4863: get_node_metrics 必须从 node:metrics:{id} Hash 解析
    `loaded_portfolio_ids`（JSON 列表），供 Scheduler reconcile 判定漏加载。

    老节点无此字段 → 返回 None（detect_undelivered_portfolios 据此跳过，
    不误判）；JSON 解析失败也降级为 None（不阻塞 metrics 读取）。
    """

    def test_parses_loaded_portfolio_ids_json(self):
        redis_client = MagicMock()
        redis_client.hgetall.return_value = {
            b"portfolio_count": b"2",
            b"loaded_portfolio_ids": b'["pid-1","pid-2"]',
            b"queue_size": b"0",
            b"cpu_usage": b"0.0",
        }
        checker = HeartbeatChecker(redis_client)

        metrics = checker.get_node_metrics("nodeX")

        assert metrics["loaded_portfolio_ids"] == ["pid-1", "pid-2"]

    def test_missing_field_returns_none(self):
        """老节点未上报 loaded_portfolio_ids → None（跳过该节点，不误报）。"""
        redis_client = MagicMock()
        redis_client.hgetall.return_value = {
            b"portfolio_count": b"1",
            b"queue_size": b"0",
        }
        checker = HeartbeatChecker(redis_client)

        metrics = checker.get_node_metrics("nodeX")

        assert metrics["loaded_portfolio_ids"] is None

    def test_empty_list_parses(self):
        redis_client = MagicMock()
        redis_client.hgetall.return_value = {
            b"portfolio_count": b"0",
            b"loaded_portfolio_ids": b"[]",
        }
        checker = HeartbeatChecker(redis_client)

        metrics = checker.get_node_metrics("nodeX")

        assert metrics["loaded_portfolio_ids"] == []

    def test_corrupt_json_returns_none(self):
        """JSON 损坏 → None（降级，不抛异常阻塞 metrics 读取）。"""
        redis_client = MagicMock()
        redis_client.hgetall.return_value = {
            b"portfolio_count": b"1",
            b"loaded_portfolio_ids": b"not-json",
        }
        checker = HeartbeatChecker(redis_client)

        metrics = checker.get_node_metrics("nodeX")

        assert metrics["loaded_portfolio_ids"] is None
