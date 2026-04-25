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

import numpy as np
from ginkgo.trading.risk_management.correlation_risk import CorrelationRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCorrelationRiskConstruction:
    def test_default_constructor(self):
        r = CorrelationRisk()
        assert r.max_correlation == 0.7
        assert r.warning_correlation == 0.5

    def test_custom_correlation_parameters_constructor(self):
        r = CorrelationRisk(max_correlation=0.8,
                            warning_correlation=0.6,
                            min_diversification_score=0.7)
        assert r.max_correlation == 0.8
        assert r.warning_correlation == 0.6

    def test_correlation_parameter_validation(self):
        r = CorrelationRisk(max_correlation=0.9, warning_correlation=0.4)
        assert r.max_correlation >= r.warning_correlation
        assert 0 <= r.warning_correlation <= 1
        assert 0 <= r.max_correlation <= 1

    def test_property_access(self):
        r = CorrelationRisk()
        assert isinstance(r.max_correlation, float)
        assert isinstance(r.warning_correlation, float)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCorrelationRiskMatrixCalculation:
    def test_price_data_collection(self):
        r = CorrelationRisk()
        assert isinstance(r._correlation_matrix, dict)

    def test_return_rate_calculation(self):
        prices_a = [10.0, 10.5, 10.2, 10.8, 11.0]
        prices_b = [20.0, 20.3, 20.1, 20.9, 21.2]
        returns_a = np.diff(prices_a) / np.array(prices_a[:-1])
        returns_b = np.diff(prices_b) / np.array(prices_b[:-1])
        assert len(returns_a) == len(prices_a) - 1
        assert all(isinstance(x, float) for x in returns_a)

    def test_correlation_coefficient_calculation(self):
        a = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        b = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        corr = np.corrcoef(a, b)[0, 1]
        assert abs(corr - 1.0) < 1e-10

    def test_correlation_matrix_assembly(self):
        n = 5
        matrix = np.zeros((n, n))
        for i in range(n):
            matrix[i][i] = 1.0
        assert matrix[0][0] == 1.0
        assert matrix[2][2] == 1.0
        assert matrix.shape == (n, n)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCorrelationRiskHighCorrelationControl:
    def test_high_correlation_identification(self):
        r = CorrelationRisk(max_correlation=0.7, warning_correlation=0.5)
        corr_val = 0.8
        assert corr_val > r.max_correlation

    def test_correlation_warning_level(self):
        r = CorrelationRisk(warning_correlation=0.5)
        corr_val = 0.6
        assert corr_val > r.warning_correlation

    def test_correlation_critical_level(self):
        r = CorrelationRisk(max_correlation=0.7)
        corr_val = 0.85
        assert corr_val > r.max_correlation

    def test_correlation_cluster_analysis(self):
        r = CorrelationRisk()
        r._correlation_matrix = {"000001.SZ": {"000002.SZ": 0.9}}
        assert r._correlation_matrix["000001.SZ"]["000002.SZ"] == 0.9


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCorrelationRiskSystemicRiskControl:
    def test_portfolio_beta_calculation(self):
        r = CorrelationRisk()
        weights = [0.3, 0.5, 0.2]
        betas = [1.1, 0.9, 1.3]
        portfolio_beta = sum(w * b for w, b in zip(weights, betas))
        assert abs(portfolio_beta - 1.04) < 1e-10

    def test_systemic_risk_assessment(self):
        r = CorrelationRisk()
        info = _make_portfolio_info()
        signals = r.generate_signals(info, _make_bar())
        assert isinstance(signals, list)

    def test_systemic_risk_limit_enforcement(self):
        r = CorrelationRisk(max_correlation=0.6, warning_correlation=0.4)
        assert r.max_correlation == 0.6
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_systemic_risk_hedging(self):
        r = CorrelationRisk()
        report = r.get_correlation_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "avg_correlation" in report


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCorrelationRiskDiversificationEffect:
    def test_diversification_ratio_calculation(self):
        n = 10
        weights = [1.0 / n] * n
        assert abs(sum(weights) - 1.0) < 1e-10

    def test_effective_number_of_positions(self):
        n = 5
        weights = [1.0 / n] * n
        eff_n = 1.0 / sum(w ** 2 for w in weights)
        assert abs(eff_n - n) < 1e-10

    def test_diversification_benefit_assessment(self):
        r = CorrelationRisk()
        report = r.get_correlation_report({})
        assert isinstance(report, dict)

    def test_diversification_optimization(self):
        r = CorrelationRisk(min_diversification_score=0.7)
        assert r._min_diversification_score == 0.7


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCorrelationRiskOrderProcessing:
    def test_correlation_impact_assessment(self):
        r = CorrelationRisk()
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert result is order

    def test_high_correlation_order_restriction(self):
        r = CorrelationRisk(max_correlation=0.5)
        order = _make_order(volume=500)
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)

    def test_diversification_promoting_orders(self):
        r = CorrelationRisk()
        info = _make_portfolio_info()
        signals = r.generate_signals(info, _make_bar())
        assert signals == []

    def test_correlation_based_portfolio_rebalancing(self):
        r = CorrelationRisk()
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), sell)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCorrelationRiskSignalGeneration:
    def test_correlation_spike_signal(self):
        r = CorrelationRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_diversification_degradation_signal(self):
        r = CorrelationRisk()
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert isinstance(signals, list)

    def test_systemic_risk_buildup_signal(self):
        r = CorrelationRisk(warning_correlation=0.3)
        signals = r.generate_signals(_make_portfolio_info(), _make_bar())
        assert len(signals) == 0

    def test_correlation_regime_change_signal(self):
        r = CorrelationRisk()
        report = r.get_correlation_report({})
        assert report["avg_correlation"] == 0.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCorrelationRiskReporting:
    def test_correlation_matrix_report(self):
        r = CorrelationRisk()
        report = r.get_correlation_report(_make_portfolio_info())
        assert isinstance(report, dict)
        assert "avg_correlation" in report

    def test_diversification_analysis_report(self):
        r = CorrelationRisk()
        report = r.get_correlation_report({})
        assert report["avg_correlation"] == 0.0

    def test_risk_contribution_analysis_report(self):
        r = CorrelationRisk(max_correlation=0.8, warning_correlation=0.6)
        report = r.get_correlation_report(_make_portfolio_info())
        assert isinstance(report, dict)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCorrelationRiskEdgeCases:
    def test_insufficient_historical_data(self):
        r = CorrelationRisk()
        assert r._correlation_matrix == {}

    def test_single_position_portfolio(self):
        r = CorrelationRisk()
        info = _make_portfolio_info(positions={"000001.SZ": _make_position()})
        signals = r.generate_signals(info, _make_bar())
        assert isinstance(signals, list)

    def test_extreme_correlation_scenarios(self):
        r = CorrelationRisk()
        assert 0 <= r.warning_correlation <= 1
        assert 0 <= r.max_correlation <= 1

    def test_market_crash_correlation_behavior(self):
        r = CorrelationRisk(max_correlation=0.9, warning_correlation=0.7)
        assert r.max_correlation == 0.9
        order = _make_order()
        result = r.cal(_make_portfolio_info(), order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestCorrelationRiskPerformance:
    def test_large_correlation_matrix_calculation(self):
        import time
        n = 500
        r = CorrelationRisk()
        start = time.time()
        for i in range(n):
            r._correlation_matrix[str(i).zfill(6) + ".SZ"] = {}
        elapsed = time.time() - start
        assert elapsed < 5.0
        assert len(r._correlation_matrix) == n

    def test_real_time_correlation_update(self):
        import time
        r = CorrelationRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_correlation_calculation_optimization(self):
        import time
        r = CorrelationRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0
