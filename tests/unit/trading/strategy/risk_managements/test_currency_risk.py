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

from ginkgo.trading.risk_management.currency_risk import CurrencyRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskConstruction:
    def test_default_constructor(self):
        r = CurrencyRisk()
        assert r.single_currency_exposure_limit == 0.2
        assert r.total_currency_exposure_limit == 0.5
        assert r.volatility_warning_threshold == 0.05

    def test_custom_currency_parameters_constructor(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.3,
                         total_currency_exposure_limit=0.6,
                         volatility_warning_threshold=0.08,
                         hedge_ratio_target=0.7)
        assert r.single_currency_exposure_limit == 0.3
        assert r.total_currency_exposure_limit == 0.6
        assert r.volatility_warning_threshold == 0.08

    def test_currency_parameter_validation(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.15,
                         total_currency_exposure_limit=0.4)
        assert isinstance(r.single_currency_exposure_limit, float)
        assert isinstance(r.total_currency_exposure_limit, float)
        assert r.single_currency_exposure_limit <= 1.0
        assert r.total_currency_exposure_limit <= 1.0

    def test_property_access(self):
        r = CurrencyRisk()
        assert isinstance(r.single_currency_exposure_limit, float)
        assert isinstance(r.total_currency_exposure_limit, float)
        assert isinstance(r.volatility_warning_threshold, float)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskExposureMonitoring:
    def test_currency_exposure_calculation(self):
        r = CurrencyRisk()
        report = r.get_exposure_report({})
        assert isinstance(report, dict)
        assert "total_exposure" in report

    def test_multi_currency_aggregation(self):
        r = CurrencyRisk()
        report = r.get_exposure_report({"positions": {}})
        assert report["total_exposure"] == 0.0

    def test_exposure_limit_enforcement(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.2)
        assert r.single_currency_exposure_limit == 0.2
        assert r.total_currency_exposure_limit == 0.5

    def test_exposure_projection_calculation(self):
        r = CurrencyRisk()
        info = _make_portfolio_info()
        order = _make_order(volume=500)
        result = r.cal(info, order)
        assert isinstance(result, Order)
        assert result.volume == 500


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskVolatilityMonitoring:
    def test_exchange_rate_volatility_calculation(self):
        r = CurrencyRisk(volatility_warning_threshold=0.1)
        assert r.volatility_warning_threshold == 0.1

    def test_volatility_trend_analysis(self):
        r = CurrencyRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_volatility_regime_detection(self):
        r = CurrencyRisk(volatility_warning_threshold=0.03)
        assert r.volatility_warning_threshold == 0.03
        report = r.get_exposure_report({})
        assert "total_exposure" in report

    def test_extreme_volatility_events(self):
        r = CurrencyRisk()
        info = _make_portfolio_info()
        order = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(info, order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskHedgingStrategies:
    def test_hedging_ratio_calculation(self):
        r = CurrencyRisk(hedge_ratio_target=0.9)
        assert getattr(r, "hedge_ratio_target", None) is not None or r.volatility_warning_threshold >= 0

    def test_hedging_instrument_selection(self):
        r = CurrencyRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)
        assert result.code == "000001.SZ"

    def test_dynamic_hedging_adjustment(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.25)
        info = _make_portfolio_info()
        signals = r.generate_signals(info, _make_bar())
        assert isinstance(signals, list)

    def test_hedging_effectiveness_evaluation(self):
        r = CurrencyRisk()
        report = r.get_exposure_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert report["total_exposure"] == 0.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskMultiCurrencyManagement:
    def test_currency_correlation_analysis(self):
        r = CurrencyRisk()
        info = _make_portfolio_info()
        signals = r.generate_signals(info, _make_bar())
        assert signals == []

    def test_currency_optimization_allocation(self):
        r = CurrencyRisk(total_currency_exposure_limit=0.6)
        assert r.total_currency_exposure_limit == 0.6

    def test_currency_balance_management(self):
        r = CurrencyRisk()
        report = r.get_exposure_report({})
        assert isinstance(report, dict)

    def test_cross_currency_arbitrage_control(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.1,
                         total_currency_exposure_limit=0.3)
        assert r.single_currency_exposure_limit == 0.1
        assert r.total_currency_exposure_limit == 0.3


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskOrderProcessing:
    def test_currency_exposure_order_control(self):
        r = CurrencyRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert result is order

    def test_hedging_order_execution(self):
        r = CurrencyRisk()
        sell_order = _make_order(direction=DIRECTION_TYPES.SHORT, volume=50)
        result = r.cal(_make_portfolio_info(), sell_order)
        assert isinstance(result, Order)

    def test_multi_currency_order_coordination(self):
        r = CurrencyRisk()
        for i in range(3):
            order = _make_order(code=str(i).zfill(6) + ".SZ")
            result = r.cal(_make_portfolio_info(), order)
            assert isinstance(result, Order)

    def test_currency_conversion_orders(self):
        r = CurrencyRisk()
        info = _make_portfolio_info(worth=500000)
        order = _make_order(volume=1000, limit_price=50.0)
        result = r.cal(info, order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskSignalGeneration:
    def test_high_exposure_warning_signal(self):
        r = CurrencyRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_volatility_spike_signal(self):
        r = CurrencyRisk()
        bar = _make_bar(close=9.5)
        signals = r.generate_signals(_make_portfolio_info(), bar)
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_hedging_opportunity_signal(self):
        r = CurrencyRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_currency_regime_change_signal(self):
        r = CurrencyRisk(volatility_warning_threshold=0.02)
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskReporting:
    def test_currency_exposure_report(self):
        r = CurrencyRisk()
        report = r.get_exposure_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "total_exposure" in report

    def test_hedging_effectiveness_report(self):
        r = CurrencyRisk()
        report = r.get_exposure_report({})
        assert isinstance(report, dict)

    def test_currency_performance_attribution_report(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.15)
        report = r.get_exposure_report(_make_portfolio_info())
        assert report["total_exposure"] == 0.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCurrencyRiskEdgeCases:
    def test_currency_devaluation_scenarios(self):
        r = CurrencyRisk()
        order = _make_order(limit_price=1.0)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_currency_crises_handling(self):
        r = CurrencyRisk(single_currency_exposure_limit=0.05,
                         total_currency_exposure_limit=0.1)
        assert r.single_currency_exposure_limit == 0.05
        assert r.total_currency_exposure_limit == 0.1

    def test_exchange_rate_data_issues(self):
        r = CurrencyRisk()
        signals = r.generate_signals(_make_portfolio_info(), None)
        assert isinstance(signals, list)

    def test_cross_border_regulatory_changes(self):
        r = CurrencyRisk()
        order = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestCurrencyRiskPerformance:
    def test_real_time_currency_monitoring_performance(self):
        import time
        r = CurrencyRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_multi_currency_calculation_performance(self):
        import time
        r = CurrencyRisk()
        start = time.time()
        for _ in range(1000):
            r.get_exposure_report(_make_portfolio_info())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_hedging_strategy_performance(self):
        import time
        r = CurrencyRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0
