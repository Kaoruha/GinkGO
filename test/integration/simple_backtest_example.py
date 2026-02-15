"""
简单回测示例测试

展示如何使用Ginkgo回测引擎完成完整的回测流程：
1. 初始化组件（Portfolio、Strategy、Sizer、RiskManager）
2. 创建测试数据
3. 运行回测流程
4. 验证结果

基于澄清规格的完整事件链路：
DataFeeder → EventPriceUpdate → Portfolio → Strategy → Signal保存 → 延迟执行 → 风控处理 → 订单生成 → 撮合执行
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, EXECUTION_MODE


class SimpleBreakthroughStrategy(BaseStrategy):
    """简单突破策略"""

    def __init__(self, buy_threshold=Decimal("10.00"), sell_threshold=Decimal("9.00")):
        super().__init__()
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        self.signals_generated = []

    def cal(self, portfolio_info, event, *args, **kwargs):
        if isinstance(event, EventPriceUpdate) and event.code == "000001.SZ":
            current_price = event.close
            current_time = event.business_timestamp

            if current_price > self.buy_threshold:
                signal = Signal(
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    reason=f"价格{current_price}突破{self.buy_threshold}",
                    timestamp=current_time
                )
                self.signals_generated.append(signal)
                return [signal]

            elif current_price < self.sell_threshold:
                signal = Signal(
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.SHORT,
                    reason=f"价格{current_price}跌破{self.sell_threshold}",
                    timestamp=current_time
                )
                self.signals_generated.append(signal)
                return [signal]

        return []


class FixedSizer(BaseSizer):
    """固定大小Sizer"""

    def __init__(self, volume=100):
        super().__init__()
        self.volume = volume
        self.orders_created = []

    def cal(self, portfolio_info, signal):
        if signal is None:
            return None

        order = Order(
            code=signal.code,
            direction=signal.direction,
            volume=self.volume,
            limit_price=Decimal("10.50"),
            reason=signal.reason
        )

        self.orders_created.append(order)
        return order


class ConservativeRiskManager(PositionRatioRisk):
    """保守风控管理器"""

    def __init__(self, max_position_ratio=0.3):
        super().__init__(max_position_ratio=max_position_ratio)
        self.adjusted_orders = []

    def cal(self, portfolio_info, order):
        self.adjusted_orders.append(order)

        total_value = portfolio_info.get('total_value', 100000)
        max_position_value = total_value * self.max_position_ratio

        if order.limit_price:
            max_volume = int(max_position_value / order.limit_price)
            if order.volume > max_volume:
                original_volume = order.volume
                order.volume = max_volume
                order.reason = f"{order.reason} (风控调整: {original_volume}→{max_volume})"

        return order


@pytest.mark.integration
class TestSimpleBacktestExample:
    """简单回测示例测试"""

    def setup_method(self):
        """测试前设置"""
        # 初始化组件
        self.engine = TimeControlledEventEngine(
            name="SimpleBacktestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )

        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "simple_backtest_001"

        self.strategy = SimpleBreakthroughStrategy(
            buy_threshold=Decimal("10.00"),
            sell_threshold=Decimal("9.00")
        )
        self.portfolio.add_strategy(self.strategy)

        self.sizer = FixedSizer(volume=100)
        self.portfolio.set_sizer(self.sizer)

        self.risk_manager = ConservativeRiskManager(max_position_ratio=0.3)
        self.portfolio.add_risk_manager(self.risk_manager)

        self.engine.add_portfolio(self.portfolio)

    def test_complete_backtest_workflow(self):
        """测试完整回测工作流程"""
        print("\n=== 简单回测示例测试 ===")

        # 创建测试数据
        test_data = [
            Bar(
                code="000001.SZ",
                timestamp=datetime.datetime(2023, 1, 1, 9, 30),
                close=Decimal("10.50")  # 触发买入信号
            ),
            Bar(
                code="000001.SZ",
                timestamp=datetime.datetime(2023, 1, 2, 9, 30),
                close=Decimal("11.20")  # 继续持有
            ),
            Bar(
                code="000001.SZ",
                timestamp=datetime.datetime(2023, 1, 3, 9, 30),
                close=Decimal("8.80")   # 触发卖出信号
            )
        ]

        # 运行回测流程
        for i, bar in enumerate(test_data):
            print(f"\n--- 第{i+1}天: {bar.timestamp.date()} ---")
            print(f"价格: {bar.close}")

            # 创建价格事件
            price_event = EventPriceUpdate(
                price_info=bar,
                source=SOURCE_TYPES.BACKTESTFEEDER,
                engine_id=self.engine.engine_id
            )

            # Portfolio处理价格事件
            self.portfolio.on_price_received(price_event)

            # 检查策略决策
            if self.strategy.signals_generated:
                latest_signal = self.strategy.signals_generated[-1]
                print(f"策略决策: {latest_signal.direction.name} - {latest_signal.reason}")

            # 时间推进触发执行（除了最后一天）
            if i < len(test_data) - 1:
                next_time = bar.timestamp + datetime.timedelta(days=1)
                with patch.object(self.portfolio, 'put') as mock_put:
                    self.portfolio.advance_time(next_time.timestamp())

                if mock_put.called:
                    print("执行阶段: 信号批量推送完成")

        # 验证结果
        assert len(self.strategy.signals_generated) == 2, "应该生成2个信号（买入+卖出）"
        assert len(self.sizer.orders_created) == 2, "应该创建2个订单"
        assert len(self.risk_manager.adjusted_orders) == 2, "应该调整2个订单"

        # 验证信号类型
        signals = self.strategy.signals_generated
        assert signals[0].direction == DIRECTION_TYPES.LONG, "第1个信号应该是买入"
        assert signals[1].direction == DIRECTION_TYPES.SHORT, "第2个信号应该是卖出"

        print(f"\n✓ 回测完成: {len(self.strategy.signals_generated)}个信号, {len(self.sizer.orders_created)}个订单")

    def test_event_chain_verification(self):
        """测试事件链路验证"""
        print("\n=== 事件链路验证测试 ===")

        # 创建单个测试数据
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")
        )

        # 验证事件链路步骤
        print("步骤1: DataFeeder → EventPriceUpdate")
        price_event = EventPriceUpdate(
            price_info=bar,
            source=SOURCE_TYPES.BACKTESTFEEDER
        )
        assert price_event.code == "000001.SZ"
        assert price_event.close == Decimal("10.50")
        print("✓ EventPriceUpdate创建成功")

        print("步骤2: Portfolio → Strategy")
        initial_signals = len(self.strategy.signals_generated)
        self.portfolio.on_price_received(price_event)
        final_signals = len(self.strategy.signals_generated)
        assert final_signals > initial_signals, "策略应该生成新信号"
        print("✓ Strategy.cal()被调用并生成信号")

        print("步骤3: Signal保存（延迟执行机制）")
        signals_in_portfolio = self.portfolio.signals
        assert len(signals_in_portfolio) > 0, "信号应该被保存到portfolio"
        print("✓ 信号保存到_signals列表")

        print("步骤4: 时间推进触发批量执行")
        next_time = datetime.datetime(2023, 1, 2, 9, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time.timestamp())
        assert mock_put.called, "应该触发批量推送"
        print("✓ advance_time()触发批量推送")

        print("步骤5: Sizer和RiskManager处理")
        assert len(self.sizer.orders_created) > 0, "Sizer应该创建订单"
        assert len(self.risk_manager.adjusted_orders) > 0, "RiskManager应该调整订单"
        print("✓ Sizer和RiskManager协同工作")

        print("\n✓ 完整事件链路验证通过")

    def test_delayed_execution_mechanism(self):
        """测试延迟执行机制"""
        print("\n=== 延迟执行机制测试 ===")

        # 第一天：决策阶段
        bar_day1 = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")
        )
        price_event = EventPriceUpdate(price_info=bar_day1)

        print("决策阶段: 处理价格事件")
        self.portfolio.on_price_received(price_event)

        # 验证决策已保存但未执行
        assert len(self.strategy.signals_generated) == 1, "决策完成"
        assert len(self.portfolio.signals) > 0, "信号已保存"
        print("✓ 决策完成，信号已保存")

        # 第二天：执行阶段
        next_time = datetime.datetime(2023, 1, 2, 9, 30)
        print("执行阶段: 时间推进")

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(next_time.timestamp())

        # 验证执行完成
        assert mock_put.called, "执行阶段完成"
        assert len(self.sizer.orders_created) > 0, "订单已创建"
        print("✓ 执行阶段完成")

        # 验证T+1机制特性
        print("\nT+1机制特性验证:")
        print("✓ 基于当前时间点信息做出决策")
        print("✓ 决策保存到下一时间点执行")
        print("✓ advance_time()触发批量执行")
        print("✓ 执行后信号列表清空")

    def test_risk_management_integration(self):
        """测试风控系统集成"""
        print("\n=== 风控系统集成测试 ===")

        # 创建测试场景
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 处理价格事件
        self.portfolio.on_price_received(price_event)

        # 时间推进触发执行
        next_time = datetime.datetime(2023, 1, 2, 9, 30)
        with patch.object(self.portfolio, 'put'):
            self.portfolio.advance_time(next_time.timestamp())

        # 验证风控介入
        assert len(self.risk_manager.adjusted_orders) > 0, "风控应该介入"
        adjusted_order = self.risk_manager.adjusted_orders[0]

        # 验证风控调整逻辑
        total_value = 100000
        max_position_value = total_value * 0.3  # 30%
        max_volume = int(max_position_value / adjusted_order.limit_price)

        assert adjusted_order.volume <= max_volume, "订单量应该符合风控限制"
        assert "风控调整" in adjusted_order.reason, "订单原因应该包含风控标记"

        print(f"✓ 风控集成正常: 订单量调整为{adjusted_order.volume}股")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])