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
