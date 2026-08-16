# Issue: 前端 market/* 八端点 404——后端无路由
# Upstream: api.api.market（行情 4 端点 + 订阅 4 端点）
# Downstream: OKXMarketDataFeeder（行情直查）, MarketSubscriptionService（订阅 CRUD）
# Role: 端点契约——字段映射/float 化/盘口切片/订阅 CRUD/失败一律非 404（前端哨兵）

"""
market 端点测试

验证：
1. pairs：OKX 原生 instruments → snake_case + state/quote_ccy/search 过滤
2. tickers/ticker：字符串数值 float 化 + price/ts 别名
3. orderbook：条目 [p, sz, ...] 截取前两列
4. subscriptions CRUD×4：user_id 从 request.state 取、403/NotFound 映射、DELETE 204
5. 失败路径：一律 BusinessError（code≠404）——MarketData.vue 以 404 为
   "后端模块缺失"哨兵（停轮询断 WS），业务失败不得误触
6. feeder 单例：同 environment 复用同一实例
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


def run_async(coro):
    return asyncio.run(coro)


def _fake_request(user_uuid="u1"):
    return SimpleNamespace(state=SimpleNamespace(user_uuid=user_uuid))


class _FakeFeeder:
    """OKXMarketDataFeeder 桩：失败返回 {}/[]，与真实 feeder 一致"""

    def __init__(self, instruments=None, tickers=None, ticker=None, orderbook=None):
        self._instruments = instruments or []
        self._tickers = tickers or {}
        self._ticker = ticker or {}
        self._orderbook = orderbook or {}

    def get_instruments(self, inst_type="SPOT"):
        return self._instruments

    def get_all_tickers(self, inst_type="SPOT"):
        return self._tickers

    def get_ticker(self, symbol):
        return self._ticker

    def get_orderbook(self, symbol, depth=20):
        return self._orderbook


_INSTS = [
    {"instId": "BTC-USDT", "baseCcy": "BTC", "quoteCcy": "USDT", "state": "live",
     "listTime": "1597026383085", "tickSz": "0.1", "lotSz": "0.00000001", "minSz": "0.00001"},
    {"instId": "ETH-USDT", "baseCcy": "ETH", "quoteCcy": "USDT", "state": "live",
     "listTime": "1597026383085", "tickSz": "0.01", "lotSz": "0.001", "minSz": "0.001"},
    {"instId": "ETH-USD", "baseCcy": "ETH", "quoteCcy": "USD", "state": "live",
     "listTime": "1597026383085", "tickSz": "0.01", "lotSz": "1", "minSz": "1"},
    {"instId": "SUSP-USDT", "baseCcy": "SUSP", "quoteCcy": "USDT", "state": "suspend",
     "listTime": "1597026383085", "tickSz": "0.1", "lotSz": "1", "minSz": "1"},
]


class TestGetTradingPairs:
    def test_maps_and_filters(self):
        from api.market import get_trading_pairs

        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(instruments=_INSTS)):
            result = run_async(get_trading_pairs(
                exchange="okx", environment="production",
                quote_ccy="USDT", search="BTC",
            ))

        assert result["code"] == 0
        pairs = result["data"]["pairs"]
        assert [p["symbol"] for p in pairs] == ["BTC-USDT"]  # USD 计价与 suspend 均被滤掉
        assert pairs[0]["base_currency"] == "BTC" and pairs[0]["quote_currency"] == "USDT"
        assert pairs[0]["tick_size"] == "0.1"
        assert result["data"]["total"] == 1

    def test_empty_raises_business_error_not_404(self):
        from api.market import get_trading_pairs
        from core.exceptions import BusinessError

        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(instruments=[])):
            with pytest.raises(BusinessError) as exc_info:
                run_async(get_trading_pairs())
        assert exc_info.value.code != 404  # 前端 404 哨兵禁触

    def test_unsupported_exchange_rejected(self):
        from api.market import get_trading_pairs
        from core.exceptions import BusinessError

        with pytest.raises(BusinessError):
            run_async(get_trading_pairs(exchange="binance"))


class TestTickers:
    _RAW = {"BTC-USDT": {"symbol": "BTC-USDT", "last_price": "42000.5", "bid_price": "42000.1",
                         "ask_price": "42000.9", "open_24h": "41000", "high_24h": "43000",
                         "low_24h": "40500", "volume_24h": "123.45", "volume_ccy_24h": "5000000",
                         "timestamp": "1723000000000"}}

    def test_tickers_float_and_aliases(self):
        from api.market import get_all_tickers

        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(tickers=self._RAW)):
            result = run_async(get_all_tickers(exchange="okx"))

        t = result["data"]["tickers"]["BTC-USDT"]
        assert t["price"] == 42000.5 and isinstance(t["price"], float)
        assert t["last_price"] == 42000.5
        assert t["volume_24h"] == 123.45
        assert t["ts"] == "1723000000000" and t["timestamp"] == "1723000000000"
        assert result["data"]["total"] == 1

    def test_single_ticker(self):
        from api.market import get_ticker

        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(ticker=self._RAW["BTC-USDT"])):
            result = run_async(get_ticker("BTC-USDT", exchange="okx"))

        assert result["data"]["price"] == 42000.5

    def test_bad_number_becomes_zero(self):
        from api.market import get_ticker

        raw = dict(self._RAW["BTC-USDT"], last_price="N/A")
        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(ticker=raw)):
            result = run_async(get_ticker("BTC-USDT", exchange="okx"))

        assert result["data"]["price"] == 0.0

    def test_missing_ticker_not_404(self):
        from api.market import get_ticker
        from core.exceptions import BusinessError

        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(ticker={})):
            with pytest.raises(BusinessError) as exc_info:
                run_async(get_ticker("NOPE-USDT", exchange="okx"))
        assert exc_info.value.code != 404


class TestOrderbook:
    def test_slices_two_columns(self):
        from api.market import get_orderbook

        book = {"bids": [["42000.1", "0.5", "100", "2"], ["42000.0", "1.0", "200", "3"]],
                "asks": [["42000.9", "0.3", "50", "1"]], "ts": "1723000000000"}
        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(orderbook=book)):
            result = run_async(get_orderbook("BTC-USDT", exchange="okx", depth=20))

        assert result["data"]["bids"][0] == ["42000.1", "0.5"]  # 后两列丢弃
        assert len(result["data"]["bids"][0]) == 2
        assert result["data"]["asks"] == [["42000.9", "0.3"]]
        assert result["data"]["timestamp"] == "1723000000000"

    def test_empty_not_404(self):
        from api.market import get_orderbook
        from core.exceptions import BusinessError

        with patch("api.market.get_okx_feeder", return_value=_FakeFeeder(orderbook={})):
            with pytest.raises(BusinessError) as exc_info:
                run_async(get_orderbook("NOPE-USDT", exchange="okx"))
        assert exc_info.value.code != 404


def _sub_service():
    svc = MagicMock()
    svc.list_subscriptions.return_value = MagicMock(
        is_success=lambda: True,
        data={"subscriptions": [{"uuid": "s-1", "symbol": "BTC-USDT"}], "total": 1},
    )
    return svc


class TestSubscriptions:
    def test_list_passes_user_and_filters(self):
        from api.market import list_subscriptions

        svc = _sub_service()
        with patch("api.market.get_market_subscription_service", return_value=svc):
            result = run_async(list_subscriptions(
                _fake_request(), exchange="okx", environment="production", active_only=True,
            ))

        assert result["code"] == 0
        assert result["data"]["subscriptions"][0]["uuid"] == "s-1"
        kwargs = svc.list_subscriptions.call_args.kwargs
        assert kwargs["user_id"] == "u1" and kwargs["active_only"] is True

    def test_missing_auth_401(self):
        from fastapi import HTTPException
        from api.market import list_subscriptions

        with pytest.raises(HTTPException) as exc_info:
            run_async(list_subscriptions(_fake_request(user_uuid=None)))
        assert exc_info.value.status_code == 401

    def test_create_returns_envelope(self):
        from api.market import create_subscription, CreateSubscriptionRequest

        svc = MagicMock()
        svc.create_subscription.return_value = MagicMock(
            is_success=lambda: True, data={"uuid": "s-2", "symbol": "ETH-USDT"}
        )
        req = CreateSubscriptionRequest(exchange="okx", symbol="ETH-USDT")
        with patch("api.market.get_market_subscription_service", return_value=svc):
            result = run_async(create_subscription(req, _fake_request()))

        assert result["code"] == 0 and result["data"]["uuid"] == "s-2"
        kwargs = svc.create_subscription.call_args.kwargs
        assert kwargs["environment"] == "production"  # API 层默认 production

    def test_update_not_found_maps_404(self):
        from api.market import update_subscription, UpdateSubscriptionRequest
        from core.exceptions import NotFoundError

        svc = MagicMock()
        svc.update_subscription.return_value = MagicMock(
            is_success=lambda: False, error="Subscription not found: s-x"
        )
        req = UpdateSubscriptionRequest(is_active=False)
        with patch("api.market.get_market_subscription_service", return_value=svc):
            with pytest.raises(NotFoundError):
                run_async(update_subscription(req, "s-x", _fake_request()))

    def test_update_foreign_owner_maps_403(self):
        from api.market import update_subscription, UpdateSubscriptionRequest
        from core.exceptions import BusinessError

        svc = MagicMock()
        svc.update_subscription.return_value = MagicMock(
            is_success=lambda: False, error="无权访问该订阅"
        )
        req = UpdateSubscriptionRequest(is_active=False)
        with patch("api.market.get_market_subscription_service", return_value=svc):
            with pytest.raises(BusinessError) as exc_info:
                run_async(update_subscription(req, "s-1", _fake_request()))
        assert exc_info.value.code == 403

    def test_delete_success_returns_none(self):
        from api.market import delete_subscription

        svc = MagicMock()
        svc.delete_subscription.return_value = MagicMock(is_success=lambda: True)
        with patch("api.market.get_market_subscription_service", return_value=svc):
            result = run_async(delete_subscription("s-1", _fake_request()))

        assert result is None  # 204 空 body
        assert svc.delete_subscription.call_args.kwargs["user_id"] == "u1"

    def test_delete_not_found(self):
        from api.market import delete_subscription
        from core.exceptions import NotFoundError

        svc = MagicMock()
        svc.delete_subscription.return_value = MagicMock(
            is_success=lambda: False, error="Subscription not found: s-x"
        )
        with patch("api.market.get_market_subscription_service", return_value=svc):
            with pytest.raises(NotFoundError):
                run_async(delete_subscription("s-x", _fake_request()))


class TestFeederSingleton:
    def test_same_environment_reuses_instance(self):
        import api.market as market_mod

        with patch("ginkgo.trading.feeders.okx_feeder.OKXMarketDataFeeder") as cls:
            cls.side_effect = lambda environment=None: object()
            market_mod._OKX_FEEDERS.clear()
            f1 = market_mod.get_okx_feeder("production")
            f2 = market_mod.get_okx_feeder("production")
            f3 = market_mod.get_okx_feeder("testnet")

        assert f1 is f2
        assert f1 is not f3
        assert cls.call_count == 2  # production + testnet 各建一次
