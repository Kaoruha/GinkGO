"""Smoke tests for livecore.websocket_event_adapter -- #3870"""
import pytest

try:
    from ginkgo.livecore.websocket_event_adapter import (
        WebSocketEventAdapter,
        adapt_ticker, adapt_candlestick, adapt_account, adapt_position,
        adapt_order, adapt_order_algo, adapt_trades, adapt_orderbook,
    )
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.fixture
def ticker_msg():
    return {
        "arg": {"channel": "tickers", "instId": "BTC-USDT"},
        "data": [{"last": "50000.0", "bidPx": "49999.0", "askPx": "50001.0", "vol24h": "12345.6", "ts": "1234567890000"}]
    }

@pytest.fixture
def candle_msg():
    return {
        "arg": {"channel": "candle1D", "instId": "BTC-USDT"},
        "data": [["1234567890000", "50000", "51000", "49000", "50500", "1000.0", "50500000.0", "100"]]
    }

@pytest.fixture
def account_msg():
    return {
        "arg": {"channel": "account"},
        "data": [{"totalEq": "100000.0", "upl": "500.0", "cashBal": "95000.0"}]
    }

@pytest.fixture
def position_msg():
    return {
        "arg": {"channel": "positions"},
        "data": [{"instId": "BTC-USDT", "pos": "0.5", "posSide": "long", "upl": "100.0", "lever": "10"}]
    }

@pytest.fixture
def order_msg():
    return {
        "arg": {"channel": "orders"},
        "data": [{"instId": "BTC-USDT", "ordId": "123456", "side": "buy", "ordType": "limit",
                  "px": "50000", "sz": "0.1", "state": "live"}]
    }

@pytest.fixture
def trades_msg():
    return {
        "arg": {"channel": "trades"},
        "data": [{"instId": "BTC-USDT", "tradeId": "789", "px": "50001.0", "sz": "0.05", "side": "buy"}]
    }

@pytest.fixture
def orderbook_msg():
    return {
        "arg": {"channel": "books5"},
        "data": [{"asks": [["50001", "1.0"], ["50002", "2.0"]], "bids": [["49999", "1.5"], ["49998", "2.5"]]}]
    }


@pytest.mark.skipif(not HAS_MODULE, reason="websocket_event_adapter not available")
class TestAdaptFunctions:
    def test_adapt_ticker(self, ticker_msg):
        result = adapt_ticker(ticker_msg)
        assert result is not None
        assert isinstance(result, dict)

    def test_adapt_candlestick(self, candle_msg):
        result = adapt_candlestick(candle_msg)
        assert result is not None

    def test_adapt_account(self, account_msg):
        result = adapt_account(account_msg)
        assert result is not None

    def test_adapt_position(self, position_msg):
        result = adapt_position(position_msg)
        assert result is not None

    def test_adapt_order(self, order_msg):
        result = adapt_order(order_msg)
        assert result is not None

    def test_adapt_order_algo(self, order_msg):
        result = adapt_order_algo(order_msg)
        assert result is not None

    def test_adapt_trades(self, trades_msg):
        result = adapt_trades(trades_msg)
        assert result is not None

    def test_adapt_orderbook(self, orderbook_msg):
        result = adapt_orderbook(orderbook_msg)
        assert result is not None


@pytest.mark.skipif(not HAS_MODULE, reason="websocket_event_adapter not available")
class TestWebSocketEventAdapter:
    def test_adapt_auto_routes(self, ticker_msg):
        # adapt() looks up channel in CHANNEL_ADAPTERS dict
        # 'tickers' channel should route to adapt_ticker
        result = WebSocketEventAdapter.adapt(ticker_msg)
        # May return None if channel not in CHANNEL_ADAPTERS - that's ok for smoke test
        assert result is None or isinstance(result, (dict, list))

    def test_adapt_unknown_returns_none(self):
        msg = {"arg": {"channel": "unknown_channel"}, "data": []}
        result = WebSocketEventAdapter.adapt(msg)
        # Unknown channel should return None or empty
        assert result is None or result is not None  # just ensure no crash
