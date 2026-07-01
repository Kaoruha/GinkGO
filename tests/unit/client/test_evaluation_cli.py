"""
TDD for ginkgo eval 三命令(stability/monitor-create/monitor-live)恢复。

背景:#4652 误把 import 路径漂移当"未实现",加 return stub 屏蔽。
底层 BacktestEvaluator 实现完好,3 调用方在用。本测试守护命令真正调通 evaluator,
并防回归(输出不得再含 "not yet implemented")。
"""

import sys
import json
import re
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
sys.path.insert(0, _path)

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

runner = CliRunner()

from ginkgo.client.evaluation_cli import app  # noqa: E402

# patch 源模块(命令体为函数级 import,每次执行从源模块取属性)
_EVALUATOR_PATH = "ginkgo.trading.analysis.evaluation.backtest_evaluator.BacktestEvaluator"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _success_result() -> dict:
    """匹配 _display_stability_results / _display_baseline_summary 期望的键。"""
    return {
        "status": "success",
        "evaluation_time": "2026-07-01T10:00:00",
        "portfolio_id": "port-001",
        # 返回键是 task_id(ADR-016),展示层读 engine_id → 兼容读取
        "task_id": "task-001",
        "data_summary": {
            "analyzer_records": 100,
            "signal_records": 50,
            "order_records": 40,
            "time_span": {"days": 244},
        },
        "optimal_slice_config": {
            "period_days": 30,
            "stability_score": 0.85,
            "slice_count": 8,
        },
        "stability_analysis": {
            "cross_metric_comparison": {
                "ranking": [("sharpe", 0.85), ("max_drawdown", 0.72)],
            }
        },
        "recommendations": ["consider more slices"],
        "monitoring_baseline": {
            "slice_period_days": 30,
            "total_slices": 8,
            "creation_time": "2026-07-01",
            "baseline_stats": {
                "sharpe": {"mean": 1.2, "std_dev": 0.3, "range": 0.9},
            },
        },
    }


# ---- stability ----

def test_stability_success():
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = _success_result()

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app, ["stability", "--portfolio", "port-001", "--engine", "task-001"]
        )

    out = _strip_ansi(result.output)
    assert result.exit_code == 0, result.output
    assert "not yet implemented" not in out
    mock_evaluator.evaluate_backtest_stability.assert_called_once_with(
        portfolio_id="port-001",
        task_id="task-001",
        start_date=None,
        end_date=None,
    )
    # 展示层渲染了 result 关键值
    assert "port-001" in out
    assert "244" in out  # time span days
    assert "0.8500" in out  # stability_score :.4f


def test_stability_no_stub():
    """防回归 #4652: 不得再 return stub。"""
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = _success_result()

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app, ["stability", "--portfolio", "port-001", "--engine", "task-001"]
        )

    out = _strip_ansi(result.output)
    assert "not yet implemented" not in out
    assert "4639" not in out  # TODO issue 链接也不应在用户输出里


def test_stability_failed():
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = {
        "status": "failed",
        "reason": "invalid_data",
    }

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app, ["stability", "--portfolio", "port-001", "--engine", "task-001"]
        )

    out = _strip_ansi(result.output)
    assert result.exit_code == 0
    assert "invalid_data" in out


def test_stability_portfolio_required():
    """--portfolio/--engine 必填(删交互式列出后)。"""
    result = runner.invoke(app, ["stability"])
    assert result.exit_code != 0  # typer 缺必填参数


# ---- monitor-create ----

def test_monitor_create_success(tmp_path):
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate_backtest_stability.return_value = _success_result()
    out_file = tmp_path / "baseline.json"

    with patch(_EVALUATOR_PATH, return_value=mock_evaluator):
        result = runner.invoke(
            app,
            [
                "monitor-create",
                "-p", "port-001",
                "-e", "task-001",
                "-o", str(out_file),
            ],
        )

    assert result.exit_code == 0, result.output
    assert "not yet implemented" not in _strip_ansi(result.output)
    assert out_file.exists()
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["slice_period_days"] == 30


# ---- monitor-live ----

def test_monitor_live_no_stub(tmp_path):
    """monitor-live 去 stub 后真调 create_live_monitor(demo loop 用异常短路)。"""
    baseline_file = tmp_path / "b.json"
    baseline_file.write_text(
        json.dumps(_success_result()["monitoring_baseline"]), encoding="utf-8"
    )

    mock_evaluator = MagicMock()
    # 让 demo loop 第一次 sleep 即抛错,被 except Exception 捕获后正常返回
    with patch(_EVALUATOR_PATH, return_value=mock_evaluator), \
            patch(
                "time.sleep",
                side_effect=RuntimeError("short-circuit demo loop"),
            ):
        result = runner.invoke(
            app,
            [
                "monitor-live",
                "-b", str(baseline_file),
                "-p", "port-001",
                "--interval", "1",
            ],
        )

    out = _strip_ansi(result.output)
    assert "not yet implemented" not in out
    assert mock_evaluator.create_live_monitor.called
