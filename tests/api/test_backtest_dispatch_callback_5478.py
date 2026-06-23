# Issue #5478: backtest Kafka 派发 fire-and-forget 失败静默
#
# 根因：api/api/backtest.py:379 `asyncio.create_task(send_task_to_kafka(...))`
#   无 add_done_callback；producer.send 失败时异常被 asyncio 吞，任务永留
#   PENDING，API 已返回 success。
# 修复：create_backtest 给 create_task 挂 add_done_callback，回调调模块级
#   `_on_kafka_dispatch_done(task_uuid, asyncio_task)`——失败时记日志 +
#   BacktestTaskService.update_status(status="failed", error_message=...)。
#
# 方案 A（保留异步语义）：create_backtest 仍立即返回 ok(task)；AC3「return 500」
#   在异步架构下不可行（已 return），改为「任务状态 PENDING→FAILED 可查」。

import pytest
from unittest.mock import patch, MagicMock


class TestBacktestDispatchFailureCallback:
    """#5478: Kafka 派发失败不再静默——done_callback 记日志 + 更新任务 failed"""

    def test_dispatch_failure_marks_task_failed(self, api_modules):
        """派发协程抛异常时，任务状态更新为 failed 并记录错误日志"""
        from api.backtest import _on_kafka_dispatch_done

        fake_task = MagicMock()
        fake_task.cancelled.return_value = False
        fake_task.exception.return_value = RuntimeError("Kafka broker unreachable")

        with patch("api.backtest.get_backtest_task_service") as mock_get_svc, \
             patch("api.backtest.logger") as mock_logger:
            mock_svc = MagicMock()
            mock_get_svc.return_value = mock_svc

            _on_kafka_dispatch_done("task-abc-123", fake_task)

            # 失败时更新任务状态为 failed，含错误信息
            mock_svc.update_status.assert_called_once()
            call = mock_svc.update_status.call_args
            assert call.args[0] == "task-abc-123"
            assert call.kwargs.get("status") == "failed"
            err_msg = call.kwargs.get("error_message", "")
            assert "Kafka broker unreachable" in err_msg
            # 记录错误日志
            mock_logger.error.assert_called()

    def test_dispatch_success_does_not_mark_failed(self, api_modules):
        """派发协程成功（无异常）时，不应更新任务状态"""
        from api.backtest import _on_kafka_dispatch_done

        fake_task = MagicMock()
        fake_task.cancelled.return_value = False
        fake_task.exception.return_value = None  # 成功

        with patch("api.backtest.get_backtest_task_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_get_svc.return_value = mock_svc

            _on_kafka_dispatch_done("task-ok-456", fake_task)

            mock_svc.update_status.assert_not_called()

    def test_dispatch_cancelled_does_not_mark_failed(self, api_modules):
        """派发协程被取消时，不应更新任务状态"""
        from api.backtest import _on_kafka_dispatch_done

        fake_task = MagicMock()
        fake_task.cancelled.return_value = True

        with patch("api.backtest.get_backtest_task_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_get_svc.return_value = mock_svc

            _on_kafka_dispatch_done("task-cancelled-789", fake_task)

            mock_svc.update_status.assert_not_called()


class TestSendTaskToKafkaTranslatesBoolFailure:
    """#5478 review P0：GinkgoProducer.send 返 bool 不 raise（ginkgo_kafka.py:89-123
    三处 return False，成功 return True），send_task_to_kafka 必须判返回值
    False→raise。否则协程无异常，create_task 的 done_callback 里
    asyncio_task.exception() 永远 None，失败分支（落库 failed）是死代码。"""

    @pytest.mark.asyncio
    async def test_raises_when_producer_send_returns_false(self, api_modules):
        """producer.send 返 False（未连接/KafkaError/异常）时，send_task_to_kafka
        必须显式 raise，让异常进入 asyncio task 供 done_callback 捕获。"""
        from api.backtest import send_task_to_kafka

        fake_producer = MagicMock()
        fake_producer.send.return_value = False  # send 契约：返 bool 非 raise

        with patch("api.backtest.get_kafka_producer", return_value=fake_producer):
            with pytest.raises(RuntimeError, match="Kafka dispatch failed"):
                await send_task_to_kafka(
                    task_uuid="task-fail-001",
                    portfolio_uuids=["port-1"],
                    name="bt",
                    config={"k": "v"},
                )

    @pytest.mark.asyncio
    async def test_does_not_raise_when_producer_send_returns_true(self, api_modules):
        """producer.send 返 True（成功）时，send_task_to_kafka 正常完成不抛。"""
        from api.backtest import send_task_to_kafka

        fake_producer = MagicMock()
        fake_producer.send.return_value = True

        with patch("api.backtest.get_kafka_producer", return_value=fake_producer):
            await send_task_to_kafka(
                task_uuid="task-ok-002",
                portfolio_uuids=["port-1"],
                name="bt",
                config={"k": "v"},
            )
            fake_producer.send.assert_called_once()


class TestDispatchFailureE2eRealChain:
    """#5478 端到端：走真实 asyncio.create_task → send_task_to_kafka →
    _on_kafka_dispatch_done 链路（非 mock task.exception），证明死代码已激活——
    send 返 False → send_task_to_kafka raise → 异常存入 task → done_callback
    经 exception() 捕获 → 落库 failed。这是 AC2 的真实证据。"""

    @pytest.mark.asyncio
    async def test_e2e_send_false_marks_task_failed_via_done_callback(self, api_modules):
        """producer.send 返 False 时，完整派发链路自动落库 failed（done_callback
        经 asyncio_task.exception() 真实捕获，非测试直接注入异常）。"""
        import asyncio
        from api.backtest import send_task_to_kafka, _on_kafka_dispatch_done

        fake_producer = MagicMock()
        fake_producer.send.return_value = False

        with patch("api.backtest.get_kafka_producer", return_value=fake_producer), \
             patch("api.backtest.get_backtest_task_service") as mock_get_svc:
            mock_svc = MagicMock()
            mock_get_svc.return_value = mock_svc

            task = asyncio.create_task(send_task_to_kafka(
                task_uuid="task-e2e-003",
                portfolio_uuids=["p1"],
                name="bt",
                config={},
            ))
            task.add_done_callback(lambda t: _on_kafka_dispatch_done("task-e2e-003", t))

            # send_task_to_kafka 会 raise（Slice 1 已证）；await 重抛，吞掉让
            # done_callback 执行。done_callback 经 call_soon 调度，await 返回后
            # 让出一轮确保回调落库完成。
            try:
                await task
            except RuntimeError:
                pass
            await asyncio.sleep(0)

            # 真实链路：异常经 task.exception() 被 done_callback 捕获 → 落库 failed
            mock_svc.update_status.assert_called_once()
            call = mock_svc.update_status.call_args
            assert call.args[0] == "task-e2e-003"
            assert call.kwargs.get("status") == "failed"
            assert "producer.send returned False" in call.kwargs.get("error_message", "")
