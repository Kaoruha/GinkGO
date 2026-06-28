"""
ADR-018 第③步：消费端 from_payload + match 判别联合 + assignment_to_backtest_config 映射

覆盖：
- 映射函数 StartAssignment→BacktestConfig（11 字段 + analyzers 转换 + 缺字段拒）
- _handle_task_assignment 分派：start→_start_task / stop→WARN no-op(A1) / cancel→_cancel_task
- 畸形 payload：report_failed + 提交 offset（at-least-once，不重投）

详见 docs/adrs/ADR-018-backtest-assignment-contract.md
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.interfaces.dtos.backtest_assignment_dto import (
    from_payload, StartAssignment, MalformedAssignmentError,
)
from ginkgo.workers.backtest_worker.models import (
    BacktestConfig, AnalyzerConfig, assignment_to_backtest_config,
)


def _make_start_cmd(**config_overrides) -> StartAssignment:
    raw = {
        "task_uuid": "abcdef1234567890abcdef1234567890",
        "portfolio_uuid": "portfolio-1",
        "name": "test",
        "command": "start",
        "config": {"start_date": "2025-01-01", "end_date": "2025-06-01", **config_overrides},
    }
    return from_payload(raw)


# ---------- 映射函数（DTO 信使 → worker 状态主体）----------

class TestAssignmentToBacktestConfig:
    @pytest.mark.unit
    def test_maps_eleven_fields(self):
        cmd = _make_start_cmd(initial_cash=500000.0, frequency="WEEK")
        cfg = assignment_to_backtest_config(cmd)
        assert isinstance(cfg, BacktestConfig)
        assert cfg.start_date == "2025-01-01"
        assert cfg.end_date == "2025-06-01"
        assert cfg.initial_cash == 500000.0
        assert cfg.frequency == "WEEK"
        assert cfg.commission_rate == 0.0003  # DTO 唯一默认表补齐

    @pytest.mark.unit
    def test_maps_analyzers(self):
        cmd = _make_start_cmd(analyzers=[{"name": "wr", "type": "analyzer", "config": {"w": 30}}])
        cfg = assignment_to_backtest_config(cmd)
        assert len(cfg.analyzers) == 1
        assert isinstance(cfg.analyzers[0], AnalyzerConfig)
        assert cfg.analyzers[0].name == "wr"

    @pytest.mark.unit
    def test_rejects_malformed_analyzer(self):
        """analyzer dict 缺字段 → MalformedAssignmentError（与消费端窄捕一致）。"""
        cmd = _make_start_cmd(analyzers=[{"name": "wr"}])  # 缺 type
        with pytest.raises(MalformedAssignmentError):
            assignment_to_backtest_config(cmd)


# ---------- 分派 match ----------

class TestHandleAssignmentDispatch:
    def _worker(self):
        from ginkgo.workers.backtest_worker.node import BacktestWorker
        worker = BacktestWorker("test-dispatch")
        worker.task_consumer = MagicMock()
        worker.progress_tracker = MagicMock()
        worker.progress_tracker.get_task_status.return_value = None
        return worker

    @pytest.mark.unit
    def test_start_dispatches_to_start_task(self):
        worker = self._worker()
        with patch("ginkgo.workers.backtest_worker.node.BacktestProcessor"):
            worker._handle_task_assignment({
                "task_uuid": "abcdef1234567890abcdef1234567890",
                "portfolio_uuid": "p", "name": "n", "command": "start",
                "config": {"start_date": "s", "end_date": "e"},
            })
        worker.task_consumer.commit.assert_called_once()

    @pytest.mark.unit
    def test_stop_no_op_warns(self):
        """ADR-018 A1：stop 消费侧 handler 未实现，WARN no-op（不调 _start_task/_cancel_task）但仍提交 offset。"""
        worker = self._worker()
        worker._start_task = MagicMock()
        worker._cancel_task = MagicMock()
        worker._handle_task_assignment({"task_uuid": "abc123", "command": "stop"})
        worker._start_task.assert_not_called()
        worker._cancel_task.assert_not_called()
        worker.task_consumer.commit.assert_called_once()  # no-op 仍提交 offset

    @pytest.mark.unit
    def test_cancel_dispatches_to_cancel_task(self):
        worker = self._worker()
        worker._cancel_task = MagicMock()
        worker._handle_task_assignment({"task_uuid": "xyz", "command": "cancel"})
        worker._cancel_task.assert_called_once_with("xyz")
        worker.task_consumer.commit.assert_called_once()

    @pytest.mark.unit
    def test_malformed_marks_failed_and_commits(self):
        """畸形契约：report_failed + 提交 offset（at-least-once，不重投），不进 _start_task。"""
        worker = self._worker()
        worker._start_task = MagicMock()
        worker._handle_task_assignment({"task_uuid": "bad", "command": "unknown"})  # 未知 command
        worker.progress_tracker.report_failed_by_uuid.assert_called_once()
        worker._start_task.assert_not_called()
        worker.task_consumer.commit.assert_called_once()
