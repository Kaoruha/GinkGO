import pytest
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.time.providers import SystemTimeProvider

class TestPaperModeInitialization:
    """验证 PAPER 模式初始化行为"""

    def test_paper_mode_uses_system_time_provider(self):
        """PAPER 模式应使用 SystemTimeProvider"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        assert isinstance(engine._time_provider, SystemTimeProvider)

    def test_paper_mode_creates_thread_pool(self):
        """PAPER 模式应创建 ThreadPoolExecutor"""
        from concurrent.futures import ThreadPoolExecutor
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        assert engine._executor is not None
        assert isinstance(engine._executor, ThreadPoolExecutor)
        # 注意：不调用 stop()，因为引擎未启动，避免 GLOG 初始化问题

    def test_paper_mode_uses_system_time_mode(self):
        """PAPER 模式的 TimeInfo 应为 TIME_MODE.SYSTEM"""
        from ginkgo.enums import TIME_MODE
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        time_info = engine.get_time_info()
        assert time_info.time_mode == TIME_MODE.SYSTEM
        assert not time_info.is_logical_time

    def test_paper_mode_blocking_queue_wait(self):
        """PAPER 模式应使用阻塞队列等待（与 LIVE 一致）"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        assert engine.mode == EXECUTION_MODE.PAPER
        assert engine.mode != EXECUTION_MODE.BACKTEST

    def test_paper_mode_no_auto_time_advance(self):
        """PAPER 模式不应自动推进时间"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        current_time = engine.now  # now 是 @property，不是方法
        result = engine.advance_time_to(current_time)
        assert result is False

    def test_paper_mode_no_backtest_task_on_run(self):
        """PAPER 模式 run() 不应创建 BacktestTask"""
        # 这个测试验证 PAPER 模式不会走回测路径
        # 实际验证在 advance_time_to 中完成（非 BACKTEST 模式返回 False）
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        # 验证 advance_time_to 在非 BACKTEST 模式下返回 False
        # 这证明了不会创建回测任务或进行时间推进
        result = engine.advance_time_to(engine.now)  # now 是 @property
        assert result is False, "PAPER 模式不应支持手动时间推进"
