"""
Tests for BacktestOrchestrator.

Verifies that the orchestrator correctly sequences the backtest lifecycle:
load task → build config → load portfolio → assemble → run → wait → aggregate.
"""
import datetime
from unittest.mock import MagicMock, patch, call
import pytest

from ginkgo.trading.services.backtest_orchestrator import BacktestOrchestrator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config():
    """Minimal BacktestConfig-like object."""
    cfg = MagicMock()
    cfg.start_date = "2025-01-01"
    cfg.end_date = "2025-12-31"
    cfg.initial_cash = 100000
    cfg.commission_rate = 0.0003
    cfg.slippage_rate = 0.0001
    cfg.frequency = "DAY"
    return cfg


def _make_portfolio_result():
    """Simulates lightweight portfolio metadata (no components)."""
    portfolio = MagicMock()
    portfolio.name = "TestPortfolio"
    portfolio.cash = 100000.0
    portfolio.initial_capital = 100000.0
    return portfolio


def _make_engine_mock():
    engine = MagicMock()
    main_thread = MagicMock()
    main_thread.is_alive.return_value = False
    engine._main_thread = main_thread
    engine.portfolios = []
    return engine


def _make_components():
    """Standard categorized components dict."""
    return {"strategies": [], "sizers": [], "selectors": [],
            "risk_managers": [], "analyzers": []}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_assembly_service():
    return MagicMock()


@pytest.fixture
def mock_portfolio_service():
    return MagicMock()


@pytest.fixture
def mock_task_service():
    return MagicMock()


@pytest.fixture
def mock_aggregator():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_assembly_service, mock_portfolio_service,
                 mock_task_service, mock_aggregator):
    return BacktestOrchestrator(
        assembly_service=mock_assembly_service,
        portfolio_service=mock_portfolio_service,
        task_service=mock_task_service,
        result_aggregator=mock_aggregator,
    )


# ===========================================================================
# Tracer bullet: full happy path
# ===========================================================================


class TestOrchestratorHappyPath:
    """Verify the orchestrator sequences the full backtest lifecycle."""

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_run_calls_services_in_order(self, mock_load_components, orchestrator,
                                          mock_assembly_service,
                                          mock_portfolio_service,
                                          mock_aggregator):
        config = _make_config()
        portfolio_id = "portfolio-001"
        task_id = "task-001"
        engine = _make_engine_mock()

        # Portfolio service returns lightweight metadata
        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True,
            data=[_make_portfolio_result()],
        )

        # load_portfolio_components returns categorized dict
        mock_load_components.return_value = _make_components()

        # Assembly service returns engine
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True,
            data=engine,
        )

        # Aggregator returns success
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success(
            data={"metrics": {"annual_return": 0.12}}
        )

        result = orchestrator.run(
            task_id=task_id,
            config=config,
            portfolio_id=portfolio_id,
        )

        assert result.is_success()

        # 1. Portfolio loaded (lightweight - no component binding)
        mock_portfolio_service.get.assert_called_once_with(portfolio_id=portfolio_id)

        # 2. Components loaded via task_helpers
        mock_load_components.assert_called_once_with(portfolio_id)

        # 3. Engine assembled
        mock_assembly_service.assemble_backtest_engine.assert_called_once()
        call_kwargs = mock_assembly_service.assemble_backtest_engine.call_args.kwargs
        assert call_kwargs["engine_id"] == task_id
        assert portfolio_id in call_kwargs["portfolio_configs"]

        # 4. Engine started
        engine.start.assert_called_once()

        # 5. Analyzers notified
        engine.notify_analyzers_backtest_end.assert_called_once()

        # 6. Results aggregated
        mock_aggregator.aggregate_and_save.assert_called_once()
        agg_kwargs = mock_aggregator.aggregate_and_save.call_args.kwargs
        assert agg_kwargs["task_id"] == task_id
        assert agg_kwargs["portfolio_id"] == portfolio_id

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_run_passes_progress_callback_to_assembly(
        self,
        mock_load_components,
        orchestrator,
        mock_assembly_service,
        mock_portfolio_service,
        mock_aggregator,
    ):
        config = _make_config()
        portfolio_id = "portfolio-001"
        task_id = "task-001"
        engine = _make_engine_mock()

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True,
            data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True,
            data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        progress_callback = MagicMock()
        result = orchestrator.run(
            task_id=task_id,
            config=config,
            portfolio_id=portfolio_id,
            progress_callback=progress_callback,
        )

        assert result.is_success()
        call_kwargs = mock_assembly_service.assemble_backtest_engine.call_args.kwargs
        assert call_kwargs["progress_callback"] is progress_callback


