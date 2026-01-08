"""
PortfolioLive.on_order_filled() 单元测试

测试 PortfolioLive.on_order_filled() 方法：
1. 基础功能：处理 EventOrderPartiallyFilled 并更新持仓和现金
2. LONG 方向：创建新持仓或更新现有持仓
3. SHORT 方向：减少持仓并增加现金
4. 冻结资金处理
5. 手续费处理
6. 更新订单状态（transaction_volume, remain）
7. 异常处理
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, FREQUENCY_TYPES


class MockContext:
    """Mock context for testing Portfolio without engine binding"""
    def __init__(self, engine_id="test_engine", run_id="test_run"):
        self._engine_id = engine_id
        self._run_id = run_id

    @property
    def engine_id(self):
        return self._engine_id

    @property
    def run_id(self):
        return self._run_id


def create_portfolio_with_context(**kwargs):
    """Helper function to create PortfolioLive with mock context"""
    # Default values
    if 'uuid' not in kwargs:
        kwargs['uuid'] = 'test_portfolio'
    if 'engine_id' not in kwargs:
        kwargs['engine_id'] = 'test_engine'
    if 'run_id' not in kwargs:
        kwargs['run_id'] = 'test_run'

    portfolio = PortfolioLive(**kwargs)
    # Set mock context to provide engine_id and run_id
    portfolio._context = MockContext(engine_id=kwargs['engine_id'], run_id=kwargs['run_id'])
    return portfolio


@pytest.mark.unit
class TestPortfolioOnOrderFilledBasics:
    """测试 on_order_filled() 基础功能"""

    def test_on_order_filled_calls_on_order_partially_filled(self):
        """测试 on_order_filled() 调用 on_order_partially_filled()"""
        portfolio = create_portfolio_with_context()

        # Mock on_order_partially_filled 方法
        portfolio.on_order_partially_filled = Mock()

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        # 创建成交事件
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=100,
            fill_price=Decimal("10.5")
        )

        # 调用 on_order_filled
        portfolio.on_order_filled(event)

        # 验证调用了on_order_partially_filled
        portfolio.on_order_partially_filled.assert_called_once_with(event)

        print(f"✅ on_order_filled() 调用 on_order_partially_filled()")


@pytest.mark.unit
class TestPortfolioOrderPartiallyFilledLong:
    """测试 LONG 方向的订单成交处理"""

    def test_long_order_creates_new_position(self):
        """测试 LONG 订单成交创建新持仓"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0"),
            frozen_money=Decimal("1050")  # 100 * 10.5 (包含手续费)
        )

        # 冻结足够的现金（模拟订单创建时的冻结）
        # fill_cost = price * qty + fee = 10.5 * 100 + 5.25 = 1055.25
        portfolio._frozen = Decimal("1055.25")

        # 创建成交事件
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=100,
            fill_price=Decimal("10.5"),
            commission=Decimal("5.25")
        )

        # 处理订单成交
        portfolio.on_order_partially_filled(event)

        # 验证持仓被创建
        assert "000001.SZ" in portfolio._positions
        position = portfolio._positions["000001.SZ"]
        assert position.volume == 100
        assert position.price == Decimal("10.5")

        print(f"✅ LONG 订单成交创建新持仓")

    def test_long_order_updates_existing_position(self):
        """测试 LONG 订单成交更新现有持仓"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 创建现有持仓
        existing_position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            volume=100,
            cost=Decimal("10.0"),
            price=Decimal("10.5"),
            frozen=0,
            fee=Decimal("5.0")
        )
        portfolio._positions["000001.SZ"] = existing_position

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=50,
            limit_price=Decimal("11.0"),
            frozen_money=Decimal("550")  # 50 * 11.0
        )

        # 冻结足够的现金
        # fill_cost = price * qty + fee = 11.0 * 50 + 2.75 = 552.75
        portfolio._frozen = Decimal("552.75")

        # 创建成交事件
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=50,
            fill_price=Decimal("11.0"),
            commission=Decimal("2.75")
        )

        # 处理订单成交
        portfolio.on_order_partially_filled(event)

        # 验证持仓被更新
        assert "000001.SZ" in portfolio._positions
        position = portfolio._positions["000001.SZ"]
        # deal() 方法会累加成交量
        assert position.volume == 150  # 100 + 50

        print(f"✅ LONG 订单成交更新现有持仓")


@pytest.mark.unit
class TestPortfolioOrderPartiallyFilledShort:
    """测试 SHORT 方向的订单成交处理"""

    def test_short_order_adds_cash(self):
        """测试 SHORT 订单成交增加现金"""
        initial_cash = Decimal("100000")
        portfolio = create_portfolio_with_context(initial_cash=initial_cash)

        # 创建现有持仓（用于平仓）
        existing_position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            volume=100,
            cost=Decimal("10.0"),
            price=Decimal("10.5"),
            frozen=100,
            fee=Decimal("5.0")
        )
        portfolio._positions["000001.SZ"] = existing_position

        # 记录初始现金
        initial_cash_value = portfolio.cash

        # 创建一个真实的 Order 对象（SHORT）
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("11.0")
        )

        # 创建成交事件
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=100,
            fill_price=Decimal("11.0"),
            commission=Decimal("5.5")
        )

        # 处理订单成交
        portfolio.on_order_partially_filled(event)

        # 验证现金增加（卖出收入 - 手续费）
        expected_proceeds = Decimal("1100") - Decimal("5.5")  # 100 * 11.0 - 5.5
        expected_cash = initial_cash_value + expected_proceeds
        assert portfolio.cash == expected_cash

        print(f"✅ SHORT 订单成交增加现金")


@pytest.mark.unit
class TestPortfolioOrderStateUpdate:
    """测试订单状态更新"""

    def test_order_transaction_volume_updated(self):
        """测试 transaction_volume 被更新"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0"),
            frozen_money=Decimal("1050")
        )

        # 冻结足够的现金
        # First fill: 50 * 10.5 + 2.625 = 527.625
        # Second fill: 50 * 10.6 + 2.65 = 532.65
        # Total needed: 1060.275
        portfolio._frozen = Decimal("1060.275")

        # 初始 transaction_volume 应该为 0
        assert test_order.transaction_volume == 0

        # 创建第一次成交事件（成交50股）
        event1 = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=50,
            fill_price=Decimal("10.5"),
            commission=Decimal("2.625")
        )

        portfolio.on_order_partially_filled(event1)

        # 验证 transaction_volume 被更新
        assert test_order.transaction_volume == 50

        # 创建第二次成交事件（成交50股，完全成交）
        event2 = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=50,
            fill_price=Decimal("10.6"),
            commission=Decimal("2.65")
        )

        portfolio.on_order_partially_filled(event2)

        # 验证 transaction_volume 被更新到 100
        assert test_order.transaction_volume == 100

        print(f"✅ transaction_volume 正确更新")

    def test_order_remain_updated(self):
        """测试 remain 被正确更新"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0"),
            frozen_money=Decimal("1000")
        )

        # 冻结足够的现金
        # fill_cost = 100 * 10.0 + 5.0 = 1005
        portfolio._frozen = Decimal("1005")

        # 创建成交事件
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=100,
            fill_price=Decimal("10.0"),
            commission=Decimal("5.0")
        )

        portfolio.on_order_partially_filled(event)

        # 验证 remain 被更新
        # remain = frozen_money - fill_cost = 1005 - (100 * 10.0 + 5) = 0
        assert test_order.remain == Decimal("0")

        print(f"✅ remain 正确更新")


@pytest.mark.unit
class TestPortfolioOrderPartiallyFilledErrorHandling:
    """测试订单成交的异常处理"""

    def test_on_order_filled_ignores_invalid_quantity(self):
        """测试忽略无效的成交数量"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0")
        )

        # 创建成交事件（成交数量为0）
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=0,
            fill_price=Decimal("10.5")
        )

        # 记录初始持仓数量
        initial_positions_count = len(portfolio._positions)

        # 处理订单成交
        portfolio.on_order_partially_filled(event)

        # 验证没有创建新持仓
        assert len(portfolio._positions) == initial_positions_count

        print(f"✅ 无效成交数量被忽略")


