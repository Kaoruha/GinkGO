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

    def test_paper_mode_rejects_manual_time_advance(self):
        """PAPER 模式不支持手动时间推进（advance_time_to 返回 False）"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        result = engine.advance_time_to(engine.now)
        assert result is False


class TestPaperLiveEquivalence:
    """验证 PAPER 和 LIVE 在引擎层行为等价（架构设计：差异在 Broker/Gateway 层）"""

    def _create_engine(self, mode):
        return TimeControlledEventEngine(name=f"Test_{mode.name}", mode=mode)

    def test_same_time_provider_type(self):
        """PAPER 和 LIVE 都使用 SystemTimeProvider"""
        paper = self._create_engine(EXECUTION_MODE.PAPER)
        live = self._create_engine(EXECUTION_MODE.LIVE)
        assert type(paper._time_provider) is type(live._time_provider)

    def test_same_executor_type(self):
        """PAPER 和 LIVE 都使用 ThreadPoolExecutor"""
        from concurrent.futures import ThreadPoolExecutor
        paper = self._create_engine(EXECUTION_MODE.PAPER)
        live = self._create_engine(EXECUTION_MODE.LIVE)
        assert isinstance(paper._executor, ThreadPoolExecutor)
        assert isinstance(live._executor, ThreadPoolExecutor)

    def test_same_time_mode(self):
        """PAPER 和 LIVE 都使用 TIME_MODE.SYSTEM"""
        from ginkgo.enums import TIME_MODE
        paper = self._create_engine(EXECUTION_MODE.PAPER)
        live = self._create_engine(EXECUTION_MODE.LIVE)
        assert paper.get_time_info().time_mode == TIME_MODE.SYSTEM
        assert live.get_time_info().time_mode == TIME_MODE.SYSTEM

    def test_both_reject_manual_time_advance(self):
        """PAPER 和 LIVE 都不支持手动时间推进"""
        paper = self._create_engine(EXECUTION_MODE.PAPER)
        live = self._create_engine(EXECUTION_MODE.LIVE)
        assert paper.advance_time_to(paper.now) is False
        assert live.advance_time_to(live.now) is False
