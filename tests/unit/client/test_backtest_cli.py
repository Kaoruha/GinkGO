# #5329 backtest cat 输出提示 result show 用法
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

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """去除 ANSI 转义码"""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _mock_task():
    """构造一个 mock backtest task 对象"""
    task = MagicMock()
    task.uuid = "abc123456789"
    task.task_id = "task-run-id-001"
    task.name = "Test Backtest"
    task.portfolio_id = "port-001"
    task.engine_id = "engine-001"
    task.status = "completed"
    task.progress = 100
    task.create_at = "2025-01-01"
    task.start_time = "2025-01-01T10:00:00"
    task.end_time = "2025-01-01T10:05:00"
    task.duration_seconds = "300"
    task.error_message = None
    task.config_snapshot = None
    # metrics（float 属性，0.0 跳过展示块）
    task.final_portfolio_value = 0.0
    task.total_pnl = 0.0
    task.max_drawdown = 0.0
    task.sharpe_ratio = 0.0
    task.annual_return = 0.0
    task.win_rate = 0.0
    # stats（int 属性，0 跳过展示块）
    task.total_signals = 0
    task.total_orders = 0
    task.total_positions = 0
    task.total_events = 0
    return task


class TestBacktestCatResultHint:
    """#5329 backtest cat 应提示 result show 用法"""

    @patch("ginkgo.data.containers.container")
    def test_cat_shows_result_show_hint(self, mock_container):
        """#5329 backtest cat 输出应包含 result show --run-id 提示"""
        from ginkgo.client.backtest_cli import app

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = _mock_task()
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "task-run-id-001"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        # 应包含提示，指引用户使用 result show --run-id
        assert "result show --run-id" in plain
        # 提示应包含实际的 task_id
        assert "task-run-id-001" in plain


class TestBacktestListProgressFormat:
    """#5323 list 命令 progress 格式化应为 N% 而非 N00%"""

    @patch("ginkgo.data.containers.container")
    def test_list_shows_correct_progress_percentage(self, mock_container):
        """#5323 progress=50 应显示 50% 而非 5000%"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.progress = 50
        task.status = "running"  # progress=50 进行中；避免 completed 兜底(#5996)干扰格式化断言

        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        # progress=50 应显示 "50%" 而非 "5000%"
        assert "50%" in plain
        assert "5000%" not in plain

    @patch("ginkgo.data.containers.container")
    def test_list_shows_100_percent_on_completed(self, mock_container):
        """#5323 completed 任务 progress=100 应显示 100%"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.progress = 100
        task.status = "completed"

        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        assert "100%" in plain
        assert "10000%" not in plain


class TestBacktestCatNoTradesWarning:
    """#5322 completed 回测无交易时应显示警告"""

    @patch("ginkgo.data.containers.container")
    def test_cat_shows_no_trades_warning_when_zero_stats(self, mock_container):
        """#5322 completed 回测 stats 全为 0 时应显示 'No trades' 提示"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.status = "completed"
        # stats 全为 0（默认值）
        task.total_signals = 0
        task.total_orders = 0
        task.total_positions = 0
        task.total_events = 0

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = task
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "abc123456789"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        assert "No trades" in plain or "未产生" in plain or "no trades" in plain.lower()


class TestBacktestCompletedProgressFallback:
    """#5996 completed 回测即使 DB progress=0（旧任务完成回调未更新）也应兜底显示 100%"""

    @patch("ginkgo.data.containers.container")
    def test_list_completed_zero_progress_shows_100(self, mock_container):
        """#5996 list: status=completed + progress=0 → 兜底 100%（复现 issue 现场）

        根因: backtest_cli.py:369 原样输出 task.progress，无 completed 语义兜底。
        990 条历史 completed 任务 DB progress=0，全显 0%。
        """
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.status = "completed"
        task.progress = 0  # 旧任务 DB 未被完成回调更新，复现 issue 现场

        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        # 兜底: completed 必显 100%，而非原样 0%
        assert "100%" in plain

    @patch("ginkgo.data.containers.container")
    def test_cat_completed_zero_progress_shows_100(self, mock_container):
        """#5996 cat: status=completed + progress=0 → 兜底 100%

        与 list 同根因，cat 输出层也须兜底，保证两命令一致。
        """
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.status = "completed"
        task.progress = 0  # 旧任务 DB 未更新

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = task
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "abc123456789"])
        assert invoke_result.exit_code == 0

        plain = _strip_ansi(invoke_result.output)
        assert "100%" in plain


