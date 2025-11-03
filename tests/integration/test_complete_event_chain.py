"""
完整事件链路集成测试

端到端验证完整的事件链路，从数据加载到结果输出的整个回测流程。
基于澄清规格：DataFeeder → EventPriceUpdate → Portfolio → Strategy → Signal保存 → 延迟执行 → 风控处理 → 订单生成 → 撮合执行
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.order_related import EventOrderRelated
from ginkgo.trading.events.order_lifecycle_events import EventOrderAck
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.trading.strategy.sizers.base_sizer import BaseSizer
from ginkgo.trading.strategy.risk_managers.position_ratio_risk import PositionRatioRisk
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.enums import (
    SOURCE_TYPES, DIRECTION_TYPES, EVENT_TYPES, EXECUTION_MODE,
    RECORDSTAGE_TYPES
)


class TestStrategy(BaseStrategy):
    """测试策略 - 简单突破策略"""

    def __init__(self, threshold=Decimal("10.00")):
        super().__init__()
        self.threshold = threshold
        self.signals_generated = []

    def cal(self, portfolio_info, event, *args, **kwargs):
        if isinstance(event, EventPriceUpdate) and event.code == "000001.SZ":
            if event.close > self.threshold:
                signal = Signal(
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    reason=f"价格{event.close}突破{self.threshold}",
                    timestamp=event.business_timestamp
                )
                self.signals_generated.append(signal)
                return [signal]
        return []


class TestSizer(BaseSizer):
    """测试Sizer - 固定订单大小"""

    def __init__(self, volume=100):
        super().__init__()
        self.volume = volume
        self.orders_created = []

    def cal(self, portfolio_info, signal):
        if signal and signal.direction == DIRECTION_TYPES.LONG:
            order = Order(
                code=signal.code,
                direction=signal.direction,
                volume=self.volume,
                limit_price=Decimal("10.50"),
                reason=signal.reason
            )
            self.orders_created.append(order)
            return order
        return None


class TestRiskManager(PositionRatioRisk):
    """测试风控管理器"""

    def __init__(self, max_ratio=0.3):
        super().__init__(max_position_ratio=max_ratio)
        self.adjusted_orders = []

    def cal(self, portfolio_info, order):
        self.adjusted_orders.append(order)

        # 简单风控：限制订单量
        total_value = portfolio_info.get('total_value', 100000)
        max_position_value = total_value * self.max_position_ratio

        if order.limit_price:
            max_volume = int(max_position_value / order.limit_price)
            if order.volume > max_volume:
                order.volume = max_volume
                order.reason = f"{order.reason} (风控调整)"

        return order


@pytest.mark.integration
class TestCompleteEventFlow:
    """测试完整事件流程"""

    def setup_method(self):
        """测试前设置"""
        # 创建引擎
        self.engine = TimeControlledEventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )

        # 创建组件
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy(threshold=Decimal("10.00"))
        self.sizer = TestSizer(volume=100)
        self.risk_manager = TestRiskManager(max_ratio=0.3)

        # 配置Portfolio
        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.add_risk_manager(self.risk_manager)

        # 设置引擎ID
        test_engine_id = "test_engine_complete_flow"
        self.portfolio.engine_id = test_engine_id

        # 添加到引擎
        self.engine.add_portfolio(self.portfolio)

        # 创建测试数据
        self.test_bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            open=Decimal("10.00"),
            high=Decimal("10.20"),
            low=Decimal("9.80"),
            close=Decimal("10.50"),  # 高于阈值
            volume=1000000
        )

    def test_end_to_end_price_to_order_flow(self):
        """测试从价格到订单的端到端流程"""
        print("\n=== 测试端到端事件流程 ===")

        # 步骤1: 创建价格事件
        price_event = EventPriceUpdate(
            price_info=self.test_bar,
            source=SOURCE_TYPES.BACKTESTFEEDER,
            engine_id=self.engine.engine_id
        )
        print(f"✓ 步骤1: 创建价格事件 {price_event.code} @ {price_event.close}")

        # 步骤2: Portfolio处理价格事件
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证策略生成信号
        assert len(self.strategy.signals_generated) == 1, "策略应该生成1个信号"
        signal = self.strategy.signals_generated[0]
        assert signal.code == "000001.SZ", "信号代码正确"
        assert signal.direction == DIRECTION_TYPES.LONG, "信号方向正确"
        print(f"✓ 步骤2: 策略生成信号 {signal.direction} {signal.code}")

        # 步骤3: 验证信号保存（延迟执行机制）
        signals_in_portfolio = self.portfolio.signals
        assert len(signals_in_portfolio) > 0, "信号应该被保存到portfolio"
        print(f"✓ 步骤3: 信号保存到T+1列表，当前{len(signals_in_portfolio)}个信号")

        # 步骤4: 时间推进触发批量执行
        next_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time)

        # 验证批量推送发生
        assert mock_put.called, "应该推送EventSignalGeneration事件"
        print("✓ 步骤4: 时间推进触发T+1信号批量推送")

        # 步骤5: 验证Sizer和RiskManager处理
        assert len(self.sizer.orders_created) == 1, "Sizer应该创建1个订单"
        assert len(self.risk_manager.adjusted_orders) == 1, "RiskManager应该处理1个订单"

        order = self.sizer.orders_created[0]
        assert order.code == "000001.SZ", "订单代码正确"
        print(f"✓ 步骤5: Sizer创建订单，RiskManager调整完成")

    def test_all_key_events_generated(self):
        """测试所有关键事件都正确生成"""
        event_types_generated = []

        def event_handler(event):
            event_types_generated.append(type(event).__name__)

        # 注册事件处理器
        self.engine.register_handler(EVENT_TYPES.PRICEUPDATE, event_handler)
        self.engine.register_handler(EVENT_TYPES.SIGNALGENERATION, event_handler)
        self.engine.register_handler(EVENT_TYPES.ORDERSUBMITTED, event_handler)

        # 执行完整流程
        price_event = EventPriceUpdate(price_info=self.test_bar)
        self.portfolio.on_price_received(price_event)

        # 时间推进触发批量推送
        next_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time)

        # 验证关键事件类型
        expected_events = ['EventPriceUpdate', 'EventSignalGeneration']
        for event_type in expected_events:
            assert any(event_type in et for et in event_types_generated), f"缺少{event_type}事件"

        print(f"✓ 关键事件生成验证通过: {event_types_generated}")


@pytest.mark.integration
class TestMultiComponentCollaboration:
    """测试多组件协同工作"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy()
        self.sizer = TestSizer(volume=200)
        self.risk_manager = TestRiskManager(max_ratio=0.2)  # 更严格的风控

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.add_risk_manager(self.risk_manager)

    def test_portfolio_strategy_sizer_collaboration(self):
        """测试Portfolio、Strategy、Sizer协同工作"""
        # 创建价格事件
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # Portfolio处理价格事件
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.on_price_received(price_event)

        # 验证组件协同
        assert len(self.strategy.signals_generated) == 1, "策略生成信号"

        # 时间推进触发Sizer处理
        next_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time)

        assert len(self.sizer.orders_created) == 1, "Sizer创建订单"
        order = self.sizer.orders_created[0]
        assert order.volume == 200, "订单大小符合Sizer配置"
        print("✓ Portfolio、Strategy、Sizer协同工作正常")

    def test_risk_manager_integration(self):
        """测试风控管理器集成"""
        # 创建大额订单触发风控
        large_order = Order(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=1000,  # 大额订单
            limit_price=Decimal("10.50")
        )

        portfolio_info = {'total_value': 100000}

        # 通过风控处理
        adjusted_order = self.risk_manager.cal(portfolio_info, large_order)

        # 验证风控调整
        assert adjusted_order.volume < large_order.volume, "风控应该减少订单量"
        expected_max_volume = int(100000 * 0.2 / 10.50)  # 20%仓位限制
        assert adjusted_order.volume <= expected_max_volume, "符合仓位限制"
        print(f"✓ 风控集成正常: {large_order.volume}→{adjusted_order.volume}")


