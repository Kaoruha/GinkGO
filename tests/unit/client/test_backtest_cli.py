# #5329 backtest cat 输出提示 result show 用法
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
    def test_list_json_format_outputs_adr021_contract(self, mock_container):
        """--format json 输出 list 契约，含 count/metadata。"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list", "--format", "json", "--limit", "1"])

        assert invoke_result.exit_code == 0
        payload = json.loads(invoke_result.output)
        assert payload["success"] is True
        assert payload["count"] == 1
        assert payload["metadata"] == {"total": 1, "limit": 1, "offset": 0}
        assert payload["data"][0]["uuid"] == "abc123456789"

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
    def test_cat_not_found_json_format_outputs_not_found_contract(self, mock_container):
        """--format json 下 cat 未找到输出 NOT_FOUND 错误对象。"""
        from ginkgo.client.backtest_cli import app

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = False
        result.error = "Not found"
        fuzzy_result = MagicMock()
        fuzzy_result.is_success.return_value = True
        fuzzy_result.data = []
        mock_service.get_by_id.return_value = result
        mock_service.fuzzy_search.return_value = fuzzy_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "missing-task", "--format", "json"])

        assert invoke_result.exit_code == 1
        payload = json.loads(invoke_result.output)
        assert payload["success"] is False
        assert payload["error"] == {"code": "NOT_FOUND", "message": "Backtest task not found: missing-task"}

    @patch("ginkgo.data.containers.container")
    def test_cat_fuzzy_multi_match_json_envelope(self, mock_container):
        """ADR-021 第 1/5 维：--format json + fuzzy 多匹配 → stdout 合法 JSON VALIDATION_ERROR envelope + exit 1。"""
        from ginkgo.client.backtest_cli import app

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = False
        result.error = "Not found"
        t1 = MagicMock(uuid="aaaa111122223333", name="bt-a", status="completed", create_at=None)
        t2 = MagicMock(uuid="bbbb555566667777", name="bt-b", status="running", create_at=None)
        fuzzy_result = MagicMock()
        fuzzy_result.is_success.return_value = True
        fuzzy_result.data = [t1, t2]
        mock_service.get_by_id.return_value = result
        mock_service.fuzzy_search.return_value = fuzzy_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "abc", "--format", "json"])

        assert invoke_result.exit_code == 1
        payload = json.loads(invoke_result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "VALIDATION_ERROR"
        assert "Multiple tasks match 'abc'" in payload["error"]["message"]

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


class TestBacktestRunTaskBgIngest:
    """#6704: --bg 成功分支必须镜像非 bg 路径调 ingest_task_logs。

    否则 --bg 回测日志不灌入 ClickHouse、``logging logs --task`` 恒空
    （#5293 在 --bg 场景仍复现；#6564 review 曾标范围外）。对称非 bg 路径 L279-288。
    """

    @patch("ginkgo.services.logging.log_ingester.LogIngester")
    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_bg_success_ingests_task_logs(
        self, mock_orch_cls, mock_container, mock_log_cls):
        """--bg 成功后必须调 ingest_task_logs(task.uuid)，与非 bg 路径对称。"""
        import time
        from ginkgo.client.backtest_cli import app
        from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

        mock_ingester = MagicMock()
        mock_ingester.ingest_task_logs.return_value = MagicMock(inserted=0)
        mock_log_cls.return_value = mock_ingester

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-bg-ingest-001"
        task.portfolio_id = "port-bg"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30"}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        mock_orch = MagicMock()
        mock_orch.run_from_task.return_value = OrchestratorResult(success=True, data={})
        mock_orch_cls.return_value = mock_orch

        invoke_result = runner.invoke(app, ["run", "task-bg-ingest-001", "--bg"])

        # 主线程立即返回 exit 0（bg 契约，daemon 线程后台跑）
        assert invoke_result.exit_code == 0, (
            f"--bg 主线程应 exit 0，实际 {invoke_result.exit_code}；"
            f"exception={invoke_result.exception!r}"
        )

        # 轮询等待 bg 线程跑到 ingest（daemon 异步，最多等 2s）
        deadline = time.monotonic() + 2.0
        ingest_call = None
        while time.monotonic() < deadline:
            for c in mock_ingester.ingest_task_logs.call_args_list:
                if c.args and c.args[0] == "task-bg-ingest-001":
                    ingest_call = c
                    break
            if ingest_call is not None:
                break
            time.sleep(0.02)

        # 守卫断言：--bg 成功必须调 ingest_task_logs（镜像非 bg L279-288）。
        # 守卫缺失时 --bg 回测日志不灌入 → logging logs --task 恒空（#5293 --bg 场景）。
        assert ingest_call is not None, (
            "--bg 成功后必须调 ingest_task_logs(task.uuid) 灌入日志"
            "（镜像非 bg 路径，#5293 --bg 场景）；"
            "ingest_task_logs 未被调用 = --bg 回测日志恒不灌入。"
            f" calls={mock_ingester.ingest_task_logs.call_args_list}"
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


class TestBacktestRunTaskPreflightWarningDisplay:
    """#6449 re-review #2: CLI 失败分支应印全文 preflight_warning（含 #6282 sync 指引）。

    UseCase 层把 warning 全文放 data['preflight_warning']，CLI 翻译层负责展示。
    不再只印被截断的 error 字段——master 行为是 console.print(warning) 印全文。
    bg/非 bg 两分支对称（ADR-022 §3 不静默）。
    """

    @patch("ginkgo.services.logging.log_ingester.LogIngester")
    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_nonbg_preflight_failure_prints_full_warning(
        self, mock_orch_cls, mock_container, mock_log_cls):
        """非 bg preflight 失败：输出含 #6282 sync 指引 + 尾部 symbol（全文未截断）。"""
        from ginkgo.client.backtest_cli import app
        from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

        mock_log_cls.return_value.ingest_task_logs.return_value = MagicMock(inserted=0)

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-pfdisp"
        task.portfolio_id = "port-pfdisp"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30"}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        # UseCase 层报业务事实：固定短语 error + 全文 warning in data（>200 字符）
        full_warning = (
            ":warning: Data preflight failed: 4 symbol(s) have insufficient bars\n"
            "   Window: 2024-01-01 ~ 2024-06-30\n"
            "   - 000001.SZ: 5 bar(s)\n"
            "   - 000002.SZ: 5 bar(s)\n"
            "   - 000063.SZ: 5 bar(s)\n"
            "   - 000333.SZ: 5 bar(s)\n"
            ":bulb: Tip: sync day bars first — "
            "`ginkgo data sync --code <CODE>` or widen the backtest window."
        )
        mock_orch = MagicMock()
        mock_orch.run_from_task.return_value = OrchestratorResult(
            success=False,
            error="preflight blocked: data coverage insufficient",
            data={"preflight_warning": full_warning},
        )
        mock_orch_cls.return_value = mock_orch

        invoke_result = runner.invoke(app, ["run", "task-pfdisp"])

        assert invoke_result.exit_code == 1, (
            f"非 bg preflight 失败应 exit 1，实际 {invoke_result.exit_code}；"
            f"exception={invoke_result.exception!r}"
        )
        plain = _strip_ansi(invoke_result.output)
        # 关键：#6282 symbol 级 sync 指引必须出现在输出（曾因 error[:200] 被截掉）
        assert "ginkgo data sync" in plain, (
            f"输出应含 #6282 全文 sync 指引，实际: {plain!r}"
        )
        # 尾部 symbol 也应出现（证明全文未截断，000333 在 200 字符之后）
        assert "000333.SZ" in plain, (
            f"输出应含尾部 symbol 000333.SZ，实际: {plain!r}"
        )

    @patch("ginkgo.services.logging.log_ingester.LogIngester")
    @patch("ginkgo.data.containers.container")
    @patch("ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator")
    def test_bg_preflight_failure_uses_emit_helper(
        self, mock_orch_cls, mock_container, mock_log_cls):
        """--bg 模式 preflight 失败也走 _emit_backtest_failure（与非 bg 对称印全文 warning）。

        bg 线程内 console.print 输出时机不可靠（daemon 线程，invoke 已返回），
        故 spy 模块级 _emit_backtest_failure 验证 bg 失败分支调用了它且传入含
        preflight_warning 的 result（与非 bg 分支共用 helper = 对称）。
        """
        import time as _time
        from ginkgo.client import backtest_cli
        from ginkgo.client.backtest_cli import app
        from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

        mock_log_cls.return_value.ingest_task_logs.return_value = MagicMock(inserted=0)

        mock_service = MagicMock()
        get_result = MagicMock()
        get_result.is_success.return_value = True
        task = MagicMock()
        task.uuid = "task-bg-pf"
        task.portfolio_id = "port-bg-pf"
        task.config_snapshot = '{"start_date": "2024-01-01", "end_date": "2024-06-30"}'
        get_result.data = task
        mock_service.get_by_id.return_value = get_result
        mock_container.backtest_task_service.return_value = mock_service

        full_warning = (
            ":warning: Data preflight failed: 4 symbol(s) have insufficient bars\n"
            "   - 000333.SZ: 5 bar(s)\n"
            ":bulb: Tip: `ginkgo data sync --code <CODE>` or widen the backtest window."
        )
        mock_orch = MagicMock()
        mock_orch.run_from_task.return_value = OrchestratorResult(
            success=False,
            error="preflight blocked: data coverage insufficient",
            data={"preflight_warning": full_warning},
        )
        mock_orch_cls.return_value = mock_orch

        # wraps 保留原实现（bg 线程仍真实打印），spy 仅记录调用
        with patch.object(
            backtest_cli, "_emit_backtest_failure",
            wraps=backtest_cli._emit_backtest_failure,
        ) as spy_emit:
            invoke_result = runner.invoke(app, ["run", "task-bg-pf", "--bg"])
            # 轮询等 bg daemon 线程跑到失败分支（最多 2s）
            deadline = _time.monotonic() + 2.0
            while _time.monotonic() < deadline and spy_emit.call_count == 0:
                _time.sleep(0.02)

        assert invoke_result.exit_code == 0, (
            f"--bg 主线程应 exit 0（bg 线程后台跑），实际 {invoke_result.exit_code}"
        )
        assert spy_emit.call_count >= 1, (
            "--bg 失败分支应调用 _emit_backtest_failure（与非 bg 对称印全文 warning），"
            f"实际调用次数 {spy_emit.call_count} = bg 分支仍只印截断 error"
        )
        result_arg = spy_emit.call_args.args[0]
        assert result_arg.data.get("preflight_warning") == full_warning, (
            "传给 helper 的 result 应携带全文 preflight_warning"
        )


