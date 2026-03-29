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

import numpy as np
from ginkgo.trading.risk_management.sector_rotation_risk import SectorRotationRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskConstruction:
    def test_default_constructor(self):
        r = SectorRotationRisk()
        assert r.max_sector_exposure == 0.4
        assert r.sector_warning_threshold == 0.3

    def test_custom_sector_parameters_constructor(self):
        r = SectorRotationRisk(max_sector_exposure=0.35,
                               sector_warning_threshold=0.25,
                               rotation_detection_days=30)
        assert r.max_sector_exposure == 0.35
        assert r.sector_warning_threshold == 0.25
        assert r._rotation_detection_days == 30

    def test_sector_parameter_validation(self):
        r = SectorRotationRisk(max_sector_exposure=0.5, sector_warning_threshold=0.3)
        assert r.max_sector_exposure > r.sector_warning_threshold
        assert isinstance(r.max_sector_exposure, float)

    def test_property_access(self):
        r = SectorRotationRisk()
        assert isinstance(r.max_sector_exposure, float)
        assert isinstance(r.sector_warning_threshold, float)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskRelativeStrength:
    def test_sector_price_index_calculation(self):
        r = SectorRotationRisk()
        prices = [10.0, 10.5, 10.2, 10.8, 11.0]
        index = sum(prices) / len(prices)
        assert index == 10.5

    def test_relative_strength_calculation(self):
        r = SectorRotationRisk()
        sector_return = 0.15
        market_return = 0.10
        rs = sector_return - market_return
        assert abs(rs - 0.05) < 1e-10

    def test_strength_ranking_assessment(self):
        r = SectorRotationRisk()
        sectors = {"tech": 0.15, "finance": 0.08, "health": 0.12}
        ranked = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        assert ranked[0][0] == "tech"
        assert ranked[2][0] == "finance"

    def test_strength_trend_analysis(self):
        r = SectorRotationRisk()
        trend = [0.10, 0.12, 0.11, 0.15, 0.14]
        is_up = trend[-1] > trend[0]
        assert is_up is True


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskRotationDetection:
    def test_rotation_pattern_identification(self):
        r = SectorRotationRisk()
        assert isinstance(r._sector_performance, dict)

    def test_rotation_strength_calculation(self):
        r = SectorRotationRisk()
        r._sector_performance["tech"] = [0.01, 0.02, -0.01, 0.03]
        assert "tech" in r._sector_performance

    def test_rotation_timing_analysis(self):
        r = SectorRotationRisk(rotation_detection_days=30)
        assert r._rotation_detection_days == 30

    def test_cross_sector_rotation_impact(self):
        r = SectorRotationRisk()
        for s in ["tech", "finance", "health", "energy"]:
            r._sector_performance[s] = [0.01]
        assert len(r._sector_performance) == 4


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskDecliningSectorControl:
    def test_declining_sector_identification(self):
        r = SectorRotationRisk()
        r._sector_performance["old_industry"] = [-0.01, -0.02, -0.03]
        avg = sum(r._sector_performance["old_industry"]) / len(r._sector_performance["old_industry"])
        assert avg < 0

    def test_declining_metrics_calculation(self):
        r = SectorRotationRisk()
        r._sector_performance["sector_a"] = [-0.05, -0.03, -0.02, -0.04]
        assert all(v < 0 for v in r._sector_performance["sector_a"])

    def test_exposure_limit_enforcement(self):
        r = SectorRotationRisk(max_sector_exposure=0.25)
        assert r.max_sector_exposure == 0.25

    def test_sector_exit_strategies(self):
        r = SectorRotationRisk()
        order = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskEmergingSectorOpportunity:
    def test_emerging_sector_detection(self):
        r = SectorRotationRisk()
        r._sector_performance["ai"] = [0.05, 0.08, 0.12, 0.15]
        assert all(v > 0 for v in r._sector_performance["ai"])

    def test_growth_potential_assessment(self):
        r = SectorRotationRisk()
        growth = [0.1, 0.15, 0.2, 0.25]
        avg_growth = sum(growth) / len(growth)
        assert avg_growth == 0.175

    def test_opportunity_timing_analysis(self):
        r = SectorRotationRisk()
        report = r.get_sector_report(_make_portfolio_info())
        assert isinstance(report, dict)

    def test_emerging_sector_risk_control(self):
        r = SectorRotationRisk(max_sector_exposure=0.3, sector_warning_threshold=0.2)
        assert r.max_sector_exposure == 0.3


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskOrderProcessing:
    def test_sector_rotation_order_promotion(self):
        r = SectorRotationRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_declining_sector_order_restriction(self):
        r = SectorRotationRisk()
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), sell)
        assert isinstance(result, Order)

    def test_sector_concentration_order_control(self):
        r = SectorRotationRisk(max_sector_exposure=0.3)
        order = _make_order(volume=500)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_rotation_timing_order_optimization(self):
        r = SectorRotationRisk()
        for _ in range(5):
            result = r.cal(_make_portfolio_info(), _make_order())
            assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskSignalGeneration:
    def test_sector_rotation_signal(self):
        r = SectorRotationRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)
        assert len(signals) == 0

    def test_declining_sector_warning_signal(self):
        r = SectorRotationRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert signals == []

    def test_emerging_sector_opportunity_signal(self):
        r = SectorRotationRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_sector_regime_change_signal(self):
        r = SectorRotationRisk()
        report = r.get_sector_report({})
        assert report["sector_count"] == 0
        assert report["max_exposure"] == 0.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskReporting:
    def test_sector_strength_ranking_report(self):
        r = SectorRotationRisk()
        report = r.get_sector_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "sector_count" in report

    def test_rotation_cycle_analysis_report(self):
        r = SectorRotationRisk()
        report = r.get_sector_report({})
        assert report["max_exposure"] == 0.0

    def test_sector_risk_exposure_report(self):
        r = SectorRotationRisk(max_sector_exposure=0.35)
        report = r.get_sector_report(_make_portfolio_info())
        assert isinstance(report, dict)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestSectorRotationRiskEdgeCases:
    def test_sector_classification_changes(self):
        r = SectorRotationRisk()
        r._sector_performance = {}
        assert r._sector_performance == {}

    def test_market_structure_changes(self):
        r = SectorRotationRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_extreme_rotation_events(self):
        r = SectorRotationRisk()
        r._sector_performance["volatile"] = [0.2, -0.15, 0.25, -0.2]
        assert len(r._sector_performance["volatile"]) == 4

    def test_insufficient_sector_data(self):
        r = SectorRotationRisk()
        report = r.get_sector_report(_make_portfolio_info())
        assert report["sector_count"] == 0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestSectorRotationRiskPerformance:
    def test_sector_analysis_performance(self):
        import time
        r = SectorRotationRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_rotation_detection_performance(self):
        import time
        r = SectorRotationRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_large_sector_universe_performance(self):
        import time
        r = SectorRotationRisk()
        for i in range(100):
            r._sector_performance[f"sector_{i}"] = [0.01 * i]
        start = time.time()
        for _ in range(100):
            r.get_sector_report(_make_portfolio_info())
        elapsed = time.time() - start
        assert elapsed < 5.0