class TestBacktestRunTaskExitGuard:
    """#6449 review: run_task 失败路径的 typer.Exit 必须透传，不能被 except Exception 吞。

    PR #6590 已为 8+ CLI 文件建立 `except typer.Exit: raise` 守卫；backtest_cli 是漏网者。
    吞掉后果：typer.Exit(1) 被 except Exception 捕获，str(e)=='1'，error_message 被
    覆盖成 '1' 丢失 preflight 真因（#6590 类陷阱）。
    """

    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_failure_path_does_not_swallow_typer_exit(
        self, mock_orch_cls, mock_container):
        """run_from_task 返失败时，不应把 error_message 写成 str(typer.Exit)=='1'。"""
        from ginkgo.client.backtest_cli import app
        from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-exit-001"
        task.portfolio_id = "port-exit"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30"}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        # UseCase 层报业务事实（success=False + 真实原因），CLI 翻译为 typer.Exit
        mock_orch = MagicMock()
        mock_orch.run_from_task.return_value = OrchestratorResult(
            success=False, error="preflight blocked: data coverage insufficient",
        )
        mock_orch_cls.return_value = mock_orch

        invoke_result = runner.invoke(app, ["run", "task-exit-001"])

        # typer.Exit(1) 必须透传到 CliRunner（exit_code=1）
        assert invoke_result.exit_code == 1, (
            f"期望 exit_code=1，实际 {invoke_result.exit_code}；"
            f"exception={invoke_result.exception!r}"
        )
        # 真实原因应在输出中（L228 先打印 result.error）
        plain = _strip_ansi(invoke_result.output)
        assert "preflight blocked" in plain, (
            f"输出应含真实 preflight 原因，实际: {plain!r}"
        )
        # 关键守卫断言：typer.Exit 被 except Exception 吞后 str(e)=='1' 会覆盖真因。
        # 守卫就位时 L252 不执行，update_status 不会被写成 error_message='1'。
        error_messages = [
            str(c.kwargs.get("error_message"))
            for c in mock_service.update_status.call_args_list
            if "error_message" in c.kwargs
        ]
        assert "1" not in error_messages, (
            "typer.Exit 不应被 except Exception 吞（#6590/#6449 守卫）："
            f"update_status error_messages={error_messages}"
        )


class TestBacktestRunTaskBgGuard:
    """#6449 re-review: --bg 模式 run_from_task 抛异常时 bg 线程不得静默死亡。

    master 把 preflight/config 解析放主线程同步执行（try 外、bg 分支前），bg 线程只
    调自带 try/except 的 orchestrator.run()，从不静默死亡。本 PR 把这些路径下沉进
    run_from_task 并搬进 bg 线程，却没镜像非 bg 路径的 except Exception 守卫 → bg 线程
    抛异常（JSONDecodeError / preflight DB 不可达 / BacktestConfig 构造）时静默死亡、
    CLI exit 0、task 卡 pending，与 ADR-022 §3 "UseCase 层从不静默失败" 自相矛盾。
    """

    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_bg_thread_marks_failed_on_run_from_task_exception(
        self, mock_orch_cls, mock_container):
        """--bg 模式 run_from_task 抛异常时，必须标 task failed + 印原因，不得静默死亡。"""
        import time
        from ginkgo.client.backtest_cli import app

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-bg-001"
        task.portfolio_id = "port-bg"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30"}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        # run_from_task 抛异常：模拟 _json.loads 损坏 / preflight DB 不可达 / BacktestConfig 构造异常。
        # 这些路径在到达自带 try/except 的 self.run() 之前抛出，bg 线程无 handler 即静默死亡。
        boom = RuntimeError("config_snapshot JSON corrupted: boom")
        mock_orch = MagicMock()
        mock_orch.run_from_task.side_effect = boom
        mock_orch_cls.return_value = mock_orch

        invoke_result = runner.invoke(app, ["run", "task-bg-001", "--bg"])

        # 主线程立即返回（exit 0，bg 线程后台跑）——这是 bg 模式契约，不是 bug
        assert invoke_result.exit_code == 0, (
            f"--bg 主线程应 exit 0，实际 {invoke_result.exit_code}；"
            f"exception={invoke_result.exception!r}"
        )

        # 轮询等待 bg 线程跑完异常处理（daemon 线程异步，最多等 2s）
        deadline = time.monotonic() + 2.0
        failed_call = None
        while time.monotonic() < deadline:
            for c in mock_service.update_status.call_args_list:
                # 镜像非 bg 路径：update_status(task.uuid, "failed", error_message=str(e))
                if len(c.args) >= 2 and c.args[1] == "failed":
                    failed_call = c
                    break
            if failed_call is not None:
                break
            time.sleep(0.02)

        # 关键守卫断言：bg 线程内 run_from_task 抛异常 → 必须标 failed（而非静默死亡）。
        # 守卫缺失时 bg 线程无 handler 死亡，update_status 永不被调 → failed_call is None。
        assert failed_call is not None, (
            "--bg 模式 run_from_task 抛异常时必须标 task failed + 印原因"
            "（ADR-022 §3 不静默）；update_status 未收到 failed 调用 = bg 线程静默死亡。"
            f" calls={mock_service.update_status.call_args_list}"
        )
        # error_message 应含真实异常信息（非空、非 '1'）
        err = failed_call.kwargs.get("error_message")
        assert err and "boom" in str(err), (
            f"error_message 应含异常真因，实际: {err!r}"
        )