@pytest.mark.unit
class TestPortfolioOrderFilledIntegration:
    """测试订单成交集成场景"""

    def test_full_order_fill_cycle(self):
        """测试完整的订单成交周期：创建订单 → 完全成交"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 创建一个真实的 Order 对象
        test_order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0"),
            frozen_money=Decimal("1000")
        )

        # 冻结足够的现金（一次性完全成交）
        # Fill: 100 * 10.5 + 5.25 = 1055.25
        portfolio._frozen = Decimal("1055.25")

        # 完全成交（100股）
        event = EventOrderPartiallyFilled(
            order=test_order,
            filled_quantity=100,
            fill_price=Decimal("10.5"),
            commission=Decimal("5.25")
        )

        portfolio.on_order_partially_filled(event)

        # 验证完全成交状态
        assert test_order.transaction_volume == 100
        assert test_order.remain == Decimal("0")

        # 验证持仓创建
        assert "000001.SZ" in portfolio._positions
        position = portfolio._positions["000001.SZ"]
        assert position.volume == 100

        print(f"✅ 完整订单成交周期测试通过")

    def test_multiple_orders_same_code(self):
        """测试同一代码的多笔订单成交"""
        portfolio = create_portfolio_with_context(initial_cash=100000)

        # 第一笔订单
        order1 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.0"),
            frozen_money=Decimal("1000")
        )

        # 冻结第一笔订单的现金
        # fill_cost = 100 * 10.5 + 5.25 = 1055.25
        portfolio._frozen = Decimal("1055.25")

        event1 = EventOrderPartiallyFilled(
            order=order1,
            filled_quantity=100,
            fill_price=Decimal("10.5"),
            commission=Decimal("5.25")
        )

        portfolio.on_order_partially_filled(event1)

        # 第二笔订单
        order2 = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=50,
            limit_price=Decimal("11.0"),
            frozen_money=Decimal("550")
        )

        # 冻结第二笔订单的现金（累加冻结）
        # fill_cost = 50 * 11.0 + 2.75 = 552.75
        portfolio._frozen += Decimal("552.75")

        event2 = EventOrderPartiallyFilled(
            order=order2,
            filled_quantity=50,
            fill_price=Decimal("11.0"),
            commission=Decimal("2.75")
        )

        portfolio.on_order_partially_filled(event2)

        # 验证持仓累加（150股）
        assert "000001.SZ" in portfolio._positions
        position = portfolio._positions["000001.SZ"]
        assert position.volume == 150

        print(f"✅ 多笔订单成交累加持仓")
