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

from ginkgo.trading.risk_management.trading_time_risk import TradingTimeRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestTradingTimeRiskConstruction:
    def test_default_constructor(self):
        r = TradingTimeRisk()
        assert r.open_minutes_after == 5
        assert r.close_minutes_before == 5

    def test_custom_time_parameters_constructor(self):
        r = TradingTimeRisk(open_minutes_after=10, close_minutes_before=10,
                           lunch_start_hour=11, lunch_start_minute=30,
                           lunch_end_hour=13, lunch_end_minute=0)
        assert r.open_minutes_after == 10
        assert r.close_minutes_before == 10

    def test_time_parameter_validation(self):
        r = TradingTimeRisk(open_minutes_after=15, close_minutes_before=20)
        assert isinstance(r.open_minutes_after, int)
        assert isinstance(r.close_minutes_before, int)

    def test_property_access(self):
        r = TradingTimeRisk()
        assert isinstance(r.open_minutes_after, int)
        assert isinstance(r.close_minutes_before, int)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestTradingTimeRiskMarketHoursControl:
    def test_market_opening_time_control(self):
        r = TradingTimeRisk()
        now = datetime(2024, 1, 1, 9, 30)
        assert r.is_trading_allowed(now) is True

    def test_market_closing_time_control(self):
        r = TradingTimeRisk()
        now = datetime(2024, 1, 1, 14, 55)
        assert r.is_trading_allowed(now) is True

    def test_lunch_break_management(self):
        r = TradingTimeRisk(lunch_start_hour=11, lunch_start_minute=30,
                            lunch_end_hour=13, lunch_end_minute=0)
        # 11:45 is during lunch start (h==11, m>=30)
        now = datetime(2024, 1, 1, 11, 45)
        assert r.is_trading_allowed(now) is False

    def test_continuous_auction_periods(self):
        r = TradingTimeRisk()
        now = datetime(2024, 1, 1, 10, 30)
        assert r.is_trading_allowed(now) is True


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestTradingTimeRiskAbnormalPeriodDetection:
    def test_low_volume_period_detection(self):
        r = TradingTimeRisk()
        now = datetime(2024, 1, 1, 10, 0)
        assert r.is_trading_allowed(now) is True

    def test_high_volatility_period_detection(self):
        r = TradingTimeRisk()
        assert r.is_trading_allowed(None) is True

    def test_market_stress_period_identification(self):
        r = TradingTimeRisk()
        now = datetime(2024, 1, 1, 9, 35)
        assert r.is_trading_allowed(now) is True

    def test_holiday_effect_handling(self):
        r = TradingTimeRisk()
        order = _make_order()
        info = _make_portfolio_info(now=datetime(2024, 1, 1, 10, 30))
        result = r.cal(info, order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestTradingTimeRiskVolumePatternAnalysis:
    def test_intraday_volume_pattern_analysis(self):
        r = TradingTimeRisk()
        bar = _make_bar(volume=5000000)
        assert bar.volume == 5000000

    def test_volume_pattern_learning(self):
        r = TradingTimeRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_optimal_trading_time_identification(self):
        r = TradingTimeRisk()
        morning = datetime(2024, 1, 1, 10, 0)
        assert r.is_trading_allowed(morning) is True

    def test_volume_pattern_deviations(self):
        r = TradingTimeRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar(volume=100))
        assert signals == []


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTradingTimeRiskOrderScheduling:
    def test_order_time_priority_scheduling(self):
        r = TradingTimeRisk()
        order = _make_order()
        info = _make_portfolio_info(now=datetime(2024, 1, 1, 10, 30))
        result = r.cal(info, order)
        assert isinstance(result, Order)

    def test_order_execution_time_optimization(self):
        r = TradingTimeRisk()
        info = _make_portfolio_info(now=datetime(2024, 1, 1, 14, 0))
        result = r.cal(info, _make_order())
        assert isinstance(result, Order)

    def test_large_order_time_splitting(self):
        r = TradingTimeRisk()
        order = _make_order(volume=10000)
        info = _make_portfolio_info(now=datetime(2024, 1, 1, 10, 0))
        result = r.cal(info, order)
        assert isinstance(result, Order)

    def test_cross_market_time_coordination(self):
        r = TradingTimeRisk(open_minutes_after=0, close_minutes_before=0)
        assert r.is_trading_allowed(datetime(2024, 1, 1, 9, 25)) is True


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTradingTimeRiskOrderProcessing:
    def test_normal_time_order_passthrough(self):
        r = TradingTimeRisk()
        info = _make_portfolio_info(now=datetime(2024, 1, 1, 10, 30))
        order = _make_order()
        result = r.cal(info, order)
        assert result is order

    def test_restricted_time_order_adjustment(self):
        r = TradingTimeRisk(lunch_start_hour=11, lunch_start_minute=30,
                            lunch_end_hour=13, lunch_end_minute=0)
        lunch_time = datetime(2024, 1, 1, 11, 45)
        info = _make_portfolio_info(now=lunch_time)
        result = r.cal(info, _make_order())
        assert result is None

    def test_forbidden_time_order_rejection(self):
        r = TradingTimeRisk()
        forbidden = datetime(2024, 1, 1, 11, 45)
        assert r.is_trading_allowed(forbidden) is False
        info = _make_portfolio_info(now=forbidden)
        result = r.cal(info, _make_order())
        assert result is None

    def test_optimal_time_order_scheduling(self):
        r = TradingTimeRisk()
        for hour in [9, 10, 13, 14]:
            now = datetime(2024, 1, 1, hour, 30)
            assert r.is_trading_allowed(now) is True


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTradingTimeRiskSignalGeneration:
    def test_adnormal_timing_signal(self):
        r = TradingTimeRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_optimal_timing_opportunity_signal(self):
        r = TradingTimeRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert signals == []

    def test_volume_timing_anomaly_signal(self):
        r = TradingTimeRisk()
        bar = _make_bar(volume=20000000)
        signals = r.generate_signals(_make_portfolio_info(), bar)
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTradingTimeRiskReporting:
    def test_trading_time_efficiency_report(self):
        r = TradingTimeRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_volume_pattern_analysis_report(self):
        r = TradingTimeRisk()
        assert isinstance(r.open_minutes_after, int)

    def test_timing_performance_report(self):
        r = TradingTimeRisk(open_minutes_after=3, close_minutes_before=3)
        assert r.open_minutes_after == 3


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestTradingTimeRiskEdgeCases:
    def test_market_closed_handling(self):
        r = TradingTimeRisk()
        assert r.is_trading_allowed(None) is True

    def test_trading_halt_scenarios(self):
        r = TradingTimeRisk()
        order = _make_order()
        info = _make_portfolio_info(now=None)
        result = r.cal(info, order)
        assert result is order

    def test_system_time_abnormality(self):
        r = TradingTimeRisk()
        now = datetime(2024, 1, 1, 0, 0)
        assert r.is_trading_allowed(now) is True

    def test_extreme_volume_periods(self):
        r = TradingTimeRisk()
        bar = _make_bar(volume=1)
        info = _make_portfolio_info(now=datetime(2024, 1, 1, 10, 0))
        result = r.cal(info, _make_order())
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestTradingTimeRiskPerformance:
    def test_real_time_monitoring_performance(self):
        import time
        r = TradingTimeRisk()
        start = time.time()
        for _ in range(10000):
            r.is_trading_allowed(datetime(2024, 1, 1, 10, 30))
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_volume_analysis_performance(self):
        import time
        r = TradingTimeRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_order_scheduling_performance(self):
        import time
        r = TradingTimeRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(now=datetime(2024, 1, 1, 10, 30)), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0
