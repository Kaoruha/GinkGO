"""
交易实体工厂测试

测试交易对象工厂的正确性和完整性，确保TDD测试数据的可靠性。
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List

# 导入工厂类
from test.fixtures.trading_factories import (
    OrderFactory, PositionFactory, SignalFactory, EventFactory,
    PortfolioFactory, MarketScenarioFactory,
    EnhancedEventFactory, ProtocolTestFactory, MixinTestFactory
)


@pytest.mark.tdd
@pytest.mark.fixtures
class TestOrderFactory:
    """订单工厂测试"""

    def test_create_market_order(self):
        """测试创建市价订单"""
        order = OrderFactory.create_market_order(
            code="000001.SZ",
            volume=1000
        )

        assert order is not None, "应该创建订单成功"
        assert order.code == "000001.SZ", "股票代码应该正确"
        assert order.volume == 1000, "数量应该正确"
        assert order.direction.value == "long", "默认方向应该是多头"

    def test_create_limit_order(self):
        """测试创建限价订单"""
        order = OrderFactory.create_limit_order(
            code="000001.SZ",
            volume=1000,
            limit_price=Decimal('10.50')
        )

        assert order is not None, "应该创建订单成功"
        assert order.limit_price == 10.50, "限价应该正确"
        assert order.frozen_money == 10500.0, "冻结资金应该正确"  # 1000 * 10.50

    def test_create_filled_order(self):
        """测试创建已成交订单"""
        order = OrderFactory.create_filled_order(
            code="000001.SZ",
            volume=1000,
            transaction_price=Decimal('10.50')
        )

        assert order is not None, "应该创建订单成功"
        assert order.status.value == "filled", "状态应该是已成交"
        assert order.transaction_volume == 1000, "成交数量应该正确"
        assert order.transaction_price == Decimal('10.50'), "成交价格应该正确"
        assert order.fee > 0, "应该计算手续费"

    def test_create_sell_order(self):
        """测试创建卖单"""
        order = OrderFactory.create_limit_order(
            code="000001.SZ",
            direction="short",
            volume=1000,
            limit_price=Decimal('10.50')
        )

        assert order is not None, "应该创建订单成功"
        assert order.direction.value == "short", "方向应该是空头"
        assert order.frozen_volume == 1000, "应该冻结股票数量"

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

        assert order.portfolio_id == custom_portfolio_id, "应该使用自定义投资组合ID"
        assert order.timestamp == custom_timestamp, "应该使用自定义时间戳"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestPositionFactory:
    """持仓工厂测试"""

    def test_create_long_position(self):
        """测试创建多头持仓"""
        position = PositionFactory.create_long_position(
            code="000001.SZ",
            volume=1000,
            average_cost=Decimal('10.0'),
            current_price=Decimal('10.5')
        )

        assert position is not None, "应该创建持仓成功"
        assert position.code == "000001.SZ", "股票代码应该正确"
        assert position.volume == 1000, "数量应该正确"
        assert position.average_cost == Decimal('10.0'), "平均成本应该正确"
        assert position.current_price == Decimal('10.5'), "当前价格应该正确"

        # 验证计算的字段
        expected_market_value = Decimal('10.5') * 1000
        assert position.market_value == expected_market_value, "市值应该正确计算"

        expected_profit_loss = (Decimal('10.5') - Decimal('10.0')) * 1000
        assert position.profit_loss == expected_profit_loss, "盈亏应该正确计算"

    def test_create_losing_position(self):
        """测试创建亏损持仓"""
        position = PositionFactory.create_losing_position(
            code="000001.SZ",
            volume=1000,
            loss_ratio=0.15  # 15%亏损
        )

        assert position is not None, "应该创建持仓成功"
        assert position.profit_loss < 0, "应该是亏损"

        # 验证亏损比例
        expected_profit_ratio = -0.15
        assert abs(position.profit_loss_ratio - expected_profit_ratio) < 0.001, "亏损比例应该正确"

    def test_create_profitable_position(self):
        """测试创建盈利持仓"""
        position = PositionFactory.create_profitable_position(
            code="000001.SZ",
            volume=1000,
            profit_ratio=0.25  # 25%盈利
        )

        assert position is not None, "应该创建持仓成功"
        assert position.profit_loss > 0, "应该是盈利"

        # 验证盈利比例
        expected_profit_ratio = 0.25
        assert abs(position.profit_loss_ratio - expected_profit_ratio) < 0.001, "盈利比例应该正确"


@pytest.mark.tdd
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

        assert signal is not None, "应该创建信号成功"
        assert signal.code == "000001.SZ", "股票代码应该正确"
        assert signal.direction.value == "long", "方向应该是多头"
        assert signal.strength == 0.8, "信号强度应该正确"
        assert signal.reason == "技术指标买入信号", "原因应该正确"

    def test_create_sell_signal(self):
        """测试创建卖出信号"""
        signal = SignalFactory.create_sell_signal(
            code="000001.SZ",
            strength=0.9,
            reason="技术指标卖出信号"
        )

        assert signal is not None, "应该创建信号成功"
        assert signal.direction.value == "short", "方向应该是空头"
        assert signal.strength == 0.9, "信号强度应该正确"

    def test_create_risk_signal(self):
        """测试创建风控信号"""
        signal = SignalFactory.create_risk_signal(
            code="000001.SZ",
            risk_type="stop_loss"
        )

        assert signal is not None, "应该创建信号成功"
        assert signal.direction.value == "short", "风控信号通常是卖出"
        assert signal.strength == 1.0, "风控信号强度应该最高"
        assert "止损" in signal.reason, "原因应该包含止损"
        assert signal.signal_id is not None, "应该有信号ID"

    def test_create_risk_signal_different_types(self):
        """测试创建不同类型的风控信号"""
        # 测试止盈信号
        take_profit_signal = SignalFactory.create_risk_signal(
            code="000001.SZ",
            risk_type="take_profit"
        )
        assert "止盈" in take_profit_signal.reason, "应该包含止盈"

        # 测试仓位限制信号
        position_limit_signal = SignalFactory.create_risk_signal(
            code="000001.SZ",
            risk_type="position_limit"
        )
        assert "仓位限制" in position_limit_signal.reason, "应该包含仓位限制"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestEventFactory:
    """事件工厂测试"""

    def test_create_price_update_event(self):
        """测试创建价格更新事件"""
        event = EventFactory.create_price_update_event(
            code="000001.SZ",
            open_price=Decimal('10.0'),
            high_price=Decimal('10.8'),
            low_price=Decimal('9.8'),
            close_price=Decimal('10.5'),
            volume=100000
        )

        assert event is not None, "应该创建事件成功"
        assert event.code == "000001.SZ", "股票代码应该正确"
        assert event.open == Decimal('10.0'), "开盘价应该正确"
        assert event.high == Decimal('10.8'), "最高价应该正确"
        assert event.low == Decimal('9.8'), "最低价应该正确"
        assert event.close == Decimal('10.5'), "收盘价应该正确"
        assert event.volume == 100000, "成交量应该正确"

    def test_create_price_drop_event(self):
        """测试创建价格下跌事件"""
        event = EventFactory.create_price_drop_event(
            code="000001.SZ",
            drop_ratio=0.10,
            base_price=Decimal('10.0')
        )

        assert event is not None, "应该创建事件成功"
        assert event.close == Decimal('9.0'), "下跌后价格应该正确"  # 10.0 * (1 - 0.10)

    def test_create_price_rise_event(self):
        """测试创建价格上涨事件"""
        event = EventFactory.create_price_rise_event(
            code="000001.SZ",
            rise_ratio=0.15,
            base_price=Decimal('10.0')
        )

        assert event is not None, "应该创建事件成功"
        assert event.close == Decimal('11.5'), "上涨后价格应该正确"  # 10.0 * (1 + 0.15)


@pytest.mark.tdd
@pytest.mark.fixtures
class TestPortfolioFactory:
    """投资组合工厂测试"""

    def test_create_basic_portfolio(self):
        """测试创建基础投资组合"""
        portfolio = PortfolioFactory.create_basic_portfolio(
            total_value=Decimal('100000.0'),
            cash_ratio=0.5
        )

        assert portfolio is not None, "应该创建投资组合成功"
        assert portfolio['cash'] == Decimal('50000.0'), "现金应该正确"  # 100000 * 0.5
        assert portfolio['total_value'] == Decimal('100000.0'), "总价值应该正确"
        assert len(portfolio['positions']) == 1, "应该有1个持仓"
        assert 'portfolio_' in portfolio['uuid'], "应该有投资组合ID"

    def test_create_high_risk_portfolio(self):
        """测试创建高风险投资组合"""
        portfolio = PortfolioFactory.create_high_risk_portfolio()

        assert portfolio is not None, "应该创建投资组合成功"
        assert portfolio['cash'] == Decimal('10000.0'), "现金应该较少"  # 100000 * 0.1
        assert len(portfolio['positions']) == 2, "应该有2个持仓"

        # 验证高仓位
        total_position_value = sum(pos['market_value'] for pos in portfolio['positions'].values())
        expected_total_position = Decimal('90000.0')  # 100000 - 10000
        assert total_position_value == expected_total_position, "总仓位应该很高"

    def test_create_conservative_portfolio(self):
        """测试创建保守投资组合"""
        portfolio = PortfolioFactory.create_conservative_portfolio()

        assert portfolio is not None, "应该创建投资组合成功"
        assert portfolio['cash'] == Decimal('80000.0'), "现金应该较多"  # 100000 * 0.8
        assert len(portfolio['positions']) == 1, "应该只有1个持仓"

        # 验证低仓位
        total_position_value = sum(pos['market_value'] for pos in portfolio['positions'].values())
        expected_total_position = Decimal('20000.0')  # 100000 - 80000
        assert total_position_value == expected_total_position, "总仓位应该很低"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestMarketScenarioFactory:
    """市场场景工厂测试"""

    def test_create_bull_market_scenario(self):
        """测试创建牛市场景"""
        events = MarketScenarioFactory.create_bull_market_scenario(days=5)

        assert len(events) == 5, "应该创建5天的事件"

        # 验证牛市特征：总体上涨趋势
        first_price = events[0].close
        last_price = events[-1].close
        assert last_price > first_price, "牛市应该总体上涨"

        # 验证每个事件的基本属性
        for event in events:
            assert event.low <= event.close <= event.high, "收盘价应该在高低价之间"
            assert event.volume > 0, "成交量应该大于0"

    def test_create_bear_market_scenario(self):
        """测试创建熊市场景"""
        events = MarketScenarioFactory.create_bear_market_scenario(days=5)

        assert len(events) == 5, "应该创建5天的事件"

        # 验证熊市特征：总体下跌趋势
        first_price = events[0].close
        last_price = events[-1].close
        assert last_price < first_price, "熊市应该总体下跌"

        # 熊市成交量通常更大
        total_volume = sum(event.volume for event in events)
        assert total_volume > 0, "总成交量应该大于0"

    def test_create_volatile_market_scenario(self):
        """测试创建震荡市场景"""
        events = MarketScenarioFactory.create_volatile_market_scenario(days=10)

        assert len(events) == 10, "应该创建10天的事件"

        # 验证震荡特征：价格在一定范围内波动
        prices = [event.close for event in events]
        price_range = max(prices) - min(prices)
        assert price_range > 0, "应该有价格波动"


@pytest.mark.tdd
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

        assert event is not None, "应该创建事件成功"
        assert event.correlation_id == correlation_id, "关联ID应该正确"
        assert event.causation_id == causation_id, "因果ID应该正确"
        assert event.engine_id == "test_engine", "引擎ID应该正确"
        assert event.run_id == "test_run", "运行ID应该正确"
        assert event.sequence_number == 1, "序列号应该正确"
        assert event.event_type == "price_update", "事件类型应该正确"

    def test_create_event_chain(self):
        """测试创建事件链条"""
        events = EnhancedEventFactory.create_event_chain(
            code="000001.SZ",
            start_price=Decimal('10.0'),
            price_changes=[0.01, 0.02, -0.01]
        )

        assert len(events) == 3, "应该创建3个事件"

        # 验证事件关联性
        correlation_ids = [event.correlation_id for event in events]
        assert len(set(correlation_ids)) == 1, "所有事件应该有相同的关联ID"

        # 验证因果链
        assert events[0].causation_id is None, "第一个事件不应该有因果ID"
        assert events[1].causation_id == events[0].correlation_id, "第二个事件应该引用第一个"
        assert events[2].causation_id == events[1].correlation_id, "第三个事件应该引用第二个"

        # 验证序列号
        for i, event in enumerate(events):
            assert event.sequence_number == i + 1, f"第{i+1}个事件的序列号应该正确"

        # 验证价格变化
        prices = [event.close for event in events]
        assert prices[0] == Decimal('10.0') * Decimal('1.01'), "第一个价格应该正确"
        assert prices[1] == prices[0] * Decimal('1.02'), "第二个价格应该正确"
        assert prices[2] == prices[1] * Decimal('0.99'), "第三个价格应该正确"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestProtocolTestFactory:
    """Protocol测试工厂测试"""

    def test_create_basic_strategy_implementation(self):
        """测试创建基础策略实现"""
        strategy = ProtocolTestFactory.create_strategy_implementation("TestStrategy", "basic")

        assert strategy is not None, "应该创建策略成功"
        assert strategy.name == "TestStrategy", "策略名称应该正确"

        # 测试方法存在性
        assert hasattr(strategy, 'cal'), "应该有cal方法"
        assert hasattr(strategy, 'get_strategy_info'), "应该有get_strategy_info方法"
        assert hasattr(strategy, 'validate_parameters'), "应该有validate_parameters方法"
        assert hasattr(strategy, 'initialize'), "应该有initialize方法"
        assert hasattr(strategy, 'finalize'), "应该有finalize方法"

        # 测试方法调用
        portfolio_info = {"total_value": 100000}
        event = {"code": "000001.SZ", "price": 10.50}
        signals = strategy.cal(portfolio_info, event)
        assert isinstance(signals, list), "cal方法应该返回列表"

        info = strategy.get_strategy_info()
        assert isinstance(info, dict), "get_strategy_info应该返回字典"
        assert info['name'] == "TestStrategy", "信息应该包含正确名称"

    def test_create_advanced_strategy_implementation(self):
        """测试创建高级策略实现"""
        strategy = ProtocolTestFactory.create_strategy_implementation("AdvancedStrategy", "advanced")

        assert strategy is not None, "应该创建策略成功"
        assert strategy.name == "AdvancedStrategy", "策略名称应该正确"
        assert hasattr(strategy, 'signals_generated'), "高级策略应该有信号记录"

        # 测试信号生成逻辑
        portfolio_info = {"total_value": 100000}
        event = {"code": "000001.SZ", "close_price": 15.0}  # 价格 > 10.0 应该触发信号
        signals = strategy.cal(portfolio_info, event)
        assert len(signals) > 0, "应该生成信号"

    def test_create_risk_manager_implementation(self):
        """测试创建风控管理器实现"""
        # 测试仓位比例风控
        risk_manager = ProtocolTestFactory.create_risk_manager_implementation(
            "PositionRatioRisk", "position_ratio"
        )

        assert risk_manager is not None, "应该创建风控管理器成功"
        assert risk_manager.name == "PositionRatioRisk", "名称应该正确"
        assert risk_manager.max_position_ratio == 0.2, "默认仓位比例应该正确"

        # 测试订单验证
        portfolio_info = {"total_value": 100000}
        mock_order = Mock()
        mock_order.quantity = 2000
        mock_order.limit_price = 10.0  # 订单价值20000

        adjusted_order = risk_manager.validate_order(portfolio_info, mock_order)
        # 应该调整订单数量到最大允许范围内（100000 * 0.2 = 20000）

        # 测试止损风控
        stop_loss_manager = ProtocolTestFactory.create_risk_manager_implementation(
            "StopLossRisk", "stop_loss"
        )

        assert stop_loss_manager is not None, "应该创建止损风控管理器"
        assert stop_loss_manager.loss_limit == 0.1, "默认止损比例应该正确"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestMixinTestFactory:
    """Mixin测试工厂测试"""

    def test_create_strategy_with_mixin(self):
        """测试创建带有Mixin的策略"""
        from test.fixtures.mock_data_service_factory import MockStrategy

        EnhancedStrategy = MixinTestFactory.create_strategy_with_mixin(
            mixin_classes=[MockStrategy]
        )

        assert EnhancedStrategy is not None, "应该创建增强策略类"

        strategy = EnhancedStrategy()
        assert strategy is not None, "应该创建策略实例"

        # 验证Mixin功能
        assert hasattr(strategy, 'name'), "应该有基础策略的属性"
        assert hasattr(strategy, 'signals_generated'), "应该有Mixin的属性"

    def test_create_portfolio_with_enhancement(self):
        """测试创建增强功能的投资组合"""
        EnhancedPortfolio = MixinTestFactory.create_portfolio_with_enhancement(
            enhancement_features=['event_enhancement', 'time_provider']
        )

        assert EnhancedPortfolio is not None, "应该创建增强投资组合类"

        portfolio = EnhancedPortfolio()
        assert portfolio is not None, "应该创建投资组合实例"

        # 验证增强功能
        assert 'event_enhancement' in portfolio.enhancement_features, "应该有事件增强功能"
        assert 'time_provider' in portfolio.enhancement_features, "应该有时间提供者功能"
        assert hasattr(portfolio, 'event_history'), "应该有事件历史"
        assert hasattr(portfolio, 'time_provider'), "应该有时间提供者"


@pytest.mark.tdd
@pytest.mark.fixtures
class TestFactoryEdgeCases:
    """工厂边界情况测试"""

    def test_factories_with_invalid_inputs(self):
        """测试工厂处理无效输入"""
        # 测试负数量
        order = OrderFactory.create_market_order(volume=-1000)
        # 应该创建成功，但可能需要验证逻辑

        # 测试空代码
        signal = SignalFactory.create_buy_signal(code="")
        # 应该能处理空字符串

        # 测试零持仓
        position = PositionFactory.create_long_position(volume=0)
        # 应该能处理零数量

    def test_factories_with_extreme_values(self):
        """测试工厂处理极端值"""
        # 测试极大数量
        large_order = OrderFactory.create_market_order(volume=10**9)
        assert large_order is not None, "应该能处理极大数量"

        # 测试极大价格
        expensive_signal = SignalFactory.create_buy_signal(
            limit_price=Decimal('10**6')
        )
        assert expensive_signal is not None, "应该能处理极大价格"

        # 测试极小价格
        tiny_position = PositionFactory.create_long_position(
            current_price=Decimal('0.0001')
        )
        assert tiny_position is not None, "应该能处理极小价格"

    def test_factory_consistency(self):
        """测试工厂创建对象的一致性"""
        # 创建多个相同类型的对象
        orders = [
            OrderFactory.create_limit_order(code="000001.SZ", volume=1000)
            for _ in range(10)
        ]

        # 验证一致性
        for order in orders:
            assert order.code == "000001.SZ", "所有订单代码应该一致"
            assert order.volume == 1000, "所有订单数量应该一致"

        # 验证唯一性
        portfolio_ids = [order.portfolio_id for order in orders]
        # 可能每个订单都应该有不同的ID，这取决于实现


# ===== TDD阶段标记 =====

def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator