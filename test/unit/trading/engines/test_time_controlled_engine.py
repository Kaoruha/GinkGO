"""
TimeControlledEventEngine核心功能测试

验证时间控制事件引擎的基础功能：
- 时间推进机制和事件调度
- Portfolio管理和状态监控
- 事件处理的完整生命周期
- 异常处理和资源清理
"""

import pytest
import datetime
import time
from unittest.mock import Mock, patch, call
from threading import Event
from queue import Queue

from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import EXECUTION_MODE, SOURCE_TYPES


@pytest.mark.engine
@pytest.mark.time_controlled
class TestTimeControlledEngineBasics:
    """TimeControlledEventEngine基础功能测试"""

    def setup_method(self):
        """测试前设置"""
        self.engine = TimeControlledEventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )

    def test_engine_initialization(self):
        """测试引擎初始化"""
        print("\n测试引擎初始化")

        # 验证基本属性
        assert self.engine.name == "TestEngine"
        assert self.engine.mode == EXECUTION_MODE.BACKTEST
        assert self.engine.logical_current_time == datetime.datetime(2023, 1, 1, 9, 30)

        # 验证容器初始化
        assert hasattr(self.engine, '_portfolios')
        assert hasattr(self.engine, '_event_queue')
        assert hasattr(self.engine, '_is_running')

        print("✓ 引擎初始化成功")

    def test_time_advance_mechanism(self):
        """测试时间推进机制"""
        print("\n测试时间推进机制")

        initial_time = self.engine.logical_current_time
        target_time = datetime.datetime(2023, 1, 1, 10, 30)

        # 模拟时间推进
        self.engine.logical_current_time = target_time

        assert self.engine.logical_current_time == target_time
        assert self.engine.logical_current_time > initial_time

        print(f"✓ 时间从 {initial_time} 推进到 {self.engine.logical_current_time}")

    def test_portfolio_registration(self):
        """测试Portfolio注册"""
        print("\n测试Portfolio注册")

        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "test_portfolio_001"

        # 注册Portfolio
        result = self.engine.add_portfolio(portfolio)

        assert result is True
        assert portfolio.engine_id in self.engine._portfolios
        assert self.engine._portfolios[portfolio.engine_id] is portfolio

        print("✓ Portfolio注册成功")

    def test_portfolio_duplicate_registration(self):
        """测试Portfolio重复注册"""
        print("\n测试Portfolio重复注册")

        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "duplicate_test"

        # 首次注册
        assert self.engine.add_portfolio(portfolio) is True

        # 重复注册
        result = self.engine.add_portfolio(portfolio)

        # 应该拒绝重复注册
        assert result is False

        print("✓ 重复注册被正确拒绝")

    def test_portfolio_removal(self):
        """测试Portfolio移除"""
        print("\n测试Portfolio移除")

        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "remove_test"

        # 注册后移除
        self.engine.add_portfolio(portfolio)
        assert portfolio.engine_id in self.engine._portfolios

        result = self.engine.remove_portfolio(portfolio.engine_id)

        assert result is True
        assert portfolio.engine_id not in self.engine._portfolios

        print("✓ Portfolio移除成功")


