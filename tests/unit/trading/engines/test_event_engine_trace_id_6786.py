"""
#6786 AC4: engine 子线程恢复 trace_id 守卫

contextvars 不跨线程自动传播：EventEngine 在 start() 自起的 main_loop / timer_loop
线程看不到 BacktestProcessor 线程 set 的 trace_id。修复方案：
  1. start() 在调用方线程（已 set trace_id）捕获 GLOG.get_trace_id() → self._trace_id
  2. main_loop / timer_loop 在 engine 子线程入口调 _restore_trace_context() 恢复

本套件验证恢复机制 + main_loop 入口调用 + 跨线程生效（AC4 真正达成，非仅
BacktestProcessor 主线程）。CI 全绿不能证伪——须显式 spawn 子线程才暴露原本的缺口。
"""
import sys
import threading
from pathlib import Path

import pytest
from unittest.mock import patch

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.libs import GLOG
from ginkgo.libs.core.logger import _trace_id_ctx


@pytest.mark.unit
class TestEventEngineTraceIdRestore:
    """#6786 AC4: engine 子线程 trace_id 恢复"""

    def test_restore_trace_context_sets_trace_id(self):
        """_restore_trace_context 把 self._trace_id set 到 _trace_id_ctx。"""
        engine = EventEngine()
        engine._trace_id = "tid-engine-001"

        token = _trace_id_ctx.set(None)
        try:
            engine._restore_trace_context()
            assert GLOG.get_trace_id() == "tid-engine-001"
        finally:
            _trace_id_ctx.reset(token)

    def test_restore_trace_context_noop_without_trace_id(self):
        """_trace_id 为 None 时不动 contextvars（向后兼容非 API 入口 / 旧消息）。"""
        engine = EventEngine()
        engine._trace_id = None

        token = _trace_id_ctx.set(None)
        try:
            engine._restore_trace_context()
            assert GLOG.get_trace_id() is None
        finally:
            _trace_id_ctx.reset(token)

    def test_restore_trace_context_works_in_spawned_thread(self):
        """机制核心：全新线程里 _restore_trace_context 能恢复 trace_id。

        真实场景：engine main_loop 跑在 spawn 的 Thread 中，父线程 contextvars
        不自动继承。证明 helper 在子线程内 set 生效——这是 AC4 的关键证据。
        """
        engine = EventEngine()
        engine._trace_id = "tid-spawn-002"

        _trace_id_ctx.set(None)  # 父线程无 trace_id
        seen = {}

        def runner():
            engine._restore_trace_context()
            seen["tid"] = GLOG.get_trace_id()

        t = threading.Thread(target=runner)
        t.start()
        t.join()

        assert seen["tid"] == "tid-spawn-002", (
            "engine 子线程未能恢复 trace_id——strategy/fill/portfolio 日志将无 trace_id"
        )

    def test_main_loop_restores_trace_id(self):
        """main_loop 入口恢复 trace_id，同线程 handler（_process → strategy/fill/portfolio）可见。

        预置 _main_flag 让 while 立即退出，不碰事件队列；main_loop 顶部已 set
        trace_id，返回后 get_trace_id() 应为 self._trace_id（clear_context 不动 _trace_id_ctx）。
        """
        engine = EventEngine()
        engine._trace_id = "tid-loop-003"
        engine._main_flag.set()  # while not is_set() → 立即退出

        token = _trace_id_ctx.set(None)
        try:
            engine.main_loop()
            assert GLOG.get_trace_id() == "tid-loop-003", (
                "main_loop 未在入口恢复 trace_id"
            )
        finally:
            _trace_id_ctx.reset(token)

    def test_timer_loop_restores_trace_id(self):
        """timer_loop 入口同样恢复 trace_id（与 main_loop 对称）。"""
        engine = EventEngine()
        engine._trace_id = "tid-timer-005"
        engine._timer_flag.set()  # while True → if is_set(): break 立即退出

        token = _trace_id_ctx.set(None)
        try:
            engine.timer_loop()
            assert GLOG.get_trace_id() == "tid-timer-005", (
                "timer_loop 未在入口恢复 trace_id"
            )
        finally:
            _trace_id_ctx.reset(token)

    def test_start_captures_current_trace_id(self):
        """start() 从当前线程捕获 GLOG.get_trace_id() → self._trace_id。

        模拟 BacktestProcessor 线程：trace_id 已 set，start() 应捕获供子线程恢复。
        mock 掉 super().start() 与 Thread.start()，避免真起引擎线程，只验捕获行。
        """
        engine = EventEngine()
        assert engine._trace_id is None  # 构造默认

        token = _trace_id_ctx.set("tid-capture-004")
        try:
            with patch("ginkgo.trading.engines.base_engine.BaseEngine.start", return_value=True), \
                 patch.object(engine._main_thread, "start"), \
                 patch.object(engine._timer_thread, "start"):
                engine.start()
            assert engine._trace_id == "tid-capture-004", (
                "start() 未捕获当前 trace_id，engine 子线程将无 trace_id 可恢复"
            )
        finally:
            _trace_id_ctx.reset(token)
