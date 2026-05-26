"""Smoke tests for livecore.trade_gateway_adapter -- #3870"""
import pytest
from unittest.mock import MagicMock

try:
    from ginkgo.livecore.trade_gateway_adapter import TradeGatewayAdapter
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="TradeGatewayAdapter not available")
class TestTradeGatewayAdapter:
    def test_instantiation(self):
        mock_broker = MagicMock()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])
        assert adapter is not None

    def test_get_statistics(self):
        mock_broker = MagicMock()
        adapter = TradeGatewayAdapter(brokers=[mock_broker])
        stats = adapter.get_statistics()
        assert isinstance(stats, dict)
