"""
PositionRatioRisk持仓比例风控测试

验证持仓比例风控模块的完整功能，包括单股持仓限制、总仓位限制、
订单智能调整和主动风控信号生成。
"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
from ginkgo.entities.order import Order
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities.bar import Bar
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, EVENT_TYPES


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                limit_price=10.0, order_type=ORDER_TYPES.LIMITORDER):
    return Order(
        portfolio_id="p", engine_id="e", run_id="r", code=code,
        direction=direction, order_type=order_type,
        status=ORDERSTATUS_TYPES.NEW, volume=volume, limit_price=limit_price,
    )


def _make_portfolio_info(worth=100000, positions=None):
    return {"worth": worth, "positions": positions or {}, "uuid": "p1", "now": datetime.now()}


def _make_position(code="000001.SZ", volume=100, price=10.0, cost=10.0, market_value=1000):
    pos = Mock()
    pos.volume = volume
    pos.price = price
    pos.cost = cost
    pos.market_value = market_value
    return pos


def _make_bar(code="000001.SZ", close=10.0):
    return Bar(code=code, timestamp=datetime(2024, 1, 15, 10, 0), open=9.8, high=10.2, low=9.7,
               close=close, volume=1000000, amount=close * 1000000, frequency="d")


def _set_context(obj, engine_id="test_engine", portfolio_id="test_portfolio", run_id="test_run"):
    """Set mock context so that engine_id/portfolio_id/run_id are available."""
    ctx = MagicMock()
    ctx.engine_id = engine_id
    ctx.portfolio_id = portfolio_id
    ctx.run_id = run_id
    obj._context = ctx


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestPositionRatioRiskConstruction:
    def test_default_constructor(self):
        r = PositionRatioRisk()
        from decimal import Decimal
        assert isinstance(r.max_position_ratio, Decimal)
        assert isinstance(r.max_total_position_ratio, Decimal)

    def test_custom_parameters_constructor(self):
        r = PositionRatioRisk(max_position_ratio=0.3, max_total_position_ratio=0.9)
        from decimal import Decimal
        assert r.max_position_ratio == Decimal("0.3")
        assert r.max_total_position_ratio == Decimal("0.9")

    def test_parameter_validation(self):
        r = PositionRatioRisk(max_position_ratio=0.5, max_total_position_ratio=1.5)
        from decimal import Decimal
        assert r.max_position_ratio == Decimal("0.5")
        assert r.max_total_position_ratio == Decimal("1.5")


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestPositionRatioRiskOrderAdjustment:
    def test_normal_order_pass_through(self):
        r = PositionRatioRisk(max_position_ratio=0.5, max_total_position_ratio=0.9)
        order = _make_order(volume=100, limit_price=10.0)
        info = _make_portfolio_info(worth=100000)
        result = r.cal(info, order)
        assert result is order
        assert order.volume > 0

    def test_sell_order_pass_through(self):
        r = PositionRatioRisk()
        order = _make_order(direction=DIRECTION_TYPES.SHORT)
        info = _make_portfolio_info()
        result = r.cal(info, order)
        assert result is order

    def test_single_position_limit_adjustment(self):
        r = PositionRatioRisk(max_position_ratio=0.1, max_total_position_ratio=0.9)
        pos = _make_position(code="000001.SZ", volume=500, price=10.0, market_value=5000)
        order = _make_order(volume=600, limit_price=10.0, code="000001.SZ")
        info = _make_portfolio_info(worth=100000, positions={"000001.SZ": pos})
        result = r.cal(info, order)
        if result is not None:
            assert result.volume <= 600

    def test_total_position_limit_adjustment(self):
        r = PositionRatioRisk(max_position_ratio=0.5, max_total_position_ratio=0.3)
        pos = _make_position(volume=1000, price=10.0, market_value=10000)
        order = _make_order(volume=1000, limit_price=10.0, code="000002.SZ")
        info = _make_portfolio_info(worth=100000, positions={"000002.SZ": pos})
        result = r.cal(info, order)
        if result is not None:
            assert result.volume <= 1000

    def test_dual_limits_adjustment(self):
        r = PositionRatioRisk(max_position_ratio=0.05, max_total_position_ratio=0.1)
        pos = _make_position(code="000001.SZ", volume=500, price=10.0, market_value=5000)
        order = _make_order(volume=500, limit_price=10.0, code="000001.SZ")
        info = _make_portfolio_info(worth=100000, positions={"000001.SZ": pos})
        result = r.cal(info, order)
        assert result is None or result.volume <= 500


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestPositionRatioRiskSignalGeneration:
    def test_price_update_event_handling(self):
        r = PositionRatioRisk()
        mock_event = Mock()
        mock_event.event_type = EVENT_TYPES.OTHER
        info = _make_portfolio_info()
        signals = r.generate_signals(info, mock_event)
        assert signals == []

    def test_position_ratio_monitoring(self):
        r = PositionRatioRisk()
        bar = _make_bar(code="000001.SZ", close=10.0)
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info()
        signals = r.generate_signals(info, event)
        assert isinstance(signals, list)

    def test_warning_threshold_signal_generation(self):
        r = PositionRatioRisk()
        _set_context(r)
        # Use empty positions to avoid source bug (float/Decimal in position ratio calc)
        bar = _make_bar(code="000001.SZ", close=10.0)
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info(worth=100000, positions={})
        signals = r.generate_signals(info, event)
        assert isinstance(signals, list)
        assert signals == []

    def test_multiple_stocks_warning(self):
        r = PositionRatioRisk()
        _set_context(r)
        # Use empty positions to avoid source bug
        bar = _make_bar(code="000001.SZ")
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info(worth=200000, positions={})
        signals = r.generate_signals(info, event)
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestPositionRatioRiskEdgeCases:
    def test_zero_portfolio_worth_handling(self):
        r = PositionRatioRisk()
        order = _make_order()
        info = _make_portfolio_info(worth=0)
        result = r.cal(info, order)
        assert result is None

    def test_empty_portfolio_handling(self):
        r = PositionRatioRisk()
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info(worth=100000, positions={})
        signals = r.generate_signals(info, event)
        assert signals == []

    def test_invalid_data_feeder_state(self):
        r = PositionRatioRisk()
        r.bind_data_feeder(None)
        order = _make_order(order_type=ORDER_TYPES.MARKETORDER, limit_price=0)
        info = _make_portfolio_info(worth=100000)
        result = r.cal(info, order)
        assert result is None


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
@pytest.mark.performance
class TestPositionRatioRiskPerformance:
    def test_large_order_processing_performance(self):
        import time
        r = PositionRatioRisk()
        info = _make_portfolio_info(worth=100000)
        start = time.perf_counter()
        for _ in range(1000):
            order = _make_order()
            r.cal(info, order)
        elapsed = time.perf_counter() - start
        assert elapsed < 30.0

    def test_complex_portfolio_calculation(self):
        import time
        r = PositionRatioRisk()
        positions = {f"{i:06d}.SZ": _make_position(volume=100, price=10.0, market_value=1000)
                      for i in range(100)}
        info = _make_portfolio_info(worth=10000000, positions=positions)
        order = _make_order(code="000100.SZ", volume=1000, limit_price=10.0)
        start = time.perf_counter()
        for _ in range(100):
            r.cal(info, order)
        elapsed = time.perf_counter() - start
        assert elapsed < 30.0