class TestOrchestratorPortfolioLoading:
    """Verify portfolio loading is lightweight - no component binding."""

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_uses_get_not_load(self, mock_load_components, orchestrator,
                                mock_portfolio_service,
                                mock_assembly_service, mock_aggregator):
        """Should call get() not load_portfolio_with_components()."""
        config = _make_config()
        engine = _make_engine_mock()

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        orchestrator.run(task_id="t", config=config, portfolio_id="p")

        # Must NOT call the heavyweight method
        mock_portfolio_service.load_portfolio_with_components.assert_not_called()
        # Must call the lightweight method
        mock_portfolio_service.get.assert_called_once()


class TestOrchestratorErrorHandling:
    """Verify error cases are handled properly."""

    def test_portfolio_not_found(self, orchestrator, mock_portfolio_service):
        config = _make_config()
        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: False, data=None,
        )

        result = orchestrator.run(task_id="t", config=config, portfolio_id="missing")
        assert result.is_success() is False
        assert "not found" in result.error

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_assembly_failure(self, mock_load_components, orchestrator,
                               mock_portfolio_service,
                               mock_assembly_service):
        config = _make_config()
        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=False, error="No strategy found",
        )

        result = orchestrator.run(task_id="t", config=config, portfolio_id="p")
        assert result.is_success() is False
        assert "assembly failed" in result.error

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_engine_timeout_stops_engine(self, mock_load_components, orchestrator,
                                          mock_portfolio_service,
                                          mock_assembly_service, mock_aggregator):
        config = _make_config()
        engine = _make_engine_mock()
        main_thread = MagicMock()
        main_thread.is_alive.side_effect = [True, True, False]
        engine._main_thread = main_thread

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        result = orchestrator.run(task_id="t", config=config, portfolio_id="p",
                                   timeout=0.01)
        # Should have called stop on timeout
        engine.stop.assert_called()