@pytest.mark.integration
class TestDelayedExecutionCycle:
    """测试延迟执行周期"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy()
        self.sizer = TestSizer()
        self.risk_manager = TestRiskManager()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.add_risk_manager(self.risk_manager)

    def test_decision_to_execution_cycle(self):
        """测试决策到执行的完整周期"""
        print("\n=== 测试决策到执行周期 ===")

        # 阶段1: 决策阶段（当前时间点）
        decision_time = datetime.datetime(2023, 1, 1, 9, 30)
        bar = Bar(code="000001.SZ", timestamp=decision_time, close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar, timestamp=decision_time)

        with patch.object(self.portfolio, 'put'):
            self.portfolio.on_price_received(price_event)

        # 验证决策阶段完成
        assert len(self.strategy.signals_generated) == 1, "决策阶段完成"
        assert len(self.portfolio.signals) > 0, "信号已保存"
        print(f"✓ 决策阶段完成: {decision_time}")

        # 阶段2: 执行阶段（下一时间点）
        execution_time = datetime.datetime(2023, 1, 1, 10, 30)

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(execution_time)

        # 验证执行阶段完成
        assert mock_put.called, "执行阶段完成"
        assert len(self.portfolio.signals) == 0, "信号已清空"
        print(f"✓ 执行阶段完成: {execution_time}")

    def test_multiple_cycles_integration(self):
        """测试多个周期的集成"""
        cycles = [
            (datetime.datetime(2023, 1, 1, 9, 30), Decimal("10.50")),
            (datetime.datetime(2023, 1, 1, 10, 30), Decimal("11.00")),
            (datetime.datetime(2023, 1, 1, 11, 30), Decimal("11.50"))
        ]

        total_decisions = 0
        total_executions = 0

        for i, (time_point, price) in enumerate(cycles):
            # 决策阶段
            bar = Bar(code="000001.SZ", timestamp=time_point, close=price)
            price_event = EventPriceUpdate(price_info=bar, timestamp=time_point)

            with patch.object(self.portfolio, 'put'):
                self.portfolio.on_price_received(price_event)

            total_decisions += len(self.strategy.signals_generated)

            # 执行阶段（除了最后一个）
            if i < len(cycles) - 1:
                next_time = cycles[i + 1][0]
                with patch.object(self.portfolio, 'put') as mock_put:
                    self.portfolio.advance_time(next_time)
                    if mock_put.called:
                        total_executions += 1

        # 验证多周期集成
        assert total_decisions == 3, f"应该有3个决策，实际{total_decisions}"
        assert total_executions == 2, f"应该有2次执行，实际{total_executions}"
        print(f"✓ 多周期集成正常: {total_decisions}个决策，{total_executions}次执行")


@pytest.mark.integration
class TestEventFlowIntegrity:
    """测试事件流完整性"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.strategy = TestStrategy()
        self.sizer = TestSizer()
        self.risk_manager = TestRiskManager()

        self.portfolio.add_strategy(self.strategy)
        self.portfolio.set_sizer(self.sizer)
        self.portfolio.add_risk_manager(self.risk_manager)

    def test_event_sequence_correctness(self):
        """测试事件序列正确性"""
        event_log = []

        def log_event(event):
            event_log.append({
                'type': type(event).__name__,
                'timestamp': event.timestamp,
                'code': getattr(event, 'code', None)
            })

        # 模拟完整事件序列
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 决策阶段
        with patch.object(self.portfolio, 'put') as mock_put:
            def capture_event(event):
                event_log.append({
                    'type': type(event).__name__,
                    'timestamp': event.timestamp,
                    'code': event.code
                })
            mock_put.side_effect = capture_event

            self.portfolio.on_price_received(price_event)

        # 执行阶段
        next_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            def capture_execution(event):
                event_log.append({
                    'type': type(event).__name__,
                    'timestamp': event.timestamp,
                    'code': event.code
                })
            mock_put.side_effect = capture_execution

            self.portfolio.advance_time(next_time)

        # 验证事件序列
        expected_sequence = ['EventSignalGeneration']
        actual_sequence = [event['type'] for event in event_log]

        for expected in expected_sequence:
            assert expected in actual_sequence, f"缺少{expected}事件"

        print(f"✓ 事件序列正确: {actual_sequence}")

    def test_no_events_lost(self):
        """测试事件不丢失"""
        # 创建多个价格事件
        price_events = []
        for i in range(3):
            bar = Bar(
                code="000001.SZ",
                timestamp=datetime.datetime(2023, 1, 1, 9, 30) + datetime.timedelta(minutes=i),
                close=Decimal(f"10.{i}0")
            )
            price_event = EventPriceUpdate(price_info=bar)
            price_events.append(price_event)

        # 处理所有价格事件
        for price_event in price_events:
            with patch.object(self.portfolio, 'put'):
                self.portfolio.on_price_received(price_event)

        # 验证所有决策都被保存
        saved_signals = len(self.portfolio.signals)
        expected_signals = len([pe for pe in price_events if pe.value.close > Decimal("10.00")])

        assert saved_signals == expected_signals, f"应该保存{expected_signals}个信号，实际{saved_signals}个"
        print(f"✓ 事件不丢失: {expected_signals}个决策都被保存")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])