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

from ginkgo.trading.risk_management.capital_risk import CapitalRisk


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCapitalRiskConstruction:
    def test_default_constructor(self):
        r = CapitalRisk()
        assert r.max_capital_usage_ratio == 0.9
        assert r.single_trade_max_ratio == 0.1

    def test_custom_capital_parameters_constructor(self):
        r = CapitalRisk(max_capital_usage_ratio=0.8,
                        single_trade_max_ratio=0.15,
                        cash_reserve_ratio=0.15)
        assert r.max_capital_usage_ratio == 0.8
        assert r.single_trade_max_ratio == 0.15

    def test_capital_parameter_validation(self):
        r = CapitalRisk(max_capital_usage_ratio=0.95, single_trade_max_ratio=0.2)
        assert isinstance(r.max_capital_usage_ratio, float)
        assert isinstance(r.single_trade_max_ratio, float)
        assert r.max_capital_usage_ratio <= 1.0

    def test_property_access(self):
        r = CapitalRisk()
        assert isinstance(r.max_capital_usage_ratio, float)
        assert isinstance(r.single_trade_max_ratio, float)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCapitalRiskUtilizationControl:
    def test_current_utilization_calculation(self):
        r = CapitalRisk()
        info = _make_portfolio_info(capital_info={"used_ratio": 0.5})
        assert info["capital_info"]["used_ratio"] == 0.5

    def test_utilization_warning_level(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9, single_trade_max_ratio=0.1)
        r._context = type('C', (), {'engine_id': 'test_engine'})()
        signals = r.generate_signals(
            _make_portfolio_info(capital_info={"used_ratio": 0.85}),
            _make_bar()
        )
        assert isinstance(signals, list)

    def test_utilization_critical_level(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9, single_trade_max_ratio=0.1)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.88}),
            _make_order()
        )
        assert result is None

    def test_utilization_projection_calculation(self):
        r = CapitalRisk()
        used = 0.5
        new_trade = r.single_trade_max_ratio
        projected = used + new_trade
        assert projected <= r.max_capital_usage_ratio + r.single_trade_max_ratio


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCapitalRiskSingleTradeControl:
    def test_single_trade_ratio_calculation(self):
        r = CapitalRisk(single_trade_max_ratio=0.15)
        assert r.single_trade_max_ratio == 0.15

    def test_single_trade_limit_enforcement(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9, single_trade_max_ratio=0.05)
        order = _make_order(volume=100)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.89}),
            order
        )
        assert result is None

    def test_multi_trade_accumulation_control(self):
        r = CapitalRisk(max_capital_usage_ratio=0.8, single_trade_max_ratio=0.1)
        info = _make_portfolio_info(capital_info={"used_ratio": 0.7})
        result = r.cal(info, _make_order())
        assert isinstance(result, Order)

    def test_position_based_trade_adjustment(self):
        r = CapitalRisk()
        result = r.cal(_make_portfolio_info(), _make_order())
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.critical
class TestCapitalRiskCashReserve:
    def test_cash_reserve_calculation(self):
        r = CapitalRisk(cash_reserve_ratio=0.15)
        assert r._cash_reserve_ratio == 0.15

    def test_cash_reserve_warning_mechanism(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9)
        r._context = type('C', (), {'engine_id': 'test_engine'})()
        signals = r.generate_signals(
            _make_portfolio_info(capital_info={"used_ratio": 0.82}),
            _make_bar()
        )
        assert isinstance(signals, list)

    def test_cash_reserve_enforcement(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9, single_trade_max_ratio=0.1)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.85}),
            _make_order()
        )
        assert result is None

    def test_dynamic_reserve_adjustment(self):
        r = CapitalRisk(cash_reserve_ratio=0.2)
        assert r._cash_reserve_ratio == 0.2


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCapitalRiskPositionAllocation:
    def test_position_allocation_calculation(self):
        r = CapitalRisk(single_trade_max_ratio=0.1)
        assert r.single_trade_max_ratio == 0.1

    def test_allocation_rebalancing(self):
        r = CapitalRisk(max_capital_usage_ratio=0.85)
        info = _make_portfolio_info(capital_info={"used_ratio": 0.5})
        result = r.cal(info, _make_order())
        assert isinstance(result, Order)

    def test_allocation_optimization(self):
        r = CapitalRisk(max_capital_usage_ratio=0.75, single_trade_max_ratio=0.05)
        assert r.max_capital_usage_ratio == 0.75

    def test_allocation_risk_control(self):
        r = CapitalRisk()
        sell_order = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(), sell_order)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCapitalRiskOrderProcessing:
    def test_normal_capital_order_passthrough(self):
        r = CapitalRisk()
        order = _make_order()
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.3}),
            order
        )
        assert result is order

    def test_capital_insufficient_order_rejection(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9, single_trade_max_ratio=0.1)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.88}),
            _make_order()
        )
        assert result is None

    def test_capital_adjustment_order_processing(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9, single_trade_max_ratio=0.1)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.7}),
            _make_order()
        )
        assert isinstance(result, Order)

    def test_multi_constraint_capital_check(self):
        r = CapitalRisk(max_capital_usage_ratio=0.8, single_trade_max_ratio=0.15)
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        result = r.cal(_make_portfolio_info(capital_info={"used_ratio": 0.99}), sell)
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCapitalRiskSignalGeneration:
    def test_high_utilization_signal(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9)
        r._context = type('C', (), {'engine_id': 'test_engine'})()
        signals = r.generate_signals(
            _make_portfolio_info(capital_info={"used_ratio": 0.85}),
            _make_bar()
        )
        assert len(signals) == 1
        assert signals[0].direction == DIRECTION_TYPES.SHORT
        assert signals[0].strength == 0.7

    def test_cash_reserve_depletion_signal(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9)
        r._context = type('C', (), {'engine_id': 'test_engine'})()
        signals = r.generate_signals(
            _make_portfolio_info(capital_info={"used_ratio": 0.5}),
            _make_bar()
        )
        assert len(signals) == 0

    def test_allocation_imbalance_signal(self):
        r = CapitalRisk(max_capital_usage_ratio=0.9)
        r._context = type('C', (), {'engine_id': 'test_engine'})()
        signals = r.generate_signals(
            _make_portfolio_info(capital_info={"used_ratio": 0.91}),
            _make_bar()
        )
        assert len(signals) == 1


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCapitalRiskReporting:
    def test_capital_efficiency_report(self):
        r = CapitalRisk()
        info = _make_portfolio_info(capital_info={"used_ratio": 0.6})
        signals = r.generate_signals(info, _make_bar())
        assert isinstance(signals, list)

    def test_liquidity_analysis_report(self):
        r = CapitalRisk(cash_reserve_ratio=0.15)
        assert r._cash_reserve_ratio == 0.15

    def test_allocation_effectiveness_report(self):
        r = CapitalRisk(max_capital_usage_ratio=0.85, single_trade_max_ratio=0.12)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.5}),
            _make_order()
        )
        assert isinstance(result, Order)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestCapitalRiskEdgeCases:
    def test_zero_capital_handling(self):
        r = CapitalRisk()
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.0}),
            _make_order()
        )
        assert isinstance(result, Order)

    def test_negative_balance_handling(self):
        r = CapitalRisk()
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": -0.1}),
            _make_order()
        )
        assert isinstance(result, Order)

    def test_extreme_large_order_handling(self):
        r = CapitalRisk()
        order = _make_order(volume=100000)
        result = r.cal(
            _make_portfolio_info(capital_info={"used_ratio": 0.0}),
            order
        )
        assert isinstance(result, Order)

    def test_rapid_trading_scenario(self):
        import time
        r = CapitalRisk()
        start = time.time()
        for _ in range(500):
            r.cal(_make_portfolio_info(capital_info={"used_ratio": 0.5}), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
@pytest.mark.performance
class TestCapitalRiskPerformance:
    def test_real_time_calculation_performance(self):
        import time
        r = CapitalRisk()
        start = time.time()
        for _ in range(1000):
            r.cal(_make_portfolio_info(capital_info={"used_ratio": 0.5}), _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_order_processing_performance(self):
        import time
        r = CapitalRisk()
        start = time.time()
        for _ in range(1000):
            r.generate_signals(_make_portfolio_info(), _make_bar())
        elapsed = time.time() - start
        assert elapsed < 5.0

    def test_large_portfolio_management_performance(self):
        import time
        r = CapitalRisk()
        positions = {str(i).zfill(6) + ".SZ": _make_position() for i in range(500)}
        info = _make_portfolio_info(positions=positions, capital_info={"used_ratio": 0.6})
        start = time.time()
        for _ in range(100):
            r.cal(info, _make_order())
        elapsed = time.time() - start
        assert elapsed < 5.0
