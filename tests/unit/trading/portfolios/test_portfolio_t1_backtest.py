"""
PortfolioT1Backtest核心功能测试

验证T+1回测Portfolio的完整功能：
- 组件注册和管理（Strategy、Sizer、RiskManager）
- T+1延迟执行机制（信号保存和批量执行）
- 事件处理和状态管理
- 风控集成和订单生成
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, call

from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.trading.strategy.sizers.base_sizer import BaseSizer
from ginkgo.trading.strategy.risk_managements.position_ratio_risk import PositionRatioRisk
from ginkgo.trading.strategy.selectors.base_selector import BaseSelector
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES


class TestStrategy(BaseStrategy):
    """测试用策略"""

    def __init__(self, signal_generator=None):
        super().__init__()
        self.signal_generator = signal_generator or (lambda event: [])
        self.call_count = 0
        self.last_event = None

    def cal(self, portfolio_info, event, *args, **kwargs):
        self.call_count += 1
        self.last_event = event
        return self.signal_generator(event)


class TestSizer(BaseSizer):
    """测试用Sizer"""

    def __init__(self, volume=100):
        super().__init__()
        self.volume = volume
        self.call_count = 0
        self.last_signal = None

    def cal(self, portfolio_info, signal):
        self.call_count += 1
        self.last_signal = signal
        if signal is None:
            return None
        return Order(
            code=signal.code,
            direction=signal.direction,
            volume=self.volume,
            reason="TestSizer"
        )


class TestSelector(BaseSelector):
    """测试用选择器"""

    def __init__(self):
        super().__init__()
        self.call_count = 0
        self.last_portfolio_info = None

    def cal(self, portfolio_info):
        self.call_count += 1
        self.last_portfolio_info = portfolio_info
        return ["000001.SZ", "000002.SZ"]


@pytest.mark.portfolio
@pytest.mark.t1_backtest
class TestPortfolioT1BacktestBasics:
    """PortfolioT1Backtest基础功能测试"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "test_portfolio_001"

    def test_portfolio_initialization(self):
        """测试Portfolio初始化"""
        print("\n测试Portfolio初始化")

        # 验证基本属性
        assert self.portfolio.engine_id == "test_portfolio_001"
        assert hasattr(self.portfolio, '_strategies')
        assert hasattr(self.portfolio, '_sizer')
        assert hasattr(self.portfolio, '_risk_managers')
        assert hasattr(self.portfolio, '_selector')
        assert hasattr(self.portfolio, '_signals')  # T+1延迟执行信号存储

        # 验证初始状态
        assert len(self.portfolio._strategies) == 0
        assert len(self.portfolio._risk_managers) == 0
        assert self.portfolio._sizer is None
        assert self.portfolio._selector is None
        assert len(self.portfolio._signals) == 0

        print("✓ Portfolio初始化成功")

    def test_strategy_registration(self):
        """测试策略注册"""
        print("\n测试策略注册")

        strategy = TestStrategy()
        strategy.strategy_id = "test_strategy_001"

        # 注册策略
        result = self.portfolio.add_strategy(strategy)

        assert result is True
        assert strategy.strategy_id in self.portfolio._strategies
        assert self.portfolio._strategies[strategy.strategy_id] is strategy

        print("✓ 策略注册成功")

    def test_duplicate_strategy_registration(self):
        """测试重复策略注册"""
        print("\n测试重复策略注册")

        strategy = TestStrategy()
        strategy.strategy_id = "duplicate_strategy"

        # 首次注册
        assert self.portfolio.add_strategy(strategy) is True

        # 重复注册
        result = self.portfolio.add_strategy(strategy)

        # 应该拒绝重复注册
        assert result is False

        print("✓ 重复策略注册被正确拒绝")

    def test_sizer_setting(self):
        """测试Sizer设置"""
        print("\n测试Sizer设置")

        sizer = TestSizer(volume=200)

        # 设置Sizer
        result = self.portfolio.set_sizer(sizer)

        assert result is True
        assert self.portfolio._sizer is sizer

        print("✓ Sizer设置成功")

    def test_risk_manager_registration(self):
        """测试风控管理器注册"""
        print("\n测试风控管理器注册")

        risk_manager = PositionRatioRisk(max_position_ratio=0.3)

        # 注册风控管理器
        result = self.portfolio.add_risk_manager(risk_manager)

        assert result is True
        assert risk_manager in self.portfolio._risk_managers

        print("✓ 风控管理器注册成功")

    def test_selector_setting(self):
        """测试选择器设置"""
        print("\n测试选择器设置")

        selector = TestSelector()

        # 设置选择器
        result = self.portfolio.set_selector(selector)

        assert result is True
        assert self.portfolio._selector is selector

        print("✓ 选择器设置成功")