class TestBacktestRunTaskBanner:
    """#6449 review fix: 非 bg 模式补回 master 启动 banner（Period/Capital/Portfolio）。

    config 下沉到 run_from_task 后，banner 字段从 task.config_snapshot 轻量取。
    回归契约：用户 `ginkgo backtest run <id>` 应看到回测参数概览（master 既有 UX），
    不能因下沉丢失。
    """

    @patch("ginkgo.services.logging.log_ingester.LogIngester")
    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_non_bg_prints_starting_banner(
        self, mock_orch_cls, mock_container, mock_log_cls):
        from ginkgo.client.backtest_cli import app
        from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

        # 屏蔽 ClickHouse 日志灌入（避免真实连接副作用）
        mock_log_cls.return_value.ingest_task_logs.return_value = MagicMock(inserted=0)

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-banner-001"
        task.name = "MyBacktest"
        task.portfolio_id = "port-banner-123456"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30", "initial_cash": 999999}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        mock_orch = MagicMock()
        mock_orch.run_from_task.return_value = OrchestratorResult(success=True, data={})
        mock_orch_cls.return_value = mock_orch

        invoke_result = runner.invoke(app, ["run", "task-banner-001"])

        assert invoke_result.exit_code == 0, (
            f"期望 exit_code=0，实际 {invoke_result.exit_code}；"
            f"exception={invoke_result.exception!r}"
        )
        plain = _strip_ansi(invoke_result.output)
        assert "MyBacktest" in plain, f"输出应含 task.name，实际: {plain!r}"
        assert "2024-01-01" in plain and "2024-06-30" in plain, (
            f"输出应含 Period（start/end），实际: {plain!r}"
        )
        assert "999999" in plain, f"输出应含 Capital，实际: {plain!r}"
        assert "port-banner-" in plain, f"输出应含 Portfolio 截断，实际: {plain!r}"


class TestBacktestRunTaskListDataGuard:
    """#6449 review fix: result.data 是 list（非 dict）时 FINALIZING 不得抛 AttributeError。

    OrchestratorResult.data 可能是 list（backtest_orchestrator.py:98 有 isinstance(list)
    分支）。master 用 str(config.end_date) 不依赖 data 类型；本 PR 改成 result.data.get(...)，
    若 data 是 list，.get 抛 AttributeError。守卫：isinstance(result.data, dict) 退化 ""。
    """

    @patch("ginkgo.services.logging.log_ingester.LogIngester")
    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_non_dict_data_does_not_raise(
        self, mock_orch_cls, mock_container, mock_log_cls):
        from ginkgo.client.backtest_cli import app
        from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

        mock_log_cls.return_value.ingest_task_logs.return_value = MagicMock(inserted=0)

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-list-001"
        task.portfolio_id = "port-list"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30"}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        # run_from_task 返回 list data（aggregator list 路径）+ success
        mock_orch = MagicMock()
        mock_orch.run_from_task.return_value = OrchestratorResult(
            success=True, data=["net_value_row_1", "net_value_row_2"],
        )
        mock_orch_cls.return_value = mock_orch

        invoke_result = runner.invoke(app, ["run", "task-list-001"])

        # 关键守卫：list data 不应抛 AttributeError（.get 在 list 上不存在）。
        # 守卫缺失时（if result.data else）list truthy 进 .get 抛 AttributeError，
        # CliRunner 捕获 → exception 非 None + exit_code=1。
        assert invoke_result.exception is None, (
            f"list data 路径不应抛异常；exception={invoke_result.exception!r}"
        )
        assert invoke_result.exit_code == 0, (
            f"list data 路径应 exit 0；实际 {invoke_result.exit_code}"
        )
        # FINALIZING update_progress 应被调用（说明走到非 bg 成功路径末段未崩）
        assert mock_service.update_progress.called, (
            "list data 不应阻断 FINALIZING update_progress 调用"
        )
