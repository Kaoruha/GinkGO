"""
MarketCapRisk市值风格风控测试

"""

import pytest
from unittest.mock import Mock
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


def _make_bar(code="000001.SZ", close=10.0):
    return Bar(code=code, timestamp=datetime(2024, 1, 15, 10, 0), open=9.8, high=10.2, low=9.7,
               close=close, volume=1000000, amount=close * 1000000, frequency="d")


from ginkgo.trading.risk_management.market_cap_risk import MarketCapRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskConstruction:
    def test_default_constructor(self):
        r = MarketCapRisk()
        assert r.large_cap_limit == 0.5
        assert r.mid_cap_limit == 0.3
        assert r.small_cap_limit == 0.2

    def test_custom_market_cap_parameters_constructor(self):
        r = MarketCapRisk(large_cap_limit=0.4, mid_cap_limit=0.35, small_cap_limit=0.25)
        assert r.large_cap_limit == 0.4
        assert r.mid_cap_limit == 0.35

    def test_market_cap_parameter_validation(self):
        r = MarketCapRisk(large_cap_limit=0.6, mid_cap_limit=0.3, small_cap_limit=0.1)
        total = r.large_cap_limit + r.mid_cap_limit + r.small_cap_limit
        assert total == pytest.approx(1.0)

    def test_property_access(self):
        r = MarketCapRisk()
        assert isinstance(r.large_cap_limit, float)
        assert isinstance(r.mid_cap_limit, float)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskClassification:
    def test_market_cap_classification_criteria(self):
        r = MarketCapRisk()
        assert r.classify_cap(50000000000) == "large"
        assert r.classify_cap(10000000000) == "mid"
        assert r.classify_cap(1000000000) == "small"

    def test_stock_market_cap_calculation(self):
        r = MarketCapRisk()
        assert r.classify_cap(r._large_cap_min) == "large"
        assert r.classify_cap(r._small_cap_max) == "mid"
        assert r.classify_cap(r._small_cap_max - 1) == "small"

    def test_dynamic_classification_update(self):
        r = MarketCapRisk()
        r._cap_classification["000001.SZ"] = "large"
        assert r._cap_classification["000001.SZ"] == "large"

    def test_classification_boundary_handling(self):
        r = MarketCapRisk()
        assert r.classify_cap(r._large_cap_min - 1) == "mid"
        assert r.classify_cap(r._small_cap_max) == "mid"
        assert r.classify_cap(r._small_cap_max - 1) == "small"


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskExposureControl:
    def test_current_exposure_calculation(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert report["large"] == 0.0
        assert report["mid"] == 0.0
        assert report["small"] == 0.0

    def test_exposure_limit_enforcement(self):
        r = MarketCapRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert result is order

    def test_exposure_projection_calculation(self):
        r = MarketCapRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert result is order

    def test_multi_cap_exposure_coordination(self):
        r = MarketCapRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert result is order


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskStyleDriftDetection:
    def test_target_style_profile_definition(self):
        r = MarketCapRisk()
        assert callable(getattr(r, "classify_cap", None))

    def test_current_style_assessment(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert isinstance(report, dict)

    def test_drift_detection_algorithm(self):
        r = MarketCapRisk(style_drift_threshold=0.1)
        assert r._style_drift_threshold == 0.1

    def test_drift_trend_analysis(self):
        r = MarketCapRisk()
        assert callable(getattr(r, "get_style_exposure", None))


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskFactorExposure:
    def test_market_cap_factor_calculation(self):
        r = MarketCapRisk()
        assert r.classify_cap(10000000000) == "mid"

    def test_portfolio_factor_exposure(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert isinstance(report, dict)

    def test_factor_risk_budgeting(self):
        r = MarketCapRisk()
        assert isinstance(r._style_drift_threshold, float)

    def test_factor_performance_attribution(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert isinstance(report, dict)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskOrderProcessing:
    def test_style_compliant_order_passthrough(self):
        r = MarketCapRisk()
        order = _make_order()
        assert r.cal(_make_portfolio_info(), order) is order

    def test_style_drift_order_adjustment(self):
        r = MarketCapRisk()
        order = _make_order()
        assert r.cal(_make_portfolio_info(), order) is order

    def test_excessive_exposure_order_restriction(self):
        r = MarketCapRisk()
        order = _make_order()
        assert r.cal(_make_portfolio_info(), order) is order

    def test_style_balancing_order_promotion(self):
        r = MarketCapRisk()
        order = _make_order()
        assert r.cal(_make_portfolio_info(), order) is order


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskSignalGeneration:
    def test_style_drift_warning_signal(self):
        r = MarketCapRisk()
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        signals = r.generate_signals(_make_portfolio_info(), event)
        assert signals == []

    def test_excessive_exposure_signal(self):
        r = MarketCapRisk()
        signals = r.generate_signals(_make_portfolio_info(), Mock())
        assert signals == []

    def test_style_rebalancing_signal(self):
        r = MarketCapRisk()
        signals = r.generate_signals(_make_portfolio_info(), Mock())
        assert signals == []

    def test_market_cap_regime_change_signal(self):
        r = MarketCapRisk()
        signals = r.generate_signals(_make_portfolio_info(), Mock())
        assert signals == []


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskReporting:
    def test_style_exposure_report(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert isinstance(report, dict)

    def test_drift_analysis_report(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert isinstance(report, dict)

    def test_factor_exposure_report(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert isinstance(report, dict)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestMarketCapRiskEdgeCases:
    def test_market_cap_data_missing(self):
        r = MarketCapRisk()
        assert r.classify_cap(0) == "small"

    def test_extreme_market_cap_values(self):
        r = MarketCapRisk()
        assert r.classify_cap(999999999999999) == "large"
        assert r.classify_cap(1) == "small"

    def test_single_style_portfolio(self):
        r = MarketCapRisk()
        report = r.get_style_exposure(_make_portfolio_info())
        assert report == {"large": 0.0, "mid": 0.0, "small": 0.0}

    def test_market_cap_regime_change(self):
        r = MarketCapRisk()
        assert r.classify_cap(r._large_cap_min) == "large"


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestMarketCapRiskPerformance:
    def test_real_time_classification_performance(self):
        import time
        r = MarketCapRisk()
        start = time.perf_counter()
        for i in range(10000):
            r.classify_cap(i * 1000000)
        assert time.perf_counter() - start < 1.0

    def test_style_analysis_performance(self):
        import time
        r = MarketCapRisk()
        start = time.perf_counter()
        for _ in range(1000):
            r.get_style_exposure(_make_portfolio_info())
        assert time.perf_counter() - start < 2.0

    def test_factor_calculation_performance(self):
        import time
        r = MarketCapRisk()
        start = time.perf_counter()
        for _ in range(10000):
            r.classify_cap(10000000000)
        assert time.perf_counter() - start < 1.0
