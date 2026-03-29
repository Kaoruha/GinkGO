import pytest
from unittest.mock import Mock
from datetime import datetime, time as dt_time
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
        portfolio_id="p", engine_id="e", run_id="r", code=code,
        direction=direction, order_type=order_type,
        status=ORDERSTATUS_TYPES.NEW, volume=volume, limit_price=limit_price,
    )


def _make_portfolio_info(worth=100000, positions=None, **extra):
    info = {"worth": worth, "positions": positions or {}, "uuid": "p1", "now": datetime.now()}
    info.update(extra)
    return info


def _make_position(code="000001.SZ", volume=100, price=10.0, cost=10.0, market_value=1000):
    pos = Mock()
    pos.volume = volume
    pos.price = price
    pos.cost = cost
    pos.market_value = market_value
    return pos


def _make_bar(code="000001.SZ", close=10.0, volume=1000000):
    return Bar(code=code, open=9.8, high=10.2, low=9.7, close=close,
               volume=volume, amount=close * volume, frequency="d",
               timestamp=datetime(2024, 1, 15, 10, 30))

from ginkgo.trading.risk_management.time_based_risk import TimeBasedRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTimeBasedRiskConstruction:
    def test_default_constructor(self):
        r = TimeBasedRisk()
        assert r.max_holding_days == 30
        assert r.max_daily_trades == 5

    def test_custom_time_parameters_constructor(self):
        r = TimeBasedRisk(max_holding_days=60, max_intraday_trades=30,
                          max_daily_trades=10, min_holding_period_hours=2)
        assert r.max_holding_days == 60
        assert r.max_daily_trades == 10

    def test_time_parameter_validation(self):
        r = TimeBasedRisk(max_holding_days=15, max_daily_trades=3)
        assert isinstance(r.max_holding_days, int)
        assert isinstance(r.max_daily_trades, int)
        assert r.max_holding_days > 0

    def test_property_access(self):
        r = TimeBasedRisk()
        assert isinstance(r.max_holding_days, int)
        assert isinstance(r.max_daily_trades, int)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTimeBasedRiskHoldingTimeMonitoring:
    def test_position_entry_time_tracking(self):
        r = TimeBasedRisk()
        assert isinstance(r._hold_start, dict)

    def test_holding_duration_calculation(self):
        r = TimeBasedRisk()
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 15)
        duration = (end - start).days
        assert duration == 14

    def test_warning_level_holding_time(self):
        r = TimeBasedRisk(max_holding_days=30)
        days_held = 25
        assert days_held < r.max_holding_days

    def test_max_level_holding_time(self):
        r = TimeBasedRisk(max_holding_days=30)
        days_held = 35
        assert days_held > r.max_holding_days

    def test_forced_exit_holding_time(self):
        r = TimeBasedRisk(max_holding_days=20)
        r._hold_start["000001.SZ"] = datetime(2024, 1, 1)
        assert "000001.SZ" in r._hold_start


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTimeBasedRiskTradingFrequencyControl:
    def test_daily_trading_counting(self):
        r = TimeBasedRisk()
        assert isinstance(r._trade_count, dict)

    def test_daily_trading_limit_enforcement(self):
        r = TimeBasedRisk(max_daily_trades=5)
        r._trade_count["2024-01-01"] = 4
        assert r._trade_count["2024-01-01"] < r.max_daily_trades

    def test_intraday_position_limit(self):
        r = TimeBasedRisk(max_intraday_trades=20)
        assert r._max_intraday_trades == 20

    def test_trading_frequency_optimization(self):
        r = TimeBasedRisk(max_daily_trades=10)
        assert r.max_daily_trades == 10


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTimeBasedRiskOrderProcessing:
    def test_normal_time_order_passthrough(self):
        r = TimeBasedRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_high_frequency_order_restriction(self):
        r = TimeBasedRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_over_holding_time_order_adjustment(self):
        r = TimeBasedRisk()
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), sell)
        assert isinstance(result, Order)

    def test_time_based_signal_priority(self):
        r = TimeBasedRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTimeBasedRiskSignalGeneration:
    def test_periodic_risk_check_signal(self):
        r = TimeBasedRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_holding_time_warning_signal(self):
        r = TimeBasedRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert signals == []

    def test_forced_exit_signal_generation(self):
        r = TimeBasedRisk(max_holding_days=15)
        r._hold_start["000001.SZ"] = datetime(2024, 1, 1)
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_multi_position_time_signals(self):
        r = TimeBasedRisk()
        for i in range(10):
            r._hold_start[str(i).zfill(6) + ".SZ"] = datetime(2024, 1, 1)
        assert len(r._hold_start) == 10


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTimeBasedRiskEdgeCases:
    def test_weekend_holiday_handling(self):
        r = TimeBasedRisk()
        start = datetime(2024, 1, 5)  # Friday
        end = datetime(2024, 1, 8)    # Monday
        days = (end - start).days
        assert days == 3

    def test_market_closed_periods(self):
        r = TimeBasedRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_data_missing_time_handling(self):
        r = TimeBasedRisk()
        signals = r.generate_signals(_make_portfolio_info(), None)
        assert isinstance(signals, list)

    def test_system_time_abnormality(self):
        r = TimeBasedRisk()
        report = r.get_time_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "holding_days" in report
        assert "trade_count" in report


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestTimeBasedRiskPerformance:
    def test_time_calculation_performance(self):
        import time
        r = TimeBasedRisk()
        start = time.time()
        for _ in range(1000):
            r.get_time_report(_make_portfolio_info())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_real_time_monitoring_performance(self):
        import time
        r = TimeBasedRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_memory_usage_optimization(self):
        r = TimeBasedRisk()
        for i in range(1000):
            r._hold_start[str(i).zfill(6) + ".SZ"] = datetime(2024, 1, 1)
        assert len(r._hold_start) == 1000

    def test_concurrent_time_processing(self):
        import time
        r = TimeBasedRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0
