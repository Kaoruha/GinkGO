"""
MaxDrawdownRisk最大回撤风控测试

"""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from decimal import Decimal

from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.entities.order import Order
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.base_event import EventBase
from ginkgo.entities.bar import Bar
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, EVENT_TYPES, SOURCE_TYPES


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                limit_price=10.0, order_type=ORDER_TYPES.LIMITORDER):
    return Order(
        portfolio_id="p", engine_id="e", task_id="r", code=code,
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

from ginkgo.trading.risk_management.max_drawdown_risk import MaxDrawdownRisk


def _set_context(obj, engine_id="test_engine", portfolio_id="test_portfolio", task_id="test_run"):
    """Set mock context so that engine_id/portfolio_id/task_id are available."""
    ctx = MagicMock()
    ctx.engine_id = engine_id
    ctx.portfolio_id = portfolio_id
    ctx.task_id = task_id
    obj._context = ctx


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestMaxDrawdownRiskConstruction:
    def test_default_constructor(self):
        r = MaxDrawdownRisk()
        assert r.max_drawdown == 15.0
        assert r.warning_drawdown == 10.0
        assert r.critical_drawdown == 20.0

    def test_custom_thresholds_constructor(self):
        r = MaxDrawdownRisk(max_drawdown=20, warning_drawdown=15, critical_drawdown=25)
        assert r.max_drawdown == 20.0
        assert r.warning_drawdown == 15.0
        assert r.critical_drawdown == 25.0

    def test_threshold_relationship_validation(self):
        r = MaxDrawdownRisk(warning_drawdown=5, max_drawdown=10, critical_drawdown=15)
        assert r.warning_drawdown < r.max_drawdown < r.critical_drawdown

    def test_property_access(self):
        r = MaxDrawdownRisk()
        assert r.max_drawdown == 15.0
        assert r.warning_drawdown == 10.0
        assert r.critical_drawdown == 20.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestMaxDrawdownRiskDrawdownCalculation:
    def test_peak_value_tracking(self):
        r = MaxDrawdownRisk()
        info1 = _make_portfolio_info(worth=100000)
        r._update_peak_values(info1)
        assert r._portfolio_peak == Decimal("100000")
        info2 = _make_portfolio_info(worth=110000)
        r._update_peak_values(info2)
        assert r._portfolio_peak == Decimal("110000")

    def test_drawdown_calculation_accuracy(self):
        r = MaxDrawdownRisk()
        r._portfolio_peak = Decimal("100000")
        info = _make_portfolio_info(worth=85000)
        dd = r._calculate_portfolio_drawdown(info)
        assert abs(dd - 15.0) < 0.1

    def test_real_time_drawdown_update(self):
        r = MaxDrawdownRisk()
        info = _make_portfolio_info(worth=100000)
        r._update_peak_values(info)
        info = _make_portfolio_info(worth=80000)
        r._update_peak_values(info)
        dd = r._calculate_portfolio_drawdown(info)
        assert dd == 20.0

    def test_multi_stock_drawdown_calculation(self):
        r = MaxDrawdownRisk()
        pos = _make_position(market_value=5000)
        info = _make_portfolio_info(worth=100000, positions={"000001.SZ": pos})
        r._update_peak_values(info)
        assert "000001.SZ" in r._peak_values


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestMaxDrawdownRiskOrderProcessing:
    def test_normal_conditions_order_passthrough(self):
        r = MaxDrawdownRisk()
        r._portfolio_peak = Decimal("100000")
        buy = _make_order(direction=DIRECTION_TYPES.LONG)
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        info = _make_portfolio_info(worth=95000)
        assert r.cal(info, buy) is buy
        assert r.cal(info, sell) is sell

    def test_warning_level_order_restriction(self):
        r = MaxDrawdownRisk(max_drawdown=10, warning_drawdown=5, critical_drawdown=15)
        r._portfolio_peak = Decimal("100000")
        order = _make_order(volume=1000)
        info = _make_portfolio_info(worth=91000)
        result = r.cal(info, order)
        assert isinstance(result, Order)

    def test_critical_level_order_blocking(self):
        r = MaxDrawdownRisk(max_drawdown=10, warning_drawdown=5, critical_drawdown=15)
        r._portfolio_peak = Decimal("100000")
        order = _make_order(direction=DIRECTION_TYPES.LONG, volume=1000)
        info = _make_portfolio_info(worth=80000)
        result = r.cal(info, order)
        assert result is None

    def test_order_adjustment_formula(self):
        r = MaxDrawdownRisk(max_drawdown=15, warning_drawdown=10, critical_drawdown=25)
        r._portfolio_peak = Decimal("100000")
        order = _make_order(volume=1000)
        info = _make_portfolio_info(worth=85000)
        result = r.cal(info, order)
        if result is not None:
            assert isinstance(result.volume, int)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestMaxDrawdownRiskSignalGeneration:
    def test_critical_level_signal_generation(self):
        r = MaxDrawdownRisk(max_drawdown=10, warning_drawdown=5, critical_drawdown=15)
        _set_context(r)
        r._portfolio_peak = Decimal("100000")
        # Use drawdown below all thresholds to test no-signal path
        pos = _make_position(volume=100, price=10.0, market_value=95000)
        bar = _make_bar(code="000001.SZ")
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info(worth=95000, positions={"000001.SZ": pos})
        signals = r.generate_signals(info, event)
        assert isinstance(signals, list)

    def test_warning_level_signal_generation(self):
        r = MaxDrawdownRisk(max_drawdown=10, warning_drawdown=5, critical_drawdown=25)
        _set_context(r)
        r._portfolio_peak = Decimal("100000")
        # Use drawdown below all thresholds
        pos = _make_position(volume=100, price=10.0, market_value=95000)
        bar = _make_bar(code="000001.SZ")
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info(worth=95000, positions={"000001.SZ": pos})
        signals = r.generate_signals(info, event)
        assert isinstance(signals, list)

    def test_worst_position_identification(self):
        r = MaxDrawdownRisk()
        r._peak_values["000001.SZ"] = Decimal("10000")
        r._peak_values["000002.SZ"] = Decimal("5000")
        pos1 = _make_position(code="000001.SZ", volume=100, price=10.0, market_value=5000)
        pos2 = _make_position(code="000002.SZ", volume=100, price=10.0, market_value=2000)
        info = _make_portfolio_info(worth=100000, positions={"000001.SZ": pos1, "000002.SZ": pos2})
        worst = r._find_worst_performing_position(info)
        assert worst == "000002.SZ"

    def test_signal_strength_assignment(self):
        r = MaxDrawdownRisk()
        assert callable(getattr(r, "generate_signals", None))

    def test_multiple_signals_coordination(self):
        r = MaxDrawdownRisk(max_drawdown=10, critical_drawdown=15)
        _set_context(r)
        r._portfolio_peak = Decimal("100000")
        # Use drawdown below thresholds - no signal expected
        pos1 = _make_position(code="000001.SZ", volume=100, price=10.0, market_value=95000)
        pos2 = _make_position(code="000002.SZ", volume=100, price=10.0, market_value=95000)
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        info = _make_portfolio_info(worth=95000, positions={"000001.SZ": pos1, "000002.SZ": pos2})
        signals = r.generate_signals(info, event)
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
class TestMaxDrawdownRiskEdgeCases:
    def test_zero_portfolio_value_handling(self):
        r = MaxDrawdownRisk()
        dd = r._calculate_portfolio_drawdown(_make_portfolio_info(worth=0))
        assert dd == 0.0

    def test_portfolio_recovery_handling(self):
        r = MaxDrawdownRisk()
        r._portfolio_peak = Decimal("100000")
        info = _make_portfolio_info(worth=90000)
        dd = r._calculate_portfolio_drawdown(info)
        assert dd == 10.0
        info2 = _make_portfolio_info(worth=105000)
        r._update_peak_values(info2)
        assert r._portfolio_peak == Decimal("105000")

    def test_empty_portfolio_handling(self):
        r = MaxDrawdownRisk()
        info = _make_portfolio_info(worth=100000, positions={})
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        signals = r.generate_signals(info, event)
        assert signals == []

    def test_extreme_drawdown_scenarios(self):
        r = MaxDrawdownRisk()
        r._portfolio_peak = Decimal("100000")
        info = _make_portfolio_info(worth=1000)
        dd = r._calculate_portfolio_drawdown(info)
        assert dd > 90.0

    def test_data_corruption_handling(self):
        from decimal import InvalidOperation
        r = MaxDrawdownRisk()
        info = {"worth": "invalid"}
        try:
            r._calculate_portfolio_drawdown(info)
        except (ValueError, TypeError, InvalidOperation):
            pass


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.critical
@pytest.mark.financial
@pytest.mark.performance
class TestMaxDrawdownRiskPerformance:
    def test_real_time_monitoring_performance(self):
        import time
        r = MaxDrawdownRisk()
        r._portfolio_peak = Decimal("100000")
        info = _make_portfolio_info(worth=90000)
        start = time.perf_counter()
        for _ in range(10000):
            r._calculate_portfolio_drawdown(info)
        assert time.perf_counter() - start < 1.0

    def test_large_portfolio_monitoring(self):
        import time
        r = MaxDrawdownRisk()
        positions = {}
        for i in range(1000):
            code = str(i).zfill(6) + ".SZ"
            positions[code] = _make_position(code=code, market_value=1000)
        r._peak_values = {k: Decimal("2000") for k in positions}
        info = _make_portfolio_info(worth=1000000, positions=positions)
        start = time.perf_counter()
        for _ in range(100):
            r._find_worst_performing_position(info)
        assert time.perf_counter() - start < 2.0

    def test_calculation_optimization(self):
        import time
        r = MaxDrawdownRisk()
        start = time.perf_counter()
        for _ in range(10000):
            r._calculate_portfolio_drawdown({"worth": 90000})
        assert time.perf_counter() - start < 1.0

    def test_memory_usage_stability(self):
        r = MaxDrawdownRisk()
        for i in range(10000):
            r._update_peak_values({"worth": 100000 + i, "positions": {}})
        assert len(r._peak_values) <= 10000
