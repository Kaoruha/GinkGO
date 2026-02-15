"""
交易实体工厂测试 - Pytest重构版本

测试交易对象工厂的正确性和完整性，确保TDD测试数据的可靠性。

重构要点：
- 使用pytest fixtures共享测试资源
- 使用parametrize进行参数化测试
- 使用pytest.mark.unit和pytest.mark.fixtures标记
- 清晰的测试类分组
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import Mock

# 导入工厂类
from test.fixtures.trading_factories import (
    OrderFactory, PositionFactory, SignalFactory, EventFactory,
    PortfolioFactory, MarketScenarioFactory,
    EnhancedEventFactory, ProtocolTestFactory, MixinTestFactory
)
from ginkgo.enums import DIRECTION_TYPES


# ===== Fixtures =====

@pytest.fixture
def base_order_params():
    """基础订单参数fixture"""
    return {
        "code": "000001.SZ",
        "volume": 1000,
        "limit_price": Decimal('10.50')
    }


@pytest.fixture
def base_position_params():
    """基础持仓参数fixture"""
    return {
        "code": "000001.SZ",
        "volume": 1000,
        "average_cost": Decimal('10.0'),
        "current_price": Decimal('10.5')
    }


@pytest.fixture
def sample_portfolio_info():
    """示例投资组合信息fixture"""
    return PortfolioFactory.create_basic_portfolio(
        total_value=Decimal('100000.0'),
        cash_ratio=0.5
    )


@pytest.fixture
def sample_bar_data():
    """示例K线数据fixture"""
    return {
        "code": "000001.SZ",
        "timestamp": datetime(2024, 1, 1),
        "open": Decimal('10.0'),
        "high": Decimal('10.5'),
        "low": Decimal('9.8'),
        "close": Decimal('10.2'),
        "volume": 100000
    }


# ===== OrderFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestOrderFactory:
    """订单工厂测试"""

    def test_create_market_order(self):
        """测试创建市价订单"""
        order = OrderFactory.create_market_order(
            code="000001.SZ",
            volume=1000
        )

        assert order is not None
        assert order.code == "000001.SZ"
        assert order.volume == 1000
        assert order.direction.value == "long"

    def test_create_limit_order(self, base_order_params):
        """测试创建限价订单"""
        order = OrderFactory.create_limit_order(**base_order_params)

        assert order is not None
        assert order.limit_price == Decimal('10.50')
        assert order.frozen_money == pytest.approx(10500.0)

    def test_create_filled_order(self):
        """测试创建已成交订单"""
        order = OrderFactory.create_filled_order(
            code="000001.SZ",
            volume=1000,
            transaction_price=Decimal('10.50')
        )

        assert order.status.value == "filled"
        assert order.transaction_volume == 1000
        assert order.transaction_price == Decimal('10.50')
        assert order.fee > 0

    @pytest.mark.parametrize("direction,expected_direction", [
        ("long", DIRECTION_TYPES.LONG),
        ("short", DIRECTION_TYPES.SHORT),
    ])
    def test_create_order_with_direction(self, direction, expected_direction):
        """测试创建不同方向的订单"""
        order = OrderFactory.create_limit_order(
            code="000001.SZ",
            direction=direction,
            volume=1000,
            limit_price=Decimal('10.50')
        )

        assert order.direction == expected_direction

    def test_order_with_overrides(self):
        """测试使用覆盖参数创建订单"""
        custom_portfolio_id = "custom_portfolio"
        custom_timestamp = datetime(2024, 1, 1, 9, 30, 0)

        order = OrderFactory.create_limit_order(
            code="000001.SZ",
            volume=1000,
            limit_price=Decimal('10.50'),
            portfolio_id=custom_portfolio_id,
            timestamp=custom_timestamp
        )

        assert order.portfolio_id == custom_portfolio_id
        assert order.timestamp == custom_timestamp


# ===== PositionFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestPositionFactory:
    """持仓工厂测试"""

    def test_create_long_position(self, base_position_params):
        """测试创建多头持仓"""
        position = PositionFactory.create_long_position(**base_position_params)

        assert position is not None
        assert position.code == "000001.SZ"
        assert position.volume == 1000
        assert position.average_cost == Decimal('10.0')
        assert position.current_price == Decimal('10.5')

        # 验证计算的字段
        expected_market_value = Decimal('10.5') * 1000
        assert position.market_value == expected_market_value

        expected_profit_loss = (Decimal('10.5') - Decimal('10.0')) * 1000
        assert position.profit_loss == expected_profit_loss

    @pytest.mark.parametrize("loss_ratio,expected_sign", [
        (0.15, -1),  # 15%亏损，应为负值
        (0.20, -1),  # 20%亏损，应为负值
    ])
    def test_create_losing_position(self, loss_ratio, expected_sign):
        """测试创建亏损持仓"""
        position = PositionFactory.create_losing_position(
            code="000001.SZ",
            volume=1000,
            loss_ratio=loss_ratio
        )

        assert position.profit_loss < 0
        expected_profit_ratio = -loss_ratio
        assert abs(position.profit_loss_ratio - expected_profit_ratio) < 0.001

    @pytest.mark.parametrize("profit_ratio,expected_sign", [
        (0.25, 1),  # 25%盈利，应为正值
        (0.30, 1),  # 30%盈利，应为正值
    ])
    def test_create_profitable_position(self, profit_ratio, expected_sign):
        """测试创建盈利持仓"""
        position = PositionFactory.create_profitable_position(
            code="000001.SZ",
            volume=1000,
            profit_ratio=profit_ratio
        )

        assert position.profit_loss > 0
        expected_profit_ratio = profit_ratio
        assert abs(position.profit_loss_ratio - expected_profit_ratio) < 0.001


# ===== SignalFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestSignalFactory:
    """信号工厂测试"""

    def test_create_buy_signal(self):
        """测试创建买入信号"""
        signal = SignalFactory.create_buy_signal(
            code="000001.SZ",
            strength=0.8,
            reason="技术指标买入信号"
        )

        assert signal is not None
        assert signal.code == "000001.SZ"
        assert signal.direction.value == "long"
        assert signal.strength == 0.8
        assert signal.reason == "技术指标买入信号"

    def test_create_sell_signal(self):
        """测试创建卖出信号"""
        signal = SignalFactory.create_sell_signal(
            code="000001.SZ",
            strength=0.9,
            reason="技术指标卖出信号"
        )

        assert signal is not None
        assert signal.direction.value == "short"
        assert signal.strength == 0.9

    @pytest.mark.parametrize("risk_type,expected_keyword", [
        ("stop_loss", "止损"),
        ("take_profit", "止盈"),
        ("position_limit", "仓位限制"),
    ])
    def test_create_risk_signal(self, risk_type, expected_keyword):
        """测试创建不同类型的风控信号"""
        signal = SignalFactory.create_risk_signal(
            code="000001.SZ",
            risk_type=risk_type
        )

        assert signal is not None
        assert expected_keyword in signal.reason
        assert signal.strength == 1.0
        assert signal.signal_id is not None


# ===== EventFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestEventFactory:
    """事件工厂测试"""

    def test_create_price_update_event(self, sample_bar_data):
        """测试创建价格更新事件"""
        event = EventFactory.create_price_update_event(**sample_bar_data)

        assert event is not None
        assert event.code == "000001.SZ"
        assert event.open == Decimal('10.0')
        assert event.high == Decimal('10.5')
        assert event.low == Decimal('9.8')
        assert event.close == Decimal('10.2')
        assert event.volume == 100000

    @pytest.mark.parametrize("drop_ratio,expected_close", [
        (0.10, Decimal('9.0')),  # 10%下跌
        (0.15, Decimal('8.5')),  # 15%下跌
        (0.20, Decimal('8.0')),  # 20%下跌
    ])
    def test_create_price_drop_event(self, drop_ratio, expected_close):
        """测试创建价格下跌事件"""
        event = EventFactory.create_price_drop_event(
            code="000001.SZ",
            drop_ratio=drop_ratio,
            base_price=Decimal('10.0')
        )

        assert event is not None
        assert event.close == expected_close

    @pytest.mark.parametrize("rise_ratio,expected_close", [
        (0.15, Decimal('11.5')),  # 15%上涨
        (0.20, Decimal('12.0')),  # 20%上涨
        (0.25, Decimal('12.5')),  # 25%上涨
    ])
    def test_create_price_rise_event(self, rise_ratio, expected_close):
        """测试创建价格上涨事件"""
        event = EventFactory.create_price_rise_event(
            code="000001.SZ",
            rise_ratio=rise_ratio,
            base_price=Decimal('10.0')
        )

        assert event is not None
        assert event.close == expected_close


# ===== PortfolioFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestPortfolioFactory:
    """投资组合工厂测试"""

    def test_create_basic_portfolio(self):
        """测试创建基础投资组合"""
        portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('100000.0'),
            cash_ratio=0.5
        )

        assert portfolio is not None
        assert portfolio['cash'] == Decimal('50000.0')
        assert portfolio['total_value'] == Decimal('100000.0')
        assert len(portfolio['positions']) == 1
        assert 'portfolio_' in portfolio['uuid']

    @pytest.mark.parametrize("risk_type,expected_cash,expected_positions", [
        ("high", Decimal('10000.0'), 2),    # 高风险，低现金，多持仓
        ("conservative", Decimal('80000.0'), 1),  # 保守，高现金，少持仓
    ])
    def test_create_risk_portfolio(self, risk_type, expected_cash, expected_positions):
        """测试创建不同风险类型的投资组合"""
        if risk_type == "high":
            portfolio = PortfolioFactory.create_high_risk_portfolio()
        else:
            portfolio = PortfolioFactory.create_conservative_portfolio()

        assert portfolio['cash'] == expected_cash
        assert len(portfolio['positions']) == expected_positions


# ===== MarketScenarioFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestMarketScenarioFactory:
    """市场场景工厂测试"""

    @pytest.mark.parametrize("scenario_type,expected_trend", [
        ("bull", "up"),      # 牛市上涨
        ("bear", "down"),    # 熊市下跌
        ("volatile", None),   # 震荡无明确趋势
    ])
    def test_create_market_scenarios(self, scenario_type, expected_trend):
        """测试创建不同市场场景"""
        if scenario_type == "bull":
            events = MarketScenarioFactory.create_bull_market_scenario(days=5)
        elif scenario_type == "bear":
            events = MarketScenarioFactory.create_bear_market_scenario(days=5)
        else:
            events = MarketScenarioFactory.create_volatile_market_scenario(days=10)

        assert len(events) > 0

        # 对于牛市和熊市，验证趋势
        if expected_trend == "up":
            first_price = events[0].close
            last_price = events[-1].close
            assert last_price > first_price
        elif expected_trend == "down":
            first_price = events[0].close
            last_price = events[-1].close
            assert last_price < first_price

    def test_bull_market_scenario(self):
        """测试创建牛市场景"""
        events = MarketScenarioFactory.create_bull_market_scenario(days=5)

        assert len(events) == 5
        first_price = events[0].close
        last_price = events[-1].close
        assert last_price > first_price

        # 验证每个事件的基本属性
        for event in events:
            assert event.low <= event.close <= event.high
            assert event.volume > 0


# ===== EnhancedEventFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestEnhancedEventFactory:
    """增强事件工厂测试"""

    def test_create_enhanced_price_update_event(self):
        """测试创建增强的价格更新事件"""
        correlation_id = "test_correlation_123"
        causation_id = "test_causation_456"

        event = EnhancedEventFactory.create_enhanced_price_update_event(
            code="000001.SZ",
            close_price=Decimal('10.5'),
            correlation_id=correlation_id,
            causation_id=causation_id
        )

        assert event is not None
        assert event.correlation_id == correlation_id
        assert event.causation_id == causation_id
        assert event.engine_id == "test_engine"
        assert event.run_id == "test_run"
        assert event.sequence_number == 1
        assert event.event_type == "price_update"

    def test_create_event_chain(self):
        """测试创建事件链条"""
        events = EnhancedEventFactory.create_event_chain(
            code="000001.SZ",
            start_price=Decimal('10.0'),
            price_changes=[0.01, 0.02, -0.01]
        )

        assert len(events) == 3

        # 验证事件关联性
        correlation_ids = [event.correlation_id for event in events]
        assert len(set(correlation_ids)) == 1  # 所有事件有相同的关联ID

        # 验证因果链
        assert events[0].causation_id is None
        assert events[1].causation_id == events[0].correlation_id
        assert events[2].causation_id == events[1].correlation_id

        # 验证序列号
        for i, event in enumerate(events):
            assert event.sequence_number == i + 1


# ===== ProtocolTestFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestProtocolTestFactory:
    """Protocol测试工厂测试"""

    def test_create_basic_strategy_implementation(self):
        """测试创建基础策略实现"""
        strategy = ProtocolTestFactory.create_strategy_implementation("TestStrategy", "basic")

        assert strategy is not None
        assert strategy.name == "TestStrategy"

        # 测试方法存在性
        assert hasattr(strategy, 'cal')
        assert hasattr(strategy, 'get_strategy_info')
        assert hasattr(strategy, 'validate_parameters')

        # 测试方法调用
        portfolio_info = {"total_value": 100000}
        event = {"code": "000001.SZ", "price": 10.50}
        signals = strategy.cal(portfolio_info, event)
        assert isinstance(signals, list)

    def test_create_risk_manager_implementation(self):
        """测试创建风控管理器实现"""
        risk_manager = ProtocolTestFactory.create_risk_manager_implementation(
            "PositionRatioRisk", "position_ratio"
        )

        assert risk_manager is not None
        assert risk_manager.name == "PositionRatioRisk"
        assert risk_manager.max_position_ratio == 0.2


# ===== MixinTestFactory测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestMixinTestFactory:
    """Mixin测试工厂测试"""

    def test_create_strategy_with_mixin(self):
        """测试创建带有Mixin的策略"""
        from test.fixtures.mock_data_service_factory import MockStrategy

        EnhancedStrategy = MixinTestFactory.create_strategy_with_mixin(
            mixin_classes=[MockStrategy]
        )

        assert EnhancedStrategy is not None

        strategy = EnhancedStrategy()
        assert strategy is not None

        # 验证Mixin功能
        assert hasattr(strategy, 'name')
        assert hasattr(strategy, 'signals_generated')


# ===== 边界情况测试 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestFactoryEdgeCases:
    """工厂边界情况测试"""

    @pytest.mark.parametrize("volume", [
        -1000,   # 负数量
        0,        # 零数量
        10**9,    # 极大数量
    ])
    def test_factories_with_extreme_volumes(self, volume):
        """测试工厂处理极端数量"""
        order = OrderFactory.create_market_order(volume=volume)
        assert order is not None
        assert order.volume == volume

    @pytest.mark.parametrize("price", [
        Decimal('0.0001'),  # 极小价格
        Decimal('1000000'),  # 极大价格
    ])
    def test_factories_with_extreme_prices(self, price):
        """测试工厂处理极端价格"""
        position = PositionFactory.create_long_position(
            code="000001.SZ",
            volume=1000,
            current_price=price
        )
        assert position is not None
        assert position.current_price == price

    def test_factory_consistency(self):
        """测试工厂创建对象的一致性"""
        # 创建多个相同类型的对象
        orders = [
            OrderFactory.create_limit_order(code="000001.SZ", volume=1000)
            for _ in range(10)
        ]

        # 验证一致性
        for order in orders:
            assert order.code == "000001.SZ"
            assert order.volume == 1000

    @pytest.mark.parametrize("invalid_code", [
        "",           # 空字符串
        "INVALID",    # 无效格式
        None,         # None值
    ])
    def test_factories_with_invalid_codes(self, invalid_code):
        """测试工厂处理无效代码"""
        # 应该能处理无效代码而不崩溃
        try:
            signal = SignalFactory.create_buy_signal(code=invalid_code)
            assert signal is not None
        except (ValueError, AttributeError, TypeError):
            # 某些工厂可能会抛出异常
            pass


# ===== 参数化测试组合 =====

@pytest.mark.unit
@pytest.mark.fixtures
class TestFactoryCombinations:
    """工厂组合参数化测试"""

    @pytest.mark.parametrize("cash_ratio,expected_cash", [
        (0.0, Decimal('0.0')),
        (0.5, Decimal('50000.0')),
        (1.0, Decimal('100000.0')),
    ])
    def test_portfolio_cash_ratios(self, cash_ratio, expected_cash):
        """测试不同现金比例的投资组合"""
        portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('100000.0'),
            cash_ratio=cash_ratio
        )

        assert portfolio['cash'] == expected_cash

    @pytest.mark.parametrize("days,expected_events", [
        (1, 1),
        (5, 5),
        (10, 10),
    ])
    def test_market_scenario_days(self, days, expected_events):
        """测试不同天数的市场场景"""
        events = MarketScenarioFactory.create_bull_market_scenario(days=days)
        assert len(events) == expected_events

    @pytest.mark.parametrize("strength,reason", [
        (0.5, "低强度信号"),
        (0.8, "高强度信号"),
        (1.0, "最大强度信号"),
    ])
    def test_signal_strength_variations(self, strength, reason):
        """测试不同强度的信号"""
        signal = SignalFactory.create_buy_signal(
            code="000001.SZ",
            strength=strength,
            reason=reason
        )

        assert signal.strength == strength
        assert signal.reason == reason
