# Issue #6786 AC5: ginkgo backtest cat 显示 trace_id（从 task.meta JSON 解析）
#
# API 写 task.meta={"trace_id":...}（任务 #3），cat 须解析显示，让运维 grep trace_id
# 串联 API→worker 全链路（AC4 闭环 + AC5 机读/人读）。

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import re
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from ginkgo.client.backtest_cli import _task_record

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """去除 ANSI 转义码"""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _mock_task(meta="{}"):
    """构造 mock backtest task（参考 test_backtest_cli._mock_task，补 meta 字段）。"""
    task = MagicMock()
    task.uuid = "abc123456789"
    task.task_id = "task-run-id-001"
    task.name = "Test Backtest"
    task.portfolio_id = "port-001"
    task.engine_id = "engine-001"
    task.status = "completed"
    task.progress = 100
    task.create_at = "2025-01-01"
    task.start_time = None
    task.end_time = None
    task.duration_seconds = None
    task.error_message = None
    task.config_snapshot = None
    task.final_portfolio_value = 0.0
    task.total_pnl = 0.0
    task.max_drawdown = 0.0
    task.sharpe_ratio = 0.0
    task.annual_return = 0.0
    task.win_rate = 0.0
    task.total_signals = 0
    task.total_orders = 0
    task.total_positions = 0
    task.total_events = 0
    task.meta = meta
    return task


class TestBacktestCatTraceId:
    """#6786 AC5: cat 显示从 meta 解析的 trace_id（人读 text + 机读 json 双路径）"""

    def test_record_extracts_trace_id_from_meta_json(self):
        """_task_record 从 task.meta JSON 解析 trace_id（json 机读路径，AC5）。"""
        task = _mock_task(meta=json.dumps({"trace_id": "tid-cat-001"}))
        record = _task_record(task)
        assert record["trace_id"] == "tid-cat-001", \
            "cat --format json 须暴露 trace_id，供运维 grep 串联 API→worker 全链路（AC5）"

    def test_record_trace_id_none_when_meta_empty(self):
        """meta 无 trace_id（'{}'/旧任务）时 record.trace_id is None（向后兼容）。"""
        task = _mock_task(meta="{}")
        assert _task_record(task)["trace_id"] is None

    @patch("ginkgo.data.containers.container")
    def test_cat_text_shows_trace_id_line(self, mock_container):
        """cat text 模式输出含 trace_id 行（人读路径，AC5）。"""
        from ginkgo.client.backtest_cli import app

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = _mock_task(meta=json.dumps({"trace_id": "tid-cat-002"}))
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "abc12345"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        assert "tid-cat-002" in plain, "cat text 须显示 trace_id 值（AC5 人读路径）"
        assert "Trace ID" in plain or "trace_id" in plain.lower(), \
            "须有 Trace ID 标签行（可读性，运维一眼定位）"
