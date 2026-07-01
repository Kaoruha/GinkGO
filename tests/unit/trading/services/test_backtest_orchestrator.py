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
