import pytest
from decimal import Decimal
from ginkgo.trading.brokers.sim_broker import SimBroker

class TestSimBrokerLimitPrice:
    def test_buy_at_limit_up_should_block(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("10.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("10.00"), "buy") is True

    def test_buy_below_limit_up_should_pass(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.50"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.80"), "buy") is False

    def test_sell_at_limit_down_should_block(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.00"), "sell") is True

    def test_sell_above_limit_down_should_pass(self):
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.50"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.20"), "sell") is False

    def test_no_market_data_should_pass(self):
        broker = SimBroker()
        assert broker._is_limit_blocked("UNKNOWN.SZ", Decimal("10.00"), "buy") is False