class TestBacktestCatJsonResultData:
    """#6580 backtest cat --format json 须输出完整回测结果数据

    text 路径渲染的 final_portfolio_value/total_pnl/max_drawdown/sharpe_ratio
    等核心指标在 JSON 路径缺失（PR #6652 review 打回）。_task_record 补全字段，
    让机读消费者在 JSON 路径拿到与 text 等量的结构化回测结果（ADR-021 初衷）。
    """

    @patch("ginkgo.data.containers.container")
    def test_cat_json_includes_full_result_data(self, mock_container):
        """--format json 成功路径输出含 metrics + statistics + 执行信息。"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.status = "completed"
        # 回测结果 metrics（text 路径 Results panel）
        task.final_portfolio_value = 125000.0
        task.total_pnl = 25000.0
        task.max_drawdown = -0.12
        task.sharpe_ratio = 1.85
        task.annual_return = 0.23
        task.win_rate = 0.62
        # 统计（text 路径 Statistics panel）
        task.total_signals = 42
        task.total_orders = 38
        task.total_positions = 15
        task.total_events = 500
        # 执行信息
        task.start_time = "2025-01-01T10:00:00"
        task.end_time = "2025-01-01T10:05:00"
        task.duration_seconds = 300
        task.error_message = None

        mock_service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        result.data = task
        mock_service.get_by_id.return_value = result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["cat", "abc123456789", "--format", "json"])

        assert invoke_result.exit_code == 0
        payload = json.loads(invoke_result.output)
        assert payload["success"] is True
        record = payload["data"]
        # Results metrics（reviewer 点名的核心指标）
        assert record["final_portfolio_value"] == 125000.0
        assert record["total_pnl"] == 25000.0
        assert record["max_drawdown"] == -0.12
        assert record["sharpe_ratio"] == 1.85
        assert record["annual_return"] == 0.23
        assert record["win_rate"] == 0.62
        # Statistics
        assert record["total_signals"] == 42
        assert record["total_orders"] == 38
        assert record["total_positions"] == 15
        assert record["total_events"] == 500
        # 执行信息
        assert record["start_time"] == "2025-01-01T10:00:00"
        assert record["end_time"] == "2025-01-01T10:05:00"
        assert record["duration_seconds"] == 300
        assert record["error_message"] is None


class TestBacktestListJsonResultMetrics:
    """#6580 list --format json 也含回测结果 metrics

    _task_record 被 list/cat 共用，扩展后 list 每个 record 同步带上 metrics，
    回测列表可机读每个任务收益/回撤（ADR-021 机读收益）。
    """

    @patch("ginkgo.data.containers.container")
    def test_list_json_includes_metrics(self, mock_container):
        """--format json list 每个 record 含 final_portfolio_value/sharpe_ratio 等。"""
        from ginkgo.client.backtest_cli import app

        task = _mock_task()
        task.status = "completed"
        task.final_portfolio_value = 125000.0
        task.total_pnl = 25000.0
        task.max_drawdown = -0.12
        task.sharpe_ratio = 1.85

        mock_service = MagicMock()
        list_result = MagicMock()
        list_result.is_success.return_value = True
        list_result.data = {"data": [task], "total": 1}
        mock_service.list.return_value = list_result
        mock_container.backtest_task_service.return_value = mock_service

        invoke_result = runner.invoke(app, ["list", "--format", "json", "--limit", "1"])

        assert invoke_result.exit_code == 0
        payload = json.loads(invoke_result.output)
        record = payload["data"][0]
        assert record["final_portfolio_value"] == 125000.0
        assert record["sharpe_ratio"] == 1.85
        assert record["total_pnl"] == 25000.0
        assert record["max_drawdown"] == -0.12
