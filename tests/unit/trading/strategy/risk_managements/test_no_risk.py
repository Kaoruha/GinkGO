"""
NoRiskManagement无风控管理器测试

验证无风控管理器的基础功能和接口规范，
确保作为测试和基准对比的参考实现正确性。
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.risk_management.no_risk import NoRiskManagement
from ginkgo.entities.order import Order
from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities.bar import Bar
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, EVENT_TYPES


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                limit_price=10.0):
    return Order(
        portfolio_id="p", engine_id="e", run_id="r", code=code,
        direction=direction, order_type=ORDER_TYPES.LIMITORDER,
        status=ORDERSTATUS_TYPES.NEW, volume=volume, limit_price=limit_price,
    )


def _make_bar(code="000001.SZ", close=10.0):
    return Bar(code=code, timestamp=datetime(2024, 1, 15, 10, 0), open=9.8, high=10.2, low=9.7,
               close=close, volume=1000000, amount=close * 1000000, frequency="d")


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.unit
class TestNoRiskConstruction:
    def test_default_constructor(self):
        nr = NoRiskManagement()
        assert isinstance(nr, NoRiskManagement)
        assert isinstance(nr, BaseRiskManagement)

    def test_custom_name_constructor(self):
        nr = NoRiskManagement(name="CustomNoRisk")
        assert nr.name == "CustomNoRisk"

    def test_abstract_flag_setting(self):
        assert NoRiskManagement.__abstract__ is False
        nr = NoRiskManagement()
        assert isinstance(nr, NoRiskManagement)


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.unit
class TestNoRiskOrderProcessing:
    def test_order_passthrough_behavior(self):
        nr = NoRiskManagement()
        buy = _make_order(direction=DIRECTION_TYPES.LONG)
        sell = _make_order(direction=DIRECTION_TYPES.SHORT)
        assert nr.cal({}, buy) is buy
        assert nr.cal({}, sell) is sell

    def test_order_type_independence(self):
        nr = NoRiskManagement()
        lo = _make_order()
        lo.order_type = ORDER_TYPES.LIMITORDER
        mo = _make_order()
        mo.order_type = ORDER_TYPES.MARKETORDER
        assert nr.cal({}, lo) is lo
        assert nr.cal({}, mo) is mo

    def test_large_order_handling(self):
        nr = NoRiskManagement()
        big = _make_order(volume=999999999, limit_price=99999.99)
        result = nr.cal({}, big)
        assert result is big
        assert result.volume == 999999999


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.unit
class TestNoRiskSignalGeneration:
    def test_empty_signal_list_return(self):
        nr = NoRiskManagement()
        assert nr.generate_signals({}, Mock()) == []

    def test_event_type_independence(self):
        nr = NoRiskManagement()
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        assert nr.generate_signals({}, event) == []
        assert nr.generate_signals({}, EventBase()) == []

    def test_no_side_effects(self):
        nr = NoRiskManagement()
        order = _make_order()
        portfolio = {"key": "value"}
        orig_volume = order.volume
        nr.cal(portfolio, order)
        assert order.volume == orig_volume
        assert portfolio["key"] == "value"


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.unit
class TestNoRiskInterfaceCompliance:
    def test_method_signature_compliance(self):
        import inspect
        nr = NoRiskManagement()
        cal_sig = inspect.signature(nr.cal)
        gen_sig = inspect.signature(nr.generate_signals)
        assert "portfolio_info" in cal_sig.parameters
        assert "order" in cal_sig.parameters
        assert "portfolio_info" in gen_sig.parameters
        assert "event" in gen_sig.parameters

    def test_polymorphic_compatibility(self):
        nr = NoRiskManagement()
        base: BaseRiskManagement = nr
        order = _make_order()
        assert base.cal({}, order) is order
        assert base.generate_signals({}, Mock()) == []


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.unit
@pytest.mark.performance
class TestNoRiskPerformance:
    def test_order_processing_performance(self):
        import time
        nr = NoRiskManagement()
        order = _make_order()
        start = time.perf_counter()
        for _ in range(100000):
            nr.cal({}, order)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0

    def test_signal_generation_performance(self):
        import time
        nr = NoRiskManagement()
        start = time.perf_counter()
        for _ in range(100000):
            nr.generate_signals({}, Mock())
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0
