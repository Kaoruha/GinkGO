"""
BacktestWorker node 测试

覆盖 #5399 子问题 ②③：
- ③ task_uuid 用完整值查 self.tasks 去重（node.py:234 [:8] 截断 bug）
- ② Kafka offset 在任务派发决策后提交（at-least-once 语义）
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)


def _make_assignment(task_uuid: str = "abcdef1234567890abcdef1234567890") -> dict:
    """构造合法的 Kafka 任务分配 payload（含 _start_task 所需全部必填字段）"""
    return {
        "task_uuid": task_uuid,  # 完整 32 hex，验证 [:8] 截断不误判
        "portfolio_uuid": "portfolio-uuid-full",
        "name": "dedup-test",
        "command": "start",
        "config": {
            "start_date": "2025-01-01",
            "end_date": "2025-06-01",
            "initial_cash": 100000.0,
        },
    }


@pytest.mark.unit
class TestStartTaskDedupByFullUuid:
    """③ #5399: _start_task 必须用完整 task_uuid 查 self.tasks 去重

    bug: node.py:234 `task_uuid = ...[:8]` 截断后用于 :238 查找，
    而 :354 存储用完整 `task.task_uuid`，两者 key 永不匹配 →
    同一任务的重复 start 不被去重，processor 被重复创建并覆盖。
    """

    def test_duplicate_start_task_uuid_deduped(self):
        """同一完整 task_uuid 连续两次 _start_task，第二次应被去重（processor 仅创建一次）"""
        from ginkgo.workers.backtest_worker.node import BacktestWorker

        worker = BacktestWorker("test-dedup")
        # __init__ 不连外部，progress_tracker 为 None；注入 mock 跳过 DB 状态检查
        worker.progress_tracker = MagicMock()
        worker.progress_tracker.get_task_status.return_value = None  # DB 无既有记录

        # ADR-018：_start_task 接收 StartAssignment（DTO）非裸 dict
        from ginkgo.interfaces.dtos.backtest_assignment_dto import from_payload
        cmd = from_payload(_make_assignment())

        with patch("ginkgo.workers.backtest_worker.node.BacktestProcessor") as MockProc:
            MockProc.return_value = MagicMock()
            worker._start_task(cmd)
            worker._start_task(cmd)  # 重复派发同一任务

        # 修复后：第二次被 self.tasks 完整 UUID 检测拦截，processor 只创建一次
        assert MockProc.call_count == 1, (
            f"重复 task_uuid 应被去重，但 BacktestProcessor 被创建 {MockProc.call_count} 次"
        )


@pytest.mark.unit
class TestHandleAssignmentCommitTiming:
    """② #5399: Kafka offset 必须在任务派发决策完成「之后」提交

    bug: node.py consume_tasks:209 在 _handle_task_assignment(:213)「之前」
    无条件 commit，违反 at-least-once——若派发/处理抛异常，消息已 commit，
    worker 重启后不会重投，任务静默丢失。
    修复：commit 移到 _handle_task_assignment 正常完成决策后；异常不 commit。
    """

    def test_commits_offset_after_successful_dispatch(self):
        """派发决策完成后提交 Kafka offset（commit 在 _start_task 之后调用）"""
        from ginkgo.workers.backtest_worker.node import BacktestWorker

        worker = BacktestWorker("test-commit")
        worker.task_consumer = MagicMock()
        worker.progress_tracker = MagicMock()
        worker.progress_tracker.get_task_status.return_value = None

        with patch("ginkgo.workers.backtest_worker.node.BacktestProcessor"):
            worker._handle_task_assignment(_make_assignment())

        # commit 必须在派发决策完成「之后」调用（at-least-once）
        worker.task_consumer.commit.assert_called_once()

    def test_no_commit_offset_on_dispatch_exception(self):
        """② 派发/处理异常时不提交 offset，留给重启后 Kafka 重投 + DB 去重"""
        from ginkgo.workers.backtest_worker.node import BacktestWorker

        worker = BacktestWorker("test-commit-err")
        worker.task_consumer = MagicMock()
        worker.progress_tracker = MagicMock()
        worker.progress_tracker.get_task_status.return_value = None

        # _start_task 内创建 BacktestProcessor 抛异常（模拟派发失败）
        with patch(
            "ginkgo.workers.backtest_worker.node.BacktestProcessor",
            side_effect=RuntimeError("dispatch boom"),
        ):
            with pytest.raises(RuntimeError):
                worker._handle_task_assignment(_make_assignment())

        # 异常分支绝不提交 offset（at-least-once：重启后重投）
        worker.task_consumer.commit.assert_not_called()
