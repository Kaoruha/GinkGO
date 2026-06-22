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
