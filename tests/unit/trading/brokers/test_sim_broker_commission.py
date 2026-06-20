"""
SimBroker 佣金统一与部分成交 (issue #5492)

修复 _adjust_volume_for_funds 的两个问题:
1. 预检佣金与实际扣费(_calculate_commission)不一致 —— 卖单少算 0.1% 印花税
2. 全额资金不足时直接拒单(返回0), 不支持部分成交

A 股 volume 为 100 整数倍(ashare_broker.py:263 约定), 部分成交对齐 100 整手。
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ginkgo.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.trading.brokers.sim_broker import SimBroker


def _make_market_bar(close="9.5", high="10", low="9", limit_up="10.5", limit_down="8.5"):
    """构造带属性的市场数据 Bar (对齐生产 Bar 对象的 getattr 访问)

    submit_order_event:273 对市价单用 `getattr(market_data, 'close', 0)` 取价,
    dict 无 .close 属性会塌缩成 0 触发误判涨跌停; 必须用属性对象。
    """
    return SimpleNamespace(
        open=Decimal(close), high=Decimal(high), low=Decimal(low),
        close=Decimal(close), volume=1000000,
        limit_up=Decimal(limit_up), limit_down=Decimal(limit_down),
    )


def _make_order(code, direction, volume, frozen_money):
    """构造带冻结资金的市价单 Order (SimBroker 资金检查读 frozen_money)"""
    return Order(
        portfolio_id="p-001",
        engine_id="e-001",
        task_id="r-001",
        code=code,
        direction=direction,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.SUBMITTED,
        volume=volume,
        frozen_money=Decimal(str(frozen_money)),
    )


class TestAdjustVolumeForFunds:
    """_adjust_volume_for_funds 行为: 资金检查与部分成交"""

    def test_sufficient_funds_returns_full_volume(self):
        """资金充足: 返回全额 volume (tracer, 验证测试 harness)"""
        broker = SimBroker()
        # 1000股 @ 10.00: 本金 10000 + 佣金 max(10000*0.0003, 5)=30, 买入无印花税
        # total ≈ 10030, frozen 15000 充足
        order = _make_order("000001.SZ", DIRECTION_TYPES.LONG, 1000, 15000)
        vol = broker._adjust_volume_for_funds(order, Decimal("10.00"))
        assert vol == 1000

    def test_sell_partial_fill_when_insufficient_funds(self):
        """卖单资金不足全额: 部分成交, 对齐100整手, 佣金含印花税(_calculate_commission)

        10000股 @ 10.00 卖出: 全额 total = 100000 + 30(佣) + 100(印花) = 100130
        frozen=50000 远低于全额(含5%容差阈值95123.5) -> 部分成交
        max v 对齐100: total(4900)=49000+14.7+49=49063.7<=50000; total(5000)=50065>50000
        """
        broker = SimBroker()
        order = _make_order("000001.SZ", DIRECTION_TYPES.SHORT, 10000, 50000)
        vol = broker._adjust_volume_for_funds(order, Decimal("10.00"))
        assert vol == 4900

    def test_insufficient_for_one_lot_returns_zero(self):
        """资金不足一手(100股): 返回 0 (调用方据此 REJECTED)

        10000股 @ 10.00, frozen=500 连 100 股(本金1000+佣5=1005)都买不起
        """
        broker = SimBroker()
        order = _make_order("000001.SZ", DIRECTION_TYPES.LONG, 10000, 500)
        vol = broker._adjust_volume_for_funds(order, Decimal("10.00"))
        assert vol == 0

    def test_buy_partial_fill_uses_no_stamp_tax(self):
        """买单部分成交: 无印花税 (回归, 确认方向无关的部分成交)

        10000股 @ 10.00 买入: rate_per_share=10*(1+0.0003)=10.003
        frozen=50000 -> v_upper=4998 -> 对齐100=4900
        total(4900)=49000+14.7=49014.7<=50000; total(5000)=50015>50000 -> 4900
        """
        broker = SimBroker()
        order = _make_order("000001.SZ", DIRECTION_TYPES.LONG, 10000, 50000)
        vol = broker._adjust_volume_for_funds(order, Decimal("10.00"))
        assert vol == 4900


class TestSubmitOrderEventPartialFill:
    """端到端: submit_order_event 在部分成交时返回 FILLED (非 REJECTED)"""

    def test_market_order_partial_fill_returns_filled(self):
        """资金不足全额: submit_order_event 返回 FILLED, filled_volume 对齐100且小于全额"""
        broker = SimBroker(random_seed=42)
        broker._current_market_data = {"000001.SZ": _make_market_bar()}
        # 卖单 10000 股, frozen 40000 远不足全额(>90000) -> 部分成交
        order = Order(
            portfolio_id="p-001", engine_id="e-001", task_id="r-001",
            code="000001.SZ", direction=DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.MARKETORDER, status=ORDERSTATUS_TYPES.SUBMITTED,
            volume=10000, frozen_money=Decimal("40000"),
        )
        event = MagicMock()
        event.payload = order
        result = broker.submit_order_event(event)

        assert result.status == ORDERSTATUS_TYPES.FILLED
        assert 0 < result.filled_volume < order.volume
        assert result.filled_volume % 100 == 0

    def test_insufficient_for_one_lot_returns_rejected(self):
        """资金不足一手: submit_order_event 返回 REJECTED (部分成交下限保护)"""
        broker = SimBroker(random_seed=42)
        broker._current_market_data = {"000001.SZ": _make_market_bar()}
        # frozen=500 连 100 股(@~9.5)都买不起
        order = Order(
            portfolio_id="p-001", engine_id="e-001", task_id="r-001",
            code="000001.SZ", direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER, status=ORDERSTATUS_TYPES.SUBMITTED,
            volume=10000, frozen_money=Decimal("500"),
        )
        event = MagicMock()
        event.payload = order
        result = broker.submit_order_event(event)

        assert result.status == ORDERSTATUS_TYPES.REJECTED