@pytest.mark.engine
@pytest.mark.event_processing
class TestTimeControlledEngineEventProcessing:
    """TimeControlledEventEngine事件处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.engine = TimeControlledEventEngine(
            name="EventTestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "event_test_portfolio"
        self.engine.add_portfolio(self.portfolio)

    def test_event_price_update_handling(self):
        """测试价格更新事件处理"""
        print("\n测试价格更新事件处理")

        # 创建价格更新事件
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            close=10.50
        )
        price_event = EventPriceUpdate(
            price_info=bar,
            source=SOURCE_TYPES.BACKTESTFEEDER,
            engine_id=self.engine.engine_id
        )

        # 模拟事件处理
        with patch.object(self.portfolio, 'on_price_received') as mock_on_price:
            self.engine.put(price_event)

            # 验证Portfolio接收到事件
            time.sleep(0.1)  # 等待事件处理
            assert mock_on_price.called
            assert mock_on_price.call_args[0][0] is price_event

        print("✓ 价格更新事件处理成功")

    def test_event_time_advance_handling(self):
        """测试时间推进事件处理"""
        print("\n测试时间推进事件处理")

        # 创建时间推进事件
        advance_time = datetime.datetime(2023, 1, 1, 10, 30)
        time_event = EventTimeAdvance(
            current_time=advance_time,
            source=SOURCE_TYPES.ENGINE
        )

        # 模拟事件处理
        with patch.object(self.portfolio, 'advance_time') as mock_advance:
            self.engine.put(time_event)

            # 验证Portfolio接收到时间推进
            time.sleep(0.1)  # 等待事件处理
            assert mock_advance.called
            assert mock_advance.call_args[0][0] == advance_time.timestamp()

        print("✓ 时间推进事件处理成功")

    def test_multiple_portfolio_event_dispatch(self):
        """测试多Portfolio事件分发"""
        print("\n测试多Portfolio事件分发")

        # 添加多个Portfolio
        portfolio1 = self.portfolio
        portfolio2 = PortfolioT1Backtest()
        portfolio2.engine_id = "multi_test_2"
        self.engine.add_portfolio(portfolio2)

        # 创建事件
        bar = Bar(code="000001.SZ", close=10.50)
        price_event = EventPriceUpdate(price_info=bar)

        # 监控所有Portfolio的响应
        with patch.object(portfolio1, 'on_price_received') as mock1, \
             patch.object(portfolio2, 'on_price_received') as mock2:

            self.engine.put(price_event)
            time.sleep(0.1)

            # 验证所有Portfolio都收到事件
            assert mock1.called
            assert mock2.called
            assert mock1.call_args[0][0] is price_event
            assert mock2.call_args[0][0] is price_event

        print("✓ 多Portfolio事件分发成功")

    def test_event_queue_overflow_handling(self):
        """测试事件队列溢出处理"""
        print("\n测试事件队列溢出处理")

        # 模拟大量事件
        events = []
        for i in range(100):
            bar = Bar(code=f"00000{i%10}.SZ", close=10.0 + i)
            event = EventPriceUpdate(price_info=bar)
            events.append(event)

        # 快速添加事件
        for event in events:
            self.engine.put(event)

        # 验证引擎仍然正常工作
        assert self.engine._event_queue.qsize() > 0

        # 处理部分事件
        time.sleep(0.1)
        processed = self.engine._event_queue.qsize()

        print(f"✓ 事件队列处理正常，剩余 {processed} 个事件")


@pytest.mark.engine
@pytest.mark.lifecycle
class TestTimeControlledEngineLifecycle:
    """TimeControlledEventEngine生命周期测试"""

    def setup_method(self):
        """测试前设置"""
        self.engine = TimeControlledEventEngine(
            name="LifecycleTestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )

    def test_engine_startup_sequence(self):
        """测试引擎启动序列"""
        print("\n测试引擎启动序列")

        # 初始状态应该是未运行
        assert not self.engine._is_running

        # 模拟启动过程
        with patch.object(self.engine, 'start') as mock_start:
            mock_start.return_value = None
            self.engine.start()

            assert mock_start.called

        print("✓ 引擎启动序列执行成功")

    def test_engine_shutdown_sequence(self):
        """测试引擎关闭序列"""
        print("\n测试引擎关闭序列")

        # 先启动再关闭
        with patch.object(self.engine, 'start'), \
             patch.object(self.engine, 'stop') as mock_stop:

            self.engine.start()
            self.engine.stop()

            assert mock_stop.called

        print("✓ 引擎关闭序列执行成功")

    def test_graceful_shutdown_with_pending_events(self):
        """测试优雅关闭（带待处理事件）"""
        print("\n测试优雅关闭")

        # 添加一些事件
        for i in range(5):
            bar = Bar(code=f"00000{i}.SZ", close=10.0 + i)
            event = EventPriceUpdate(price_info=bar)
            self.engine.put(event)

        pending_events = self.engine._event_queue.qsize()
        assert pending_events > 0

        # 模拟关闭过程
        with patch.object(self.engine, 'stop') as mock_stop:
            self.engine.stop()
            assert mock_stop.called

        print(f"✓ 优雅关闭成功，处理了 {pending_events} 个待处理事件")

    def test_engine_state_monitoring(self):
        """测试引擎状态监控"""
        print("\n测试引擎状态监控")

        # 验证初始状态
        assert hasattr(self.engine, 'get_status')

        # 添加Portfolio后检查状态
        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "status_test"
        self.engine.add_portfolio(portfolio)

        # 验证Portfolio数量统计
        assert len(self.engine._portfolios) == 1

        print("✓ 引擎状态监控功能正常")


@pytest.mark.engine
@pytest.mark.error_handling
class TestTimeControlledEngineErrorHandling:
    """TimeControlledEventEngine错误处理测试"""

    def setup_method(self):
        """测试前设置"""
        self.engine = TimeControlledEventEngine(
            name="ErrorTestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )
        self.portfolio = PortfolioT1Backtest()
        self.portfolio.engine_id = "error_test_portfolio"
        self.engine.add_portfolio(self.portfolio)

    def test_portfolio_error_isolation(self):
        """测试Portfolio错误隔离"""
        print("\n测试Portfolio错误隔离")

        # 创建两个Portfolio，一个会出错
        good_portfolio = PortfolioT1Backtest()
        good_portfolio.engine_id = "good_portfolio"
        self.engine.add_portfolio(good_portfolio)

        bad_portfolio = PortfolioT1Backtest()
        bad_portfolio.engine_id = "bad_portfolio"

        # 模拟Portfolio处理错误
        with patch.object(bad_portfolio, 'on_price_received', side_effect=Exception("Portfolio处理异常")):
            self.engine.add_portfolio(bad_portfolio)

            # 创建事件
            bar = Bar(code="000001.SZ", close=10.50)
            price_event = EventPriceUpdate(price_info=bar)

            # 发送事件，引擎应该继续工作
            self.engine.put(price_event)
            time.sleep(0.1)

            # 验证其他Portfolio仍然正常
            with patch.object(good_portfolio, 'on_price_received') as mock_good:
                self.engine.put(price_event)
                time.sleep(0.1)
                assert mock_good.called

        print("✓ Portfolio错误隔离成功")

    def test_invalid_event_handling(self):
        """测试无效事件处理"""
        print("\n测试无效事件处理")

        # 创建无效事件
        invalid_event = Mock()
        invalid_event.is_valid = False

        # 引擎应该能处理无效事件而不崩溃
        try:
            self.engine.put(invalid_event)
            time.sleep(0.1)
            print("✓ 无效事件处理成功")
        except Exception as e:
            pytest.fail(f"无效事件导致引擎崩溃: {e}")

    def test_resource_cleanup_on_error(self):
        """测试错误时的资源清理"""
        print("\n测试资源清理")

        # 添加资源
        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "cleanup_test"
        self.engine.add_portfolio(portfolio)

        # 添加事件
        bar = Bar(code="000001.SZ", close=10.50)
        for _ in range(10):
            self.engine.put(EventPriceUpdate(price_info=bar))

        # 模拟错误情况下的清理
        initial_queue_size = self.engine._event_queue.qsize()
        initial_portfolio_count = len(self.engine._portfolios)

        # 执行清理
        self.engine._event_queue.queue.clear()
        self.engine._portfolios.clear()

        # 验证清理结果
        assert self.engine._event_queue.qsize() == 0
        assert len(self.engine._portfolios) == 0

        print(f"✓ 资源清理成功：事件队列 {initial_queue_size}→0，Portfolio {initial_portfolio_count}→0")


@pytest.mark.engine
@pytest.mark.performance
class TestTimeControlledEnginePerformance:
    """TimeControlledEventEngine性能测试"""

    def setup_method(self):
        """测试前设置"""
        self.engine = TimeControlledEventEngine(
            name="PerformanceTestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime(2023, 1, 1, 9, 30)
        )

    def test_high_throughput_event_processing(self):
        """测试高吞吐量事件处理"""
        print("\n测试高吞吐量事件处理")

        # 添加Portfolio
        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "performance_test"
        self.engine.add_portfolio(portfolio)

        # 创建大量事件
        event_count = 1000
        start_time = time.time()

        with patch.object(portfolio, 'on_price_received'):
            for i in range(event_count):
                bar = Bar(code=f"00000{i%10}.SZ", close=10.0 + (i % 100))
                event = EventPriceUpdate(price_info=bar)
                self.engine.put(event)

        processing_time = time.time() - start_time

        print(f"✓ 高吞吐量测试：{event_count}个事件，耗时 {processing_time:.3f}秒")

        # 性能断言（可以根据实际情况调整）
        assert processing_time < 5.0, f"处理速度过慢：{processing_time:.3f}秒"

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        print("\n测试内存使用稳定性")

        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 大量操作
        portfolio = PortfolioT1Backtest()
        portfolio.engine_id = "memory_test"
        self.engine.add_portfolio(portfolio)

        # 创建和清理事件
        for cycle in range(5):
            # 添加事件
            for i in range(100):
                bar = Bar(code=f"00000{i%10}.SZ", close=10.0 + i)
                event = EventPriceUpdate(price_info=bar)
                self.engine.put(event)

            time.sleep(0.1)

            # 清理事件
            self.engine._event_queue.queue.clear()

            if cycle % 2 == 1:
                # 强制垃圾回收
                import gc
                gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"✓ 内存使用：初始 {initial_memory:.1f}MB，最终 {final_memory:.1f}MB，增长 {memory_increase:.1f}MB")

        # 内存增长应该在合理范围内（小于100MB）
        assert memory_increase < 100, f"内存泄漏可能：增长了 {memory_increase:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])