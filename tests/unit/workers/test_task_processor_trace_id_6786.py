# Issue #6786 AC4: BacktestProcessor 接力 trace_id 到 engine 线程
#
# contextvars 不跨线程自动传播：consume 线程 with_trace_id 设的 trace_id 到不了
# processor.start() spawn 的 engine 线程。_start_task 从 consume 上下文取出 trace_id
# 传入 BacktestProcessor 构造，run() 入口 _init_trace_context 手动 set _trace_id_ctx，
# 使 engine/strategy/fill/portfolio 日志带 trace_id（全链路串联，AC4）。

import inspect
from threading import Event
from unittest.mock import MagicMock

import pytest

from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor
from ginkgo.libs import GLOG
from ginkgo.libs.core.logger import _trace_id_ctx


def _make_processor(trace_id=None):
    """构造最小可测处理器（跳过 __init__ service 容器装配，参考 test_task_processor_error_logging）。"""
    proc = BacktestProcessor.__new__(BacktestProcessor)
    proc.task = MagicMock()
    proc.task.task_uuid = "t-trace"
    proc.worker_id = "w-test"
    proc.progress_tracker = MagicMock()
    proc._stop_event = Event()
    proc._engine = None
    proc._exception = None
    proc._result = {}
    proc.trace_id = trace_id  # 模拟 __init__ 改后存的属性
    return proc


class TestBacktestProcessorTraceIdRelay:
    """#6786 AC4: BacktestProcessor engine 线程接力 trace_id"""

    @pytest.mark.unit
    def test_init_trace_context_sets_trace_id(self):
        """_init_trace_context 把 self.trace_id set 到 _trace_id_ctx（engine 线程入口恢复）。"""
        proc = _make_processor(trace_id="tid-proc-999")

        token = _trace_id_ctx.set(None)
        try:
            proc._init_trace_context()
            assert GLOG.get_trace_id() == "tid-proc-999", \
                "run() 入口须恢复 trace_id，否则 engine 线程日志无 trace_id（contextvars 不跨线程）"
        finally:
            _trace_id_ctx.reset(token)

    @pytest.mark.unit
    def test_init_trace_context_no_trace_id_noop(self):
        """无 trace_id 时 _init_trace_context 不动 contextvars（向后兼容旧消息/非 API 入口）。"""
        proc = _make_processor(trace_id=None)

        token = _trace_id_ctx.set(None)
        try:
            proc._init_trace_context()
            assert GLOG.get_trace_id() is None
        finally:
            _trace_id_ctx.reset(token)

    @pytest.mark.unit
    def test_init_signature_accepts_trace_id_kwarg(self):
        """__init__ 须接 trace_id 可选 kwarg（_start_task 接力 consume 上下文传入）。"""
        sig = inspect.signature(BacktestProcessor.__init__)
        assert "trace_id" in sig.parameters, \
            f"__init__ 须接 trace_id 参数, 实际: {list(sig.parameters)}"
        assert sig.parameters["trace_id"].default is None, \
            "trace_id 默认 None（向后兼容 node.py:388 之外的现有 3 参构造）"
