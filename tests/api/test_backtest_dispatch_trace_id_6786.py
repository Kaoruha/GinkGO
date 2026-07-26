# Issue #6786: backtest 跨进程 trace_id 经 Kafka header 传播（可观测层 2/4）
#
# 根因：api/api/backtest.py send_task_to_kafka 派发 Kafka 消息时不携带 trace_id，
#   worker 消费侧拿不到，engine/strategy/fill/portfolio 日志无 trace_id，无法把
#   一次回测的 API 提交端与 worker 执行端日志关联排障。
# 修复：send_task_to_kafka 从 GLOG contextvars 取 trace_id（#6784 中间件已注入），
#   写入 producer.send 的 headers=[("trace_id", bytes)]，worker 消费时从
#   message.headers 恢复到 GLOG contextvars。

import asyncio
from unittest.mock import patch, MagicMock


class TestBacktestDispatchTraceIdHeader:
    """#6786: backtest Kafka 派发携带 trace_id header"""

    def test_dispatch_propagates_trace_id_header(self, api_modules):
        """GLOG contextvars 有 trace_id 时，producer.send 收到 headers=[("trace_id", bytes)]。

        #6784 TraceIdMiddleware 在请求入口把 trace_id 注入 GLOG contextvars；
        #6786 派发时从 contextvars 取出写入 Kafka header，跨进程传给 worker。
        """
        from api.backtest import send_task_to_kafka
        from ginkgo.libs import GLOG

        fake_producer = MagicMock()
        fake_producer.send.return_value = True

        with patch("api.backtest.get_kafka_producer", return_value=fake_producer), \
             GLOG.with_trace_id("tid-abc-123"):
            asyncio.run(
                send_task_to_kafka("task-1", ["port-1"], "name", {"engine_uuid": "e1"})
            )

        fake_producer.send.assert_called_once()
        _, kwargs = fake_producer.send.call_args
        # header 值须为 bytes（kafka-python 要求），key 为 trace_id
        assert kwargs.get("headers") == [("trace_id", b"tid-abc-123")]

    def test_dispatch_no_trace_id_no_header(self, api_modules):
        """GLOG contextvars 无 trace_id 时，不写 header（向后兼容，不污染消息）。"""
        from api.backtest import send_task_to_kafka
        from ginkgo.libs import GLOG
        from ginkgo.libs.core.logger import _trace_id_ctx

        # 显式隔离：确保本测试 contextvars trace_id 为 None（防前序测试残留）
        token = _trace_id_ctx.set(None)
        try:
            fake_producer = MagicMock()
            fake_producer.send.return_value = True

            with patch("api.backtest.get_kafka_producer", return_value=fake_producer):
                asyncio.run(
                    send_task_to_kafka("task-2", ["port-2"], "name", {})
                )
        finally:
            _trace_id_ctx.reset(token)

        _, kwargs = fake_producer.send.call_args
        assert kwargs.get("headers") is None