class TestOrchestratorTimeoutReporting:
    """#6483: 引擎超时不应静默标 completed，应如实报告为 incomplete。

    背景：3600s 挂钟超时被 _aggregate_results 硬编码 status="completed" 吞掉，
    导致 ~600 行截断的回测显示"已完成"。验收：超时分支写非 completed 状态、
    附 error_message、backtest_end_date 取引擎实际跑到的时间（非配置 end_date）。
    """

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_timeout_marks_status_incomplete_not_completed(
        self, mock_load_components, orchestrator,
        mock_portfolio_service, mock_assembly_service, mock_aggregator):
        """超时分支调 aggregator 时 status 必须不是 'completed'。"""
        import datetime as _dt
        config = _make_config()
        engine = _make_engine_mock()
        # join 超时（仍 alive），engine.stop() 后再 join 死亡
        main_thread = MagicMock()
        main_thread.is_alive.side_effect = [True, True, False]
        engine._main_thread = main_thread
        # 引擎实际跑到的时间点（远早于 config.end_date 2025-12-31）
        engine.now = _dt.datetime(2023, 10, 5)

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        orchestrator.run(task_id="t", config=config, portfolio_id="p", timeout=0.01)

        agg_kwargs = mock_aggregator.aggregate_and_save.call_args.kwargs
        assert agg_kwargs["status"] != "completed", (
            "超时不应静默标 completed（#6483）：实际 status="
            f"{agg_kwargs.get('status')!r}"
        )

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_timeout_end_date_uses_engine_now_not_config(
        self, mock_load_components, orchestrator,
        mock_portfolio_service, mock_assembly_service, mock_aggregator):
        """超时时 backtest_end_date 应取引擎实际跑到的时间，而非配置 end_date。

        #6483 诊断价值：让用户看到"跑到 2023-10"而非谎报配置的 2025-12-31。
        """
        import datetime as _dt
        config = _make_config()  # end_date = "2025-12-31"
        engine = _make_engine_mock()
        main_thread = MagicMock()
        main_thread.is_alive.side_effect = [True, True, False]
        engine._main_thread = main_thread
        engine_now = _dt.datetime(2023, 10, 5)
        engine.now = engine_now  # 引擎实际只跑到 2023-10

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        orchestrator.run(task_id="t", config=config, portfolio_id="p", timeout=0.01)

        agg_kwargs = mock_aggregator.aggregate_and_save.call_args.kwargs
        assert agg_kwargs["backtest_end_date"] == engine_now, (
            "超时 end_date 应反映引擎实际跑到的时间（#6483 诊断价值）："
            f"期望 {engine_now}，实际 {agg_kwargs.get('backtest_end_date')}"
        )

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_timeout_run_returns_failure_so_processor_can_raise(
        self, mock_load_components, orchestrator,
        mock_portfolio_service, mock_assembly_service, mock_aggregator):
        """超时时 run() 应返回 success=False + timeout error。

        #6483: task_processor.run L107 `if not result.is_success(): raise` 据此自动
        标 FAILED，task_processor 主流程零改动。
        """
        config = _make_config()
        engine = _make_engine_mock()
        main_thread = MagicMock()
        main_thread.is_alive.side_effect = [True, True, False]
        engine._main_thread = main_thread

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        result = orchestrator.run(task_id="t", config=config, portfolio_id="p", timeout=0.01)

        assert not result.is_success(), (
            "超时应返回 success=False（#6483），让 task_processor L107 自动 raise"
        )
        assert result.error and "timed out" in result.error.lower(), (
            f"error 应含 'timed out' 描述，实际: {result.error!r}"
        )


# ===========================================================================
# #6449: BacktestUseCase Protocol — 应用用例层契约
# ===========================================================================


class TestUseCaseProtocol:
    """#6449: BacktestOrchestrator 即隐式 UseCase。

    ADR-022 引入 BacktestUseCase Protocol（structural typing），让 CLI/API/worker
    通过统一的应用层入口编排回测，而非各自重复 config 解析/preflight/状态机。
    验收：BacktestOrchestrator 实例满足 BacktestUseCase 结构契约。
    """

    def test_orchestrator_satisfies_usecase_protocol(self, orchestrator):
        """BacktestOrchestrator 应当是 BacktestUseCase（duck typing 通过）。"""
        from ginkgo.trading.services.backtest_orchestrator import BacktestUseCase

        assert isinstance(orchestrator, BacktestUseCase), (
            "BacktestOrchestrator 必须满足 BacktestUseCase Protocol（#6449）："
            "缺少 run_from_task 方法"
        )


# ===========================================================================
# #6449: run_from_task — config 解析下沉（dict snapshot → BacktestConfig）
# ===========================================================================