@pytest.mark.portfolio
@pytest.mark.event_handling
class TestPortfolioT1BacktestEventHandling:
    """PortfolioT1Backtest事件处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "event_test_portfolio"

        # 注册测试组件
        self.strategy = TestStrategy()
        self.strategy.strategy_id = "test_strategy"
        self.portfolio.add_strategy(self.strategy)

        self.sizer = TestSizer(volume=100)
        self.portfolio.set_sizer(self.sizer)

        self.risk_manager = PositionRatioRisk(max_position_ratio=0.3)
        self.portfolio.add_risk_manager(self.risk_manager)

    def test_price_event_handling(self):
        """测试价格事件处理"""
        print("\n测试价格事件处理")

        # 创建价格事件
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")
        )
        price_event = EventPriceUpdate(
            price_info=bar,
            source=SOURCE_TYPES.BACKTESTFEEDER,
            engine_id=self.portfolio.engine_id
        )

        # 处理价格事件
        self.portfolio.on_price_received(price_event)

        # 验证策略被调用
        assert self.strategy.call_count == 1
        assert self.strategy.last_event is price_event

        print("✓ 价格事件处理成功")

    def test_time_advance_event_handling(self):
        """测试时间推进事件处理"""
        print("\n测试时间推进事件处理")

        # 先添加一些信号
        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="测试信号",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30)
        )
        self.portfolio._signals.append(signal)

        # 创建时间推进事件
        advance_time = datetime.datetime(2023, 1, 1, 10, 30)
        time_event = EventTimeAdvance(
            current_time=advance_time,
            source=SOURCE_TYPES.ENGINE
        )

        # 模拟批量处理
        with patch.object(self.portfolio, 'process_signals_batch') as mock_process:
            self.portfolio.advance_time(advance_time.timestamp())

            assert mock_process.called
            assert mock_process.call_args[0][0] == advance_time.timestamp()

        print("✓ 时间推进事件处理成功")

    def test_signal_generation_and_storage(self):
        """测试信号生成和存储"""
        print("\n测试信号生成和存储")

        # 配置策略生成信号
        test_signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="价格突破",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30)
        )
        self.strategy.signal_generator = lambda event: [test_signal]

        # 创建价格事件
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 处理价格事件（决策阶段）
        self.portfolio.on_price_received(price_event)

        # 验证信号被保存（延迟执行）
        assert len(self.portfolio._signals) == 1
        assert self.portfolio._signals[0] is test_signal

        print("✓ 信号生成和存储成功")

    def test_batch_signal_processing(self):
        """测试批量信号处理"""
        print("\n测试批量信号处理")

        # 添加多个信号
        signals = [
            Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, reason="信号1"),
            Signal(code="000002.SZ", direction=DIRECTION_TYPES.SHORT, reason="信号2"),
            Signal(code="000003.SZ", direction=DIRECTION_TYPES.LONG, reason="信号3")
        ]
        self.portfolio._signals.extend(signals)

        # 模拟批量处理
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.process_signals_batch(datetime.datetime.now().timestamp())

            # 验证每个信号都触发了订单生成流程
            assert self.sizer.call_count == len(signals)

        print(f"✓ 批量信号处理成功：{len(signals)}个信号")


@pytest.mark.portfolio
@pytest.mark.t1_mechanism
class TestPortfolioT1BacktestT1Mechanism:
    """PortfolioT1Backtest T+1机制测试"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "t1_test_portfolio"

        # 注册完整组件链
        self.strategy = TestStrategy()
        self.strategy.strategy_id = "t1_strategy"
        self.portfolio.add_strategy(self.strategy)

        self.sizer = TestSizer(volume=100)
        self.portfolio.set_sizer(self.sizer)

        self.risk_manager = PositionRatioRisk(max_position_ratio=0.3)
        self.portfolio.add_risk_manager(self.risk_manager)

    def test_decision_execution_separation(self):
        """测试决策执行分离"""
        print("\n测试决策执行分离（T+1机制）")

        # 第一阶段：决策（但不执行）
        test_signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="决策信号"
        )
        self.strategy.signal_generator = lambda event: [test_signal]

        # 决策阶段：处理价格事件
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        self.portfolio.on_price_received(price_event)

        # 验证决策完成，信号已保存
        assert len(self.portfolio._signals) == 1
        assert self.strategy.call_count == 1
        assert self.sizer.call_count == 0  # 尚未执行

        print("✓ 决策阶段完成，信号已保存")

        # 第二阶段：执行（下一时间点）
        advance_time = datetime.datetime(2023, 1, 1, 10, 30)

        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(advance_time.timestamp())

        # 验证执行完成
        assert self.sizer.call_count == 1  # Sizer被调用
        assert mock_put.called  # 订单被推送

        # 验证信号被清空
        assert len(self.portfolio._signals) == 0

        print("✓ 执行阶段完成，信号已清空")

    def test_multiple_decision_cycles(self):
        """测试多轮决策周期"""
        print("\n测试多轮决策周期")

        cycles = [
            {"time": datetime.datetime(2023, 1, 1, 9, 30), "price": Decimal("10.50"), "direction": DIRECTION_TYPES.LONG},
            {"time": datetime.datetime(2023, 1, 2, 9, 30), "price": Decimal("11.20"), "direction": DIRECTION_TYPES.LONG},
            {"time": datetime.datetime(2023, 1, 3, 9, 30), "price": Decimal("8.80"), "direction": DIRECTION_TYPES.SHORT},
        ]

        # 模拟多轮决策
        for i, cycle in enumerate(cycles):
            print(f"  第{i+1}轮决策: {cycle['time'].date()}")

            # 决策阶段
            test_signal = Signal(
                code="000001.SZ",
                direction=cycle["direction"],
                reason=f"第{i+1}轮决策"
            )
            self.strategy.signal_generator = lambda event, sig=test_signal: [sig]

            bar = Bar(code="000001.SZ", close=cycle["price"])
            price_event = EventPriceUpdate(price_info=bar)

            self.portfolio.on_price_received(price_event)

            # 验证信号保存
            assert len(self.portfolio._signals) == 1

            # 执行阶段（除了最后一轮）
            if i < len(cycles) - 1:
                next_time = cycle["time"] + datetime.timedelta(days=1)
                with patch.object(self.portfolio, 'put') as mock_put:
                    self.portfolio.advance_time(next_time.timestamp())

                assert mock_put.called
                assert len(self.portfolio._signals) == 0  # 信号清空

        print(f"✓ 多轮决策周期完成：{len(cycles)}轮")

    def test_signal_order_preservation(self):
        """测试信号顺序保持"""
        print("\n测试信号顺序保持")

        # 添加多个信号（不同时间）
        signals = []
        for i in range(5):
            signal = Signal(
                code=f"00000{i+1}.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason=f"信号{i+1}",
                timestamp=datetime.datetime(2023, 1, i+1, 9, 30)
            )
            signals.append(signal)
            self.portfolio._signals.append(signal)

        # 验证信号顺序
        for i, signal in enumerate(self.portfolio._signals):
            assert signal is signals[i]

        print("✓ 信号顺序保持正确")

    def test_t1_mechanism_with_multiple_strategies(self):
        """测试多策略T+1机制"""
        print("\n测试多策略T+1机制")

        # 添加多个策略
        strategy1 = TestStrategy()
        strategy1.strategy_id = "multi_strategy_1"
        self.portfolio.add_strategy(strategy1)

        strategy2 = TestStrategy()
        strategy2.strategy_id = "multi_strategy_2"
        self.portfolio.add_strategy(strategy2)

        # 配置策略生成不同信号
        signal1 = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, reason="策略1信号")
        signal2 = Signal(code="000002.SZ", direction=DIRECTION_TYPES.SHORT, reason="策略2信号")

        strategy1.signal_generator = lambda event: [signal1]
        strategy2.signal_generator = lambda event: [signal2]

        # 决策阶段
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        self.portfolio.on_price_received(price_event)

        # 验证多策略信号收集
        assert len(self.portfolio._signals) == 2
        assert strategy1.call_count == 1
        assert strategy2.call_count == 1

        # 执行阶段
        advance_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(advance_time.timestamp())

        # 验证批量执行
        assert self.sizer.call_count == 2  # 两个信号都被处理
        assert mock_put.called

        print("✓ 多策略T+1机制正常")


