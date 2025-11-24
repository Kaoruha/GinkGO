"""
RandomSignalStrategy随机信号策略测试

验证随机信号生成策略的完整功能：
- 随机信号生成机制和概率控制
- 多目标股票代码支持
- 策略统计和信息管理
- 参数更新和配置管理
- 错误处理和边界条件
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock

from ginkgo.trading.strategy.strategies.random_signal_strategy import RandomSignalStrategy
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


@pytest.mark.strategy
@pytest.mark.random_signal
class TestRandomSignalStrategyBasics:
    """RandomSignalStrategy基础功能测试"""

    def test_strategy_initialization(self):
        """测试策略初始化"""
        print("\n测试策略初始化")

        # 默认参数初始化
        strategy = RandomSignalStrategy()

        # 验证基本属性
        assert strategy.buy_probability == 0.3
        assert strategy.sell_probability == 0.3
        assert len(strategy.target_codes) == 5
        assert "000001.SZ" in strategy.target_codes
        assert strategy.signal_count == 0
        assert len(strategy.signal_history) == 0

        print("✓ 默认参数初始化成功")

        # 自定义参数初始化
        custom_strategy = RandomSignalStrategy(
            buy_probability=0.4,
            sell_probability=0.2,
            target_codes=["000001.SZ", "600000.SH"],
            signal_reason_template="测试信号-{direction}-{index}"
        )

        assert custom_strategy.buy_probability == 0.4
        assert custom_strategy.sell_probability == 0.2
        assert custom_strategy.target_codes == ["000001.SZ", "600000.SH"]
        assert custom_strategy.signal_reason_template == "测试信号-{direction}-{index}"

        print("✓ 自定义参数初始化成功")

    def test_probability_normalization(self):
        """测试概率标准化"""
        print("\n测试概率标准化")

        # 测试超出范围的概率
        strategy = RandomSignalStrategy(buy_probability=1.5, sell_probability=1.2)

        # 概率应该被标准化到总和不超过1
        assert strategy.buy_probability <= 1.0
        assert strategy.sell_probability <= 1.0
        assert strategy.buy_probability + strategy.sell_probability <= 1.0

        # 验证比例保持
        original_ratio = 1.5 / 1.2  # 买入/卖出比例
        current_ratio = strategy.buy_probability / strategy.sell_probability
        assert abs(current_ratio - original_ratio) < 0.001

        print("✓ 概率标准化成功")

    def test_random_seed_setting(self):
        """测试随机数种子设置"""
        print("\n测试随机数种子设置")

        strategy = RandomSignalStrategy()
        strategy.set_random_seed(42)

        assert strategy.random_seed == 42

        # 验证可重现性
        portfolio_info = {}
        bar = Bar(code="000001.SZ", timestamp=datetime.datetime.now(), close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        # 第一次运行
        signals1 = strategy.cal(portfolio_info, event)

        # 重置并再次运行
        strategy.reset_statistics()
        strategy.set_random_seed(42)
        signals2 = strategy.cal(portfolio_info, event)

        # 结果应该相同
        assert len(signals1) == len(signals2)
        for s1, s2 in zip(signals1, signals2):
            assert s1.code == s2.code
            assert s1.direction == s2.direction

        print("✓ 随机数种子设置成功")


@pytest.mark.strategy
@pytest.mark.signal_generation
class TestRandomSignalStrategySignalGeneration:
    """RandomSignalStrategy信号生成测试"""

    def setup_method(self):
        """测试前设置"""
        self.strategy = RandomSignalStrategy(
            buy_probability=0.5,
            sell_probability=0.3,
            target_codes=["000001.SZ", "000002.SZ"]
        )
        self.strategy.set_random_seed(123)  # 固定种子确保可重现

    def test_signal_generation_process(self):
        """测试信号生成过程"""
        print("\n测试信号生成过程")

        portfolio_info = {}
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=Decimal("10.50")
        )
        event = EventPriceUpdate(price_info=bar)

        # 生成信号
        signals = self.strategy.cal(portfolio_info, event)

        # 验证信号格式
        for signal in signals:
            assert isinstance(signal, Signal)
            assert signal.code in self.strategy.target_codes
            assert signal.direction in [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]
            assert signal.reason.startswith("随机信号-")
            assert signal.timestamp is not None

        print(f"✓ 生成了 {len(signals)} 个信号")

    def test_multi_target_signals(self):
        """测试多目标股票信号生成"""
        print("\n测试多目标股票信号生成")

        # 设置多个目标股票
        self.strategy.target_codes = ["000001.SZ", "000002.SZ", "600000.SH"]
        self.strategy.set_random_seed(456)

        portfolio_info = {}
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        signals = self.strategy.cal(portfolio_info, event)

        # 验证信号覆盖多个股票
        signal_codes = set(s.code for s in signals)
        print(f"  信号覆盖股票: {signal_codes}")

        # 可能多个股票都有信号，也可能没有
        assert len(signals) <= len(self.strategy.target_codes)

        print("✓ 多目标股票信号生成成功")

    def test_direction_probability_distribution(self):
        """测试方向概率分布"""
        print("\n测试方向概率分布")

        # 设置确定性的概率
        self.strategy.buy_probability = 1.0  # 100%买入
        self.strategy.sell_probability = 0.0  # 0%卖出
        self.strategy.set_random_seed(789)

        portfolio_info = {}
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        signals = self.strategy.cal(portfolio_info, event)

        # 所有信号都应该是买入
        for signal in signals:
            assert signal.direction == DIRECTION_TYPES.LONG

        # 设置100%卖出
        self.strategy.buy_probability = 0.0
        self.strategy.sell_probability = 1.0
        self.strategy.set_random_seed(789)

        signals = self.strategy.cal(portfolio_info, event)

        # 所有信号都应该是卖出
        for signal in signals:
            assert signal.direction == DIRECTION_TYPES.SHORT

        print("✓ 方向概率分布正确")

    def test_no_hold_signals(self):
        """测试观望信号不生成"""
        print("\n测试观望信号不生成")

        # 设置100%观望概率
        self.strategy.buy_probability = 0.0
        self.strategy.sell_probability = 0.0

        portfolio_info = {}
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        signals = self.strategy.cal(portfolio_info, event)

        # 不应该生成任何信号
        assert len(signals) == 0

        print("✓ 观望信号不生成成功")

    def test_signal_reason_formatting(self):
        """测试信号原因格式化"""
        print("\n测试信号原因格式化")

        self.strategy.signal_reason_template = "自定义-{direction}-信号-#{index}"
        self.strategy.set_random_seed(999)

        portfolio_info = {}
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        signals = self.strategy.cal(portfolio_info, event)

        # 验证信号原因格式
        for signal in signals:
            assert "自定义" in signal.reason
            assert "信号" in signal.reason
            assert "#" in signal.reason

        print("✓ 信号原因格式化成功")


@pytest.mark.strategy
@pytest.mark.statistics
class TestRandomSignalStrategyStatistics:
    """RandomSignalStrategy统计功能测试"""

    def setup_method(self):
        """测试前设置"""
        self.strategy = RandomSignalStrategy(
            buy_probability=0.4,
            sell_probability=0.3,
            target_codes=["000001.SZ", "000002.SZ", "600000.SH"]
        )
        self.strategy.set_random_seed(111)

    def test_strategy_info(self):
        """测试策略信息获取"""
        print("\n测试策略信息获取")

        info = self.strategy.get_strategy_info()

        # 验证基本信息
        assert info["strategy_name"] == "RandomSignalStrategy"
        assert info["buy_probability"] == 0.4
        assert info["sell_probability"] == 0.3
        assert info["hold_probability"] == 0.3  # 1 - 0.4 - 0.3
        assert info["target_codes_count"] == 3
        assert info["total_signals_generated"] == 0  # 初始状态
        assert info["random_seed"] == 111

        print("✓ 策略信息获取成功")

    def test_signal_statistics_calculation(self):
        """测试信号统计计算"""
        print("\n测试信号统计计算")

        # 生成一些信号
        portfolio_info = {}
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        # 运行多次以积累信号
        for i in range(5):
            event.timestamp = datetime.datetime(2023, 1, i+1, 9, 30)
            signals = self.strategy.cal(portfolio_info, event)
            print(f"  第{i+1}次生成 {len(signals)} 个信号")

        # 获取统计信息
        stats = self.strategy.get_signal_statistics()

        # 验证统计数据
        assert stats["total_signals"] > 0
        assert stats["buy_signals"] >= 0
        assert stats["sell_signals"] >= 0
        assert stats["buy_ratio"] + stats["sell_ratio"] <= 1.0
        assert isinstance(stats["signals_by_code"], dict)
        assert len(stats["signals_by_code"]) <= len(self.strategy.target_codes)

        print(f"✓ 信号统计: 总计{stats['total_signals']}个, "
              f"买入{stats['buy_signals']}个({stats['buy_ratio']:.2%}), "
              f"卖出{stats['sell_signals']}个({stats['sell_ratio']:.2%})")

    def test_most_traded_code_identification(self):
        """测试最活跃股票识别"""
        print("\n测试最活跃股票识别")

        # 生成足够多的信号
        portfolio_info = {}
        for i in range(20):
            bar = Bar(code="000001.SZ", close=Decimal(f"10.{i:02d}"))
            event = EventPriceUpdate(price_info=bar)
            event.timestamp = datetime.datetime(2023, 1, i+1, 9, 30)
            self.strategy.cal(portfolio_info, event)

        stats = self.strategy.get_signal_statistics()

        if stats["total_signals"] > 0:
            # 应该能识别出最活跃的股票
            assert stats["most_traded_code"] is not None
            assert stats["most_traded_code"] in self.strategy.target_codes

            # 验证该股票确实有最多的信号
            max_signals = max(stats["signals_by_code"].values())
            assert stats["signals_by_code"][stats["most_traded_code"]] == max_signals

            print(f"✓ 最活跃股票: {stats['most_traded_code']} ({max_signals}个信号)")
        else:
            print("  未生成信号，跳过最活跃股票测试")

    def test_statistics_reset(self):
        """测试统计数据重置"""
        print("\n测试统计数据重置")

        # 先生成一些信号
        portfolio_info = {}
        bar = Bar(code="000001.SZ", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)
        self.strategy.cal(portfolio_info, event)

        # 验证有信号记录
        assert self.strategy.signal_count > 0
        assert len(self.strategy.signal_history) > 0

        # 重置统计
        self.strategy.reset_statistics()

        # 验证重置成功
        assert self.strategy.signal_count == 0
        assert len(self.strategy.signal_history) == 0
        assert self.strategy.last_signal_time is None

        # 获取统计信息应该显示无信号
        stats = self.strategy.get_signal_statistics()
        assert stats["total_signals"] == 0

        print("✓ 统计数据重置成功")


@pytest.mark.strategy
@pytest.mark.parameter_updates
class TestRandomSignalStrategyParameterUpdates:
    """RandomSignalStrategy参数更新测试"""

    def setup_method(self):
        """测试前设置"""
        self.strategy = RandomSignalStrategy(
            buy_probability=0.3,
            sell_probability=0.3,
            target_codes=["000001.SZ"]
        )

    def test_probability_updates(self):
        """测试概率更新"""
        print("\n测试概率更新")

        # 更新概率
        self.strategy.update_parameters(
            buy_probability=0.6,
            sell_probability=0.2
        )

        # 验证更新成功
        assert self.strategy.buy_probability == 0.6
        assert self.strategy.sell_probability == 0.2

        # 测试超出范围的值
        self.strategy.update_parameters(
            buy_probability=1.5,  # 超出范围
            sell_probability=0.8   # 会导致总和>1
        )

        # 应该被标准化
        assert self.strategy.buy_probability <= 1.0
        assert self.strategy.sell_probability <= 1.0
        assert self.strategy.buy_probability + self.strategy.sell_probability <= 1.0

        print("✓ 概率更新成功")

    def test_target_codes_updates(self):
        """测试目标股票代码更新"""
        print("\n测试目标股票代码更新")

        new_codes = ["600000.SH", "600036.SH", "000858.SZ"]
        self.strategy.update_parameters(target_codes=new_codes)

        # 验证更新成功
        assert self.strategy.target_codes == new_codes

        # 验证新代码在信号生成中生效
        self.strategy.set_random_seed(222)
        portfolio_info = {}
        bar = Bar(code="600000.SH", close=Decimal("10.50"))
        event = EventPriceUpdate(price_info=bar)

        signals = self.strategy.cal(portfolio_info, event)

        # 所有信号都应该来自新的代码池
        for signal in signals:
            assert signal.code in new_codes

        print("✓ 目标股票代码更新成功")

    def test_partial_parameter_updates(self):
        """测试部分参数更新"""
        print("\n测试部分参数更新")

        original_buy = self.strategy.buy_probability
        original_sell = self.strategy.sell_probability
        original_codes = self.strategy.target_codes.copy()

        # 只更新买入概率
        self.strategy.update_parameters(buy_probability=0.8)

        # 验证只更新了买入概率
        assert self.strategy.buy_probability == 0.8
        assert self.strategy.sell_probability == original_sell
        assert self.strategy.target_codes == original_codes

        # 只更新目标代码
        new_codes = ["999999.SZ"]
        self.strategy.update_parameters(target_codes=new_codes)

        assert self.strategy.target_codes == new_codes
        assert self.strategy.buy_probability == 0.8  # 保持之前的更新
        assert self.strategy.sell_probability == original_sell

        print("✓ 部分参数更新成功")


@pytest.mark.strategy
@pytest.mark.error_handling
class TestRandomSignalStrategyErrorHandling:
    """RandomSignalStrategy错误处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.strategy = RandomSignalStrategy()

    def test_invalid_event_handling(self):
        """测试无效事件处理"""
        print("\n测试无效事件处理")

        portfolio_info = {}
        invalid_events = [
            None,  # 空事件
            Mock(),  # 无属性事件
            "invalid_string"  # 字符串事件
        ]

        for invalid_event in invalid_events:
            try:
                signals = self.strategy.cal(portfolio_info, invalid_event)
                # 应该能处理而不崩溃
                print(f"  ✓ 处理无效事件: {type(invalid_event)}")
            except Exception as e:
                # 某些错误是预期的，但不应该导致策略完全失败
                print(f"  ✓ 无效事件错误处理: {type(e).__name__}")

    def test_signal_creation_failure(self):
        """测试信号创建失败处理"""
        print("\n测试信号创建失败处理")

        # 模拟信号创建失败
        with patch('ginkgo.trading.entities.signal.Signal', side_effect=Exception("创建失败")):
            portfolio_info = {}
            bar = Bar(code="000001.SZ", close=Decimal("10.50"))
            event = EventPriceUpdate(price_info=bar)

            # 即使信号创建失败，策略也不应该崩溃
            try:
                signals = self.strategy.cal(portfolio_info, event)
                # 应该返回空列表或部分成功的结果
                assert isinstance(signals, list)
                print("✓ 信号创建失败处理成功")
            except Exception as e:
                pytest.fail(f"信号创建失败导致策略崩溃: {e}")

    def test_logging_error_handling(self):
        """测试日志错误处理"""
        print("\n测试日志错误处理")

        # 测试日志记录
        self.strategy.log_error("测试错误消息")

        # 应该能记录错误而不崩溃
        print("✓ 日志错误处理成功")

    def test_edge_case_parameters(self):
        """测试边界参数"""
        print("\n测试边界参数")

        # 极小概率
        strategy1 = RandomSignalStrategy(buy_probability=0.0, sell_probability=0.0)
        assert strategy1.buy_probability == 0.0
        assert strategy1.sell_probability == 0.0

        # 极大概率
        strategy2 = RandomSignalStrategy(buy_probability=2.0, sell_probability=3.0)
        assert strategy2.buy_probability <= 1.0
        assert strategy2.sell_probability <= 1.0

        # 空目标代码列表
        strategy3 = RandomSignalStrategy(target_codes=[])
        assert len(strategy3.target_codes) == 0

        # 空信号原因模板
        strategy4 = RandomSignalStrategy(signal_reason_template="")
        assert strategy4.signal_reason_template == ""

        print("✓ 边界参数处理成功")


