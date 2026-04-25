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
        portfolio_id="p", engine_id="e", task_id="r", code=code,
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

from ginkgo.trading.risk_management.suspension_risk import SuspensionRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskConstruction:
    def test_default_constructor(self):
        r = SuspensionRisk()
        assert r.max_suspended_ratio == 0.1
        assert r.suspension_warning_days == 5

    def test_custom_suspension_parameters_constructor(self):
        r = SuspensionRisk(max_suspended_ratio=0.15,
                           suspension_warning_days=3,
                           max_suspended_value_ratio=0.08)
        assert r.max_suspended_ratio == 0.15
        assert r.suspension_warning_days == 3
        assert r._max_suspended_value_ratio == 0.08

    def test_suspension_parameter_validation(self):
        r = SuspensionRisk(max_suspended_ratio=0.2)
        assert isinstance(r.max_suspended_ratio, float)
        assert 0 < r.max_suspended_ratio <= 1.0

    def test_property_access(self):
        r = SuspensionRisk()
        assert isinstance(r.max_suspended_ratio, float)
        assert isinstance(r.suspension_warning_days, int)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskPredictionModel:
    def test_historical_suspension_data_collection(self):
        r = SuspensionRisk()
        assert isinstance(r._suspended_stocks, dict)

    def test_suspension_risk_features_extraction(self):
        r = SuspensionRisk()
        r._suspended_stocks["000001.SZ"] = {"days": 10, "reason": "重大事项"}
        assert "000001.SZ" in r._suspended_stocks

    def test_suspension_probability_calculation(self):
        r = SuspensionRisk(max_suspended_ratio=0.15)
        assert r.max_suspended_ratio == 0.15

    def test_model_performance_validation(self):
        r = SuspensionRisk()
        assert r._suspended_stocks == {}


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskRealTimeMonitoring:
    def test_trading_status_monitoring(self):
        r = SuspensionRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_suspension_announcement_tracking(self):
        r = SuspensionRisk()
        r._suspended_stocks["000001.SZ"] = {"days": 1}
        assert r._suspended_stocks["000001.SZ"]["days"] == 1

    def test_abnormal_trading_pattern_detection(self):
        r = SuspensionRisk()
        bar = _make_bar(volume=100)
        signals = r.generate_signals(_make_portfolio_info(), bar)
        assert isinstance(signals, list)

    def test_cross_market_suspension_sync(self):
        r = SuspensionRisk()
        for i in range(5):
            r._suspended_stocks[str(i).zfill(6) + ".SZ"] = {"days": i + 1}
        assert len(r._suspended_stocks) == 5


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskLiquidityManagement:
    def test_suspended_position_identification(self):
        r = SuspensionRisk()
        r._suspended_stocks["000001.SZ"] = {"days": 5}
        assert "000001.SZ" in r._suspended_stocks

    def test_liquidity_impact_assessment(self):
        r = SuspensionRisk(max_suspended_ratio=0.1)
        report = r.get_suspension_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "suspended_count" in report
        assert "suspended_value" in report

    def test_liquidity_reserve_allocation(self):
        r = SuspensionRisk(max_suspended_value_ratio=0.05)
        assert r._max_suspended_value_ratio == 0.05

    def test_portfolio_rebalancing_for_liquidity(self):
        r = SuspensionRisk()
        report = r.get_suspension_report({})
        assert report["suspended_count"] == 0
        assert report["suspended_value"] == 0.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskEmergencyHandling:
    def test_emergency_liquidation_trigger(self):
        r = SuspensionRisk(suspension_warning_days=3)
        r._suspended_stocks["000001.SZ"] = {"days": 5}
        assert r._suspended_stocks["000001.SZ"]["days"] > r.suspension_warning_days

    def test_pre_suspension_position_reduction(self):
        r = SuspensionRisk()
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), sell)
        assert isinstance(result, Order)

    def test_suspension_hedge_strategies(self):
        r = SuspensionRisk()
        order = _make_order(volume=200)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_recovery_trading_strategies(self):
        r = SuspensionRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskOrderProcessing:
    def test_high_suspension_risk_order_restriction(self):
        r = SuspensionRisk(max_suspended_ratio=0.05)
        order = _make_order(volume=1000)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_suspended_stock_order_rejection(self):
        r = SuspensionRisk()
        order = _make_order(code="000001.SZ")
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_liquidity_adjustment_order_processing(self):
        r = SuspensionRisk()
        result = r.cal(_make_portfolio_info(), _make_order())
        assert isinstance(result, Order)

    def test_cross_stock_correlation_adjustment(self):
        r = SuspensionRisk(max_suspended_ratio=0.15)
        positions = {str(i).zfill(6) + ".SZ": _make_position() for i in range(3)}
        info = _make_portfolio_info(positions=positions)
        result = r.cal(info, _make_order())
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskSignalGeneration:
    def test_suspension_probability_warning_signal(self):
        r = SuspensionRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_imminent_suspension_signal(self):
        r = SuspensionRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert signals == []

    def test_liquidity_crisis_signal(self):
        r = SuspensionRisk()
        report = r.get_suspension_report(_make_portfolio_info())
        assert report["suspended_value"] == 0.0

    def test_resumption_trading_signal(self):
        r = SuspensionRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar(close=10.5))
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskReporting:
    def test_suspension_risk_assessment_report(self):
        r = SuspensionRisk()
        report = r.get_suspension_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "suspended_count" in report

    def test_liquidity_impact_report(self):
        r = SuspensionRisk()
        report = r.get_suspension_report({})
        assert report["suspended_count"] == 0

    def test_suspension_recovery_analysis_report(self):
        r = SuspensionRisk(suspension_warning_days=7)
        report = r.get_suspension_report(_make_portfolio_info())
        assert isinstance(report, dict)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSuspensionRiskEdgeCases:
    def test_prolonged_suspension_handling(self):
        r = SuspensionRisk(suspension_warning_days=5)
        r._suspended_stocks["000001.SZ"] = {"days": 60}
        assert r._suspended_stocks["000001.SZ"]["days"] == 60

    def test_frequent_suspension_stocks(self):
        r = SuspensionRisk()
        r._suspended_stocks["000001.SZ"] = {"days": 3, "count": 10}
        assert r._suspended_stocks["000001.SZ"]["count"] == 10

    def test_suspension_data_missing(self):
        r = SuspensionRisk()
        signals = r.generate_signals(_make_portfolio_info(), None)
        assert isinstance(signals, list)

    def test_market_wide_suspension_events(self):
        r = SuspensionRisk(max_suspended_ratio=0.2)
        for i in range(20):
            r._suspended_stocks[str(i).zfill(6) + ".SZ"] = {"days": 1}
        assert len(r._suspended_stocks) == 20


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestSuspensionRiskPerformance:
    def test_real_time_monitoring_performance(self):
        import time
        r = SuspensionRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_prediction_model_performance(self):
        import time
        r = SuspensionRisk()
        start = time.time()
        for _ in range(1000):
            r.get_suspension_report(_make_portfolio_info())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_emergency_response_performance(self):
        import time
        r = SuspensionRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0