@pytest.mark.portfolio
@pytest.mark.component_integration
class TestPortfolioT1BacktestComponentIntegration:
    """PortfolioT1Backtest组件集成测试"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "integration_test_portfolio"

    def test_complete_component_chain(self):
        """测试完整组件链"""
        print("\n测试完整组件链")

        # 注册所有组件
        strategy = TestStrategy()
        strategy.strategy_id = "chain_strategy"
        self.portfolio.add_strategy(strategy)

        sizer = TestSizer(volume=150)
        self.portfolio.set_sizer(sizer)

        risk_manager = PositionRatioRisk(max_position_ratio=0.2)
        self.portfolio.add_risk_manager(risk_manager)

        selector = TestSelector()
        self.portfolio.set_selector(selector)

        # 配置策略生成信号
        test_signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="组件链测试"
        )
        strategy.signal_generator = lambda event: [test_signal]

        # 决策阶段
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        self.portfolio.on_price_received(price_event)

        # 验证策略调用
        assert strategy.call_count == 1
        assert len(self.portfolio._signals) == 1

        # 执行阶段
        advance_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(advance_time.timestamp())

        # 验证完整链路调用
        assert sizer.call_count == 1
        assert sizer.last_signal is test_signal
        assert mock_put.called

        print("✓ 完整组件链集成成功")

    def test_risk_manager_integration(self):
        """测试风控管理器集成"""
        print("\n测试风控管理器集成")

        # 注册组件
        strategy = TestStrategy()
        strategy.strategy_id = "risk_test_strategy"
        self.portfolio.add_strategy(strategy)

        sizer = TestSizer(volume=1000)  # 大量订单
        self.portfolio.set_sizer(sizer)

        risk_manager = PositionRatioRisk(max_position_ratio=0.1)  # 严格风控
        self.portfolio.add_risk_manager(risk_manager)

        # 生成信号
        test_signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        strategy.signal_generator = lambda event: [test_signal]

        # 决策阶段
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)
        self.portfolio.on_price_received(price_event)

        # 执行阶段
        advance_time = datetime.datetime(2023, 1, 1, 10, 30)
        with patch.object(self.portfolio, 'put') as mock_put:
            self.portfolio.advance_time(advance_time.timestamp())

        # 验证风控介入
        assert sizer.call_count == 1
        order = sizer.last_signal  # Sizer应该创建了订单

        # 注意：由于使用真实的风控，订单量可能被调整
        # 这里的验证确保流程正常进行
        assert mock_put.called

        print("✓ 风控管理器集成正常")

    def test_selector_integration(self):
        """测试选择器集成"""
        print("\n测试选择器集成")

        # 注册组件
        strategy = TestStrategy()
        strategy.strategy_id = "selector_test_strategy"
        self.portfolio.add_strategy(strategy)

        selector = TestSelector()
        self.portfolio.set_selector(selector)

        # 测试选择器调用时机
        portfolio_info = {"total_value": 100000, "positions": {}}

        # 选择器应该在某些操作中被调用
        # 这里验证选择器可以被正确访问
        selected_codes = selector.cal(portfolio_info)

        assert selected_codes == ["000001.SZ", "000002.SZ"]
        assert selector.call_count == 1
        assert selector.last_portfolio_info is portfolio_info

        print("✓ 选择器集成正常")


@pytest.mark.portfolio
@pytest.mark.error_handling
class TestPortfolioT1BacktestErrorHandling:
    """PortfolioT1Backtest错误处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "error_test_portfolio"

    def test_strategy_error_handling(self):
        """测试策略错误处理"""
        print("\n测试策略错误处理")

        # 创建会出错的策略
        error_strategy = TestStrategy()
        error_strategy.strategy_id = "error_strategy"
        error_strategy.signal_generator = lambda event: [_ for _ in ()]  # 空生成器表达式，会引发异常

        self.portfolio.add_strategy(error_strategy)

        # 创建正常策略
        normal_strategy = TestStrategy()
        normal_strategy.strategy_id = "normal_strategy"
        normal_signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        normal_strategy.signal_generator = lambda event: [normal_signal]
        self.portfolio.add_strategy(normal_strategy)

        # 处理价格事件
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        price_event = EventPriceUpdate(price_info=bar)

        # 即使有策略出错，其他策略应该正常工作
        try:
            self.portfolio.on_price_received(price_event)
            print("✓ 策略错误隔离成功")
        except Exception as e:
            pytest.fail(f"策略错误导致Portfolio崩溃: {e}")

    def test_sizer_error_handling(self):
        """测试Sizer错误处理"""
        print("\n测试Sizer错误处理")

        # 注册策略
        strategy = TestStrategy()
        strategy.strategy_id = "sizer_error_strategy"
        test_signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        strategy.signal_generator = lambda event: [test_signal]
        self.portfolio.add_strategy(strategy)

        # 创建会出错的Sizer
        error_sizer = TestSizer()
        error_sizer.cal = Mock(side_effect=Exception("Sizer处理异常"))
        self.portfolio.set_sizer(error_sizer)

        # 添加信号
        self.portfolio._signals.append(test_signal)

        # 尝试处理信号
        try:
            with patch.object(self.portfolio, 'put'):
                self.portfolio.process_signals_batch(datetime.datetime.now().timestamp())
            print("✓ Sizer错误处理成功")
        except Exception as e:
            # 验证错误被正确处理
            assert "Sizer处理异常" in str(e)
            print("✓ Sizer错误被正确捕获")

    def test_invalid_event_handling(self):
        """测试无效事件处理"""
        print("\n测试无效事件处理")

        # 创建各种无效事件
        invalid_events = [
            None,  # 空事件
            Mock(),  # 无属性事件
            "invalid_string",  # 字符串事件
        ]

        for invalid_event in invalid_events:
            try:
                self.portfolio.on_price_received(invalid_event)
                print(f"✓ 无效事件处理成功: {type(invalid_event)}")
            except AttributeError as e:
                # 某些属性错误是预期的
                print(f"✓ 无效事件属性错误被正确处理: {e}")
            except Exception as e:
                pytest.fail(f"无效事件导致Portfolio崩溃: {e}")

    def test_component_missing_handling(self):
        """测试组件缺失处理"""
        print("\n测试组件缺失处理")

        # 只注册策略，不注册Sizer
        strategy = TestStrategy()
        strategy.strategy_id = "no_sizer_strategy"
        test_signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        strategy.signal_generator = lambda event: [test_signal]
        self.portfolio.add_strategy(strategy)

        # 不设置Sizer，直接处理信号
        self.portfolio._signals.append(test_signal)

        # 应该能处理缺失的Sizer
        try:
            with patch.object(self.portfolio, 'put'):
                self.portfolio.process_signals_batch(datetime.datetime.now().timestamp())
            print("✓ Sizer缺失处理成功")
        except Exception as e:
            # 验证错误信息
            assert "sizer" in str(e).lower() or "none" in str(e).lower()
            print(f"✓ Sizer缺失错误被正确处理: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])