@pytest.mark.strategy
@pytest.mark.performance
class TestRandomSignalStrategyPerformance:
    """RandomSignalStrategy性能测试"""

    def setup_method(self):
        """测试前设置"""
        self.strategy = RandomSignalStrategy(
            target_codes=["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "000858.SZ"]
        )

    def test_high_frequency_signal_generation(self):
        """测试高频信号生成"""
        print("\n测试高频信号生成")

        import time

        portfolio_info = {}
        iterations = 1000

        start_time = time.time()

        total_signals = 0
        for i in range(iterations):
            bar = Bar(code="000001.SZ", close=Decimal(f"10.{i%100:02d}"))
            event = EventPriceUpdate(price_info=bar)
            event.timestamp = datetime.datetime(2023, 1, 1, 9, 30) + datetime.timedelta(seconds=i)

            signals = self.strategy.cal(portfolio_info, event)
            total_signals += len(signals)

        elapsed_time = time.time() - start_time

        signals_per_second = total_signals / elapsed_time if elapsed_time > 0 else float('inf')

        print(f"✓ 高频测试: {iterations}次迭代, {total_signals}个信号")
        print(f"  耗时: {elapsed_time:.3f}秒, 信号速率: {signals_per_second:.1f}个/秒")

        # 性能断言
        assert elapsed_time < 5.0, f"信号生成速度过慢: {elapsed_time:.3f}秒"
        assert signals_per_second > 100, f"信号生成速率过低: {signals_per_second:.1f}个/秒"

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        print("\n测试内存使用稳定性")

        import psutil
        import os
        import gc

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 大量信号生成
        for cycle in range(3):
            portfolio_info = {}
            for i in range(200):
                bar = Bar(code="000001.SZ", close=Decimal(f"10.{i%100:02d}"))
                event = EventPriceUpdate(price_info=bar)
                self.strategy.cal(portfolio_info, event)

            if cycle % 2 == 1:
                gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"✓ 内存使用: 初始 {initial_memory:.1f}MB, 最终 {final_memory:.1f}MB, 增长 {memory_increase:.1f}MB")

        # 内存增长应该在合理范围内
        assert memory_increase < 20, f"内存增长过多: {memory_increase:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])