class TestRunFromTaskConfigParse:
    """#6449: run_from_task 应把 task.config_snapshot（dict/JSON）解析为 BacktestConfig。

    收敛点：CLI/worker 不再各自构造 BacktestConfig，由 UseCase 层统一解析。
    """

    @patch("ginkgo.trading.services.backtest_orchestrator.preflight_data_coverage")
    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_dict_snapshot_converted_to_backtest_config(
        self, mock_load_components, mock_preflight, orchestrator,
        mock_assembly_service, mock_portfolio_service, mock_aggregator):
        """传 dict config_snapshot 时，应转 BacktestConfig 传给 run()。"""
        from ginkgo.workers.backtest_worker.models import BacktestConfig

        task = MagicMock()
        task.uuid = "task-x"
        task.portfolio_id = "port-x"
        snapshot = {
            "start_date": "2024-01-01", "end_date": "2024-06-30",
            "initial_cash": 500000, "frequency": "DAY",
        }
        task.config_snapshot = snapshot

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        # #6449 review: 隔离 preflight，避免查真实 MySQL（portfolio "port-x" 不存在
        # → selector 空 → 偶然命中"动态 selector 放行"分支，无 DB 的 CI 会红）。
        mock_preflight.return_value = {"ok": True, "sparse": [], "codes": []}
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=_make_engine_mock(),
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        # spy run() 捕获实际传入的 config
        captured = {}
        original_run = orchestrator.run

        def spy_run(task_id, config, portfolio_id, **kw):
            captured["config"] = config
            return original_run(task_id, config, portfolio_id, **kw)

        orchestrator.run = spy_run

        orchestrator.run_from_task(task, config_snapshot=snapshot)

        cfg = captured.get("config")
        assert isinstance(cfg, BacktestConfig), (
            "run_from_task 应把 dict snapshot 转 BacktestConfig（#6449）："
            f"实际类型 {type(cfg).__name__}"
        )
        assert cfg.start_date == "2024-01-01"
        assert cfg.initial_cash == 500000


# ===========================================================================
# #6449: run_from_task — 标 running 状态机下沉
# ===========================================================================


class TestRunFromTaskMarksRunning:
    """#6449: run_from_task 应在委派 run() 前自动标 task 为 running。

    收敛点：状态机更新（running）成为用例契约，调用方不必手动管理。
    """

    @patch("ginkgo.trading.services.backtest_orchestrator.preflight_data_coverage")
    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_marks_running_before_run(
        self, mock_load_components, mock_preflight, orchestrator,
        mock_assembly_service, mock_portfolio_service,
        mock_aggregator, mock_task_service):
        """run_from_task 应调 task_service.update_status(task.uuid, 'running')。"""
        task = MagicMock()
        task.uuid = "task-r"
        task.portfolio_id = "port-r"
        task.config_snapshot = {}

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        # #6449 review: 隔离 preflight，避免查真实 MySQL（同 test_dict_snapshot_*）。
        mock_preflight.return_value = {"ok": True, "sparse": [], "codes": []}
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=_make_engine_mock(),
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        orchestrator.run_from_task(task)

        # task_service 是 orchestrator 的 _task_service
        status_calls = mock_task_service.update_status.call_args_list
        called_running = any(
            c.args == ("task-r", "running") or c.kwargs == {"task_id": "task-r", "status": "running"}
            for c in status_calls
        )
        assert called_running, (
            "run_from_task 应标 running（#6449）："
            f"实际 update_status 调用 {status_calls}"
        )


# ===========================================================================
# #6449: run_from_task — 成功路径回填 backtest_end_date（CLI FINALIZING 进度用）
# ===========================================================================


class TestRunFromTaskExposesEndDate:
    """#6449: run_from_task 成功时应把 backtest_end_date 放入 result.data。

    收敛点：aggregator 只把 backtest_end_date 写进 DB task 表、不进返回 dict；
    config 解析下沉到 UseCase 层后 CLI 拿不到 config.end_date。用例层需在
    result.data 回填该键，否则 CLI 成功路径的 FINALIZING current_date 恒空。
    """

    @patch("ginkgo.trading.services.backtest_orchestrator.preflight_data_coverage")
    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_success_exposes_backtest_end_date(
        self, mock_load_components, mock_preflight, orchestrator,
        mock_assembly_service, mock_portfolio_service, mock_aggregator):
        """run_from_task 成功时 result.data 应含 backtest_end_date（对齐 config.end_date）。"""
        mock_preflight.return_value = {"ok": True, "sparse": [], "codes": []}

        task = MagicMock()
        task.uuid = "task-end"
        task.portfolio_id = "port-end"
        task.config_snapshot = {
            "start_date": "2024-01-01", "end_date": "2024-06-30",
            "initial_cash": 500000, "frequency": "DAY",
        }

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=_make_engine_mock(),
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        result = orchestrator.run_from_task(task)

        assert result.is_success(), f"应成功，实际 error: {result.error}"
        assert result.data.get("backtest_end_date") == "2024-06-30", (
            "run_from_task 应在 result.data 回填 backtest_end_date（#6449）："
            f"实际 {result.data.get('backtest_end_date')!r}"
        )


