# Issue #6786 AC3: worker consume_tasks 从 Kafka header 恢复 trace_id 到 GLOG contextvars
#
# consume_tasks 内循环读 message.headers，with_trace_id 包 _handle_task_assignment，
# 使派发决策日志（_start_task 槽位等待 / 畸形处理 / offset 提交）带 trace_id，
# 与 API 提交端 grep 同一值串联。engine 线程的 trace_id 传播由 BacktestProcessor
# 接力（_start_task 取 contextvars 传 processor，run() 入口恢复，见对应测试）。

import pytest
from unittest.mock import MagicMock


class TestWorkerDispatchMessageRestoresTraceId:
    """#6786 AC3: worker _dispatch_message 从 Kafka header 恢复 trace_id"""

    def test_dispatch_restores_trace_id_from_header(self):
        """message.headers 含 trace_id 时，_handle_task_assignment 在 trace_id contextvars 内执行。"""
        from ginkgo.workers.backtest_worker.node import BacktestWorker
        from ginkgo.libs import GLOG

        worker = BacktestWorker("test-trace-restore")
        captured = {}

        def spy(assignment):
            captured["tid"] = GLOG.get_trace_id()

        worker._handle_task_assignment = spy

        msg = MagicMock()
        msg.value = {"task_uuid": "t1", "command": "start", "portfolio_uuid": "p1"}
        msg.headers = [("trace_id", b"tid-worker-001")]

        worker._dispatch_message(msg)

        assert captured.get("tid") == "tid-worker-001", \
            f"_handle_task_assignment 应在 trace_id contextvars 内执行, got {captured.get('tid')}"

    def test_dispatch_no_header_no_trace_id(self):
        """message.headers 无 trace_id 时，_handle_task_assignment 在无 trace_id 上下文执行（向后兼容）。"""
        from ginkgo.workers.backtest_worker.node import BacktestWorker
        from ginkgo.libs import GLOG
        from ginkgo.libs.core.logger import _trace_id_ctx

        worker = BacktestWorker("test-trace-none")
        captured = {}

        def spy(assignment):
            captured["tid"] = GLOG.get_trace_id()

        worker._handle_task_assignment = spy

        token = _trace_id_ctx.set(None)
        try:
            msg = MagicMock()
            msg.value = {"task_uuid": "t2", "command": "start", "portfolio_uuid": "p2"}
            msg.headers = None

            worker._dispatch_message(msg)
        finally:
            _trace_id_ctx.reset(token)

        assert captured.get("tid") is None, "无 header 时不应注入 trace_id（向后兼容旧消息）"

    def test_dispatch_ignores_malformed_header_bytes(self):
        """header value 非 valid UTF-8 bytes 时 graceful 降级（不抛、不注入 trace_id）。"""
        from ginkgo.workers.backtest_worker.node import BacktestWorker
        from ginkgo.libs import GLOG
        from ginkgo.libs.core.logger import _trace_id_ctx

        worker = BacktestWorker("test-trace-malformed")
        captured = {}

        def spy(assignment):
            captured["tid"] = GLOG.get_trace_id()

        worker._handle_task_assignment = spy

        token = _trace_id_ctx.set(None)
        try:
            msg = MagicMock()
            msg.value = {"task_uuid": "t3", "command": "start", "portfolio_uuid": "p3"}
            # 非 UTF-8 字节序列（解码失败须降级，不得抛 UnicodeDecodeError 进 consume except）
            msg.headers = [("trace_id", b"\xff\xfe\x00bad")]

            worker._dispatch_message(msg)  # 不应抛
        finally:
            _trace_id_ctx.reset(token)

        # 解码失败 → 不注入 trace_id（None），但 _handle_task_assignment 仍被调（不阻断消费）
        assert captured.get("tid") is None
