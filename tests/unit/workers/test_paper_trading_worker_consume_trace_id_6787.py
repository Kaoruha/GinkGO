"""#6787: paper worker 消费恢复 trace_id（可观测层 3/4, AC2/AC3）

_consume_loop 消费 CONTROL_COMMANDS 时，_dispatch_command 从 message.headers
恢复 trace_id 到 GLOG contextvars，with_trace_id 包 _handle_command，使 deploy
操作日志（_handle_deploy 的 GLOG.INFO/ERROR）带 trace_id，与 API deploy 端
grep 同一值串联（AC4）。覆盖 paper + live（_handle_deploy 接受 PAPER/LIVE mode）。
无 header / 解码失败时 graceful 降级（不注入，不阻断消费，向后兼容旧消息）。
"""
import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch


def _make_worker():
    from ginkgo.workers.paper_trading_worker import PaperTradingWorker
    return PaperTradingWorker(worker_id="test-trace-6787")


def _make_message(headers, command="deploy", params=None):
    """构造 mock Kafka message: headers + value(dict)。"""
    message = MagicMock()
    message.headers = headers
    message.value = {"command": command, "params": params or {"portfolio_id": "p-1"}}
    return message


def _mock_cmd(command="deploy", params=None):
    c = MagicMock()
    c.command = command
    c.params = params or {"portfolio_id": "p-1"}
    return c


class TestDispatchCommandRestoresTraceId:
    """#6787 AC2/AC3: paper worker 消费恢复 trace_id"""

    def test_restores_trace_id_from_header(self):
        """message.headers 带 trace_id 时，_handle_command 在 with_trace_id 作用域内执行。"""
        from ginkgo.libs import GLOG

        worker = _make_worker()
        captured = {}

        def fake_handle(command, params):
            captured["trace_id"] = GLOG.get_trace_id()
            captured["command"] = command
            return True

        worker._handle_command = fake_handle
        worker._send_response = MagicMock()

        message = _make_message([("trace_id", b"tid-paper-6787")])

        with patch("ginkgo.interfaces.mappers.message_mapper.MessageMapper.decode",
                   return_value=_mock_cmd()):
            worker._dispatch_command(message)

        assert captured["trace_id"] == "tid-paper-6787"
        assert captured["command"] == "deploy"

    def test_no_header_no_trace_id(self):
        """无 header（旧消息/非 API 入口）时 _handle_command 内 trace_id 为 None（向后兼容）。"""
        from ginkgo.libs import GLOG
        from ginkgo.libs.core.logger import _trace_id_ctx

        token = _trace_id_ctx.set(None)
        try:
            worker = _make_worker()
            captured = {}

            def fake_handle(command, params):
                captured["trace_id"] = GLOG.get_trace_id()

            worker._handle_command = fake_handle
            worker._send_response = MagicMock()

            message = _make_message(headers=None)

            with patch("ginkgo.messages.control_command.ControlCommand.from_dict",
                       return_value=_mock_cmd()):
                worker._dispatch_command(message)
        finally:
            _trace_id_ctx.reset(token)

        assert captured["trace_id"] is None

    def test_malformed_header_graceful(self):
        """header trace_id 解码失败（非法 UTF-8）时 graceful 降级：不抛、不注入。"""
        from ginkgo.libs import GLOG
        from ginkgo.libs.core.logger import _trace_id_ctx

        token = _trace_id_ctx.set(None)
        try:
            worker = _make_worker()
            captured = {}

            def fake_handle(command, params):
                captured["trace_id"] = GLOG.get_trace_id()

            worker._handle_command = fake_handle
            worker._send_response = MagicMock()

            # 非法 UTF-8 字节序列
            message = _make_message([("trace_id", b"\xff\xfe\x00")])

            with patch("ginkgo.messages.control_command.ControlCommand.from_dict",
                       return_value=_mock_cmd()):
                # 不应抛异常（毒丸消息不阻断消费）
                worker._dispatch_command(message)
        finally:
            _trace_id_ctx.reset(token)

        assert captured["trace_id"] is None