# ===========================================================================
# #6449: run_from_task — preflight 数据预检下沉（不抛 typer.Exit）
# ===========================================================================


class TestRunFromTaskPreflight:
    """#6449: preflight 数据预检由 UseCase 层做，业务层不抛框架异常。

    收敛点：CLI 的 preflight 阻断语义（raise typer.Exit）下沉为业务事实
    （success=False + 原因），CLI 翻译层负责转框架异常。
    """

    @patch("ginkgo.trading.services.backtest_orchestrator.preflight_data_coverage")
    def test_preflight_fail_returns_failure_not_raises(
        self, mock_preflight, orchestrator, mock_task_service):
        """preflight 报数据缺失时，run_from_task 应返回失败结果，不抛异常。"""
        # 构造一个会生成 warning 的 preflight 报告（数据稀疏）
        # 字段名必须匹配 build_preflight_warning 的真实契约：sparse/coverage/ok
        mock_preflight.return_value = {
            "codes": ["000001.SZ", "000002.SZ"],
            "coverage": {"000001.SZ": 2, "000002.SZ": 0},
            "sparse": ["000001.SZ", "000002.SZ"],
            "ok": False,
        }

        task = MagicMock()
        task.uuid = "task-pf"
        task.portfolio_id = "port-pf"
        task.config_snapshot = {"start_date": "2024-01-01", "end_date": "2024-06-30"}

        # 关键：调用不应抛任何异常（特别不能抛 typer.Exit）
        result = orchestrator.run_from_task(task)

        # 必须是失败结果（而非静默成功）
        assert not result.is_success(), (
            "preflight 失败应返回 success=False（#6449）"
        )
        assert "preflight" in result.error.lower(), (
            f"error 应含 preflight 描述，实际: {result.error!r}"
        )
        # 应标 failed（保留原 CLI 语义）
        status_calls = mock_task_service.update_status.call_args_list
        called_failed = any(c.args == ("task-pf", "failed") for c in status_calls)
        assert called_failed, (
            f"preflight 阻断应标 failed（#6449 保留原 CLI 语义）：实际 {status_calls}"
        )


class TestOrchestratorTimeoutConfig:
    """#6483: 超时阈值应可通过 GINKGO_BACKTEST_TIMEOUT 环境变量配置（覆盖默认 3600s）。"""

    @patch("ginkgo.trading.services.backtest_orchestrator.load_portfolio_components")
    def test_env_var_overrides_default_timeout(
        self, mock_load_components, orchestrator,
        mock_portfolio_service, mock_assembly_service,
        mock_aggregator, monkeypatch):
        """不显式传 timeout 时，GINKGO_BACKTEST_TIMEOUT 环境变量生效。"""
        monkeypatch.setenv("GINKGO_BACKTEST_TIMEOUT", "42")
        config = _make_config()
        engine = _make_engine_mock()

        mock_portfolio_service.get.return_value = MagicMock(
            is_success=lambda: True, data=[_make_portfolio_result()],
        )
        mock_load_components.return_value = _make_components()
        mock_assembly_service.assemble_backtest_engine.return_value = MagicMock(
            success=True, data=engine,
        )
        from ginkgo.data.services.base_service import ServiceResult
        mock_aggregator.aggregate_and_save.return_value = ServiceResult.success()

        # spy _wait_for_engine 捕获实际传入的 timeout
        captured = {}
        original_wait = orchestrator._wait_for_engine

        def spy_wait(engine_arg, t):
            captured["timeout"] = t
            return original_wait(engine_arg, t)

        orchestrator._wait_for_engine = spy_wait

        orchestrator.run(task_id="t", config=config, portfolio_id="p")  # 不传 timeout

        assert captured.get("timeout") == 42.0, (
            "GINKGO_BACKTEST_TIMEOUT 应覆盖默认 timeout："
            f"实际 _wait_for_engine 收到 {captured.get('timeout')}"
        )
