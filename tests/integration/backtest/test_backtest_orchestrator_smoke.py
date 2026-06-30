"""
BacktestOrchestrator smoke test.

Runs the orchestrator against real services to verify:
1. Import chain is intact (no missing imports)
2. Data formats match across service boundaries
3. Engine assembles, starts, and completes
4. Results aggregate and save correctly

This is NOT a unit test — it hits real databases.
Run: pytest tests/integration/backtest/test_backtest_orchestrator_smoke.py -v -s

Prerequisites:
- Debug mode on: ginkgo system config set --debug on
- Database initialized: ginkgo data init
- At least one portfolio with components bound (auto-created if missing)
"""

import pytest
import time

from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES
from ginkgo.libs import GCONF, GLOG


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def ensure_debug():
    GCONF.set_debug(True)


@pytest.fixture(scope="module")
def portfolio_with_components():
    """Create a portfolio with full component set, yield UUID, cleanup after."""
    portfolio_svc = container.portfolio_service()
    file_svc = container.file_service()

    # Find existing component files by name
    def _find_file(name, file_type):
        result = file_svc.get(name=name, file_type=file_type)
        if result.is_success() and result.data:
            files = result.data.get("files", [])
            for f in files:
                if getattr(f, 'name', '') == name:
                    return f.uuid, f.name
        return None, None

    strategy_id, strategy_name = _find_file("random_signal_strategy", FILE_TYPES.STRATEGY)
    selector_id, selector_name = _find_file("fixed_selector", FILE_TYPES.SELECTOR)
    sizer_id, sizer_name = _find_file("fixed_sizer", FILE_TYPES.SIZER)
    risk_id, risk_name = _find_file("no_risk", FILE_TYPES.RISKMANAGER)

    assert strategy_id, "Strategy 'random_signal_strategy' not found in DB"
    assert selector_id, "Selector 'fixed_selector' not found in DB"
    assert sizer_id, "Sizer 'fixed_sizer' not found in DB"
    assert risk_id, "Risk 'no_risk' not found in DB"

    # Create portfolio with unique name
    ts = int(time.time())
    result = portfolio_svc.add(
        name=f"smoke_orch_{ts}",
        initial_capital=100000.0,
        mode="BACKTEST",
    )
    assert result.is_success(), f"Portfolio creation failed: {result.error}"
    portfolio_id = result.data["uuid"]

    # Bind components
    mapping_svc = container.mapping_service()
    for file_id, file_name, comp_type in [
        (strategy_id, strategy_name, FILE_TYPES.STRATEGY),
        (selector_id, selector_name, FILE_TYPES.SELECTOR),
        (sizer_id, sizer_name, FILE_TYPES.SIZER),
        (risk_id, risk_name, FILE_TYPES.RISKMANAGER),
    ]:
        bind_result = mapping_svc.create_portfolio_file_binding(
            portfolio_uuid=portfolio_id,
            file_uuid=file_id,
            file_name=file_name,
            file_type=comp_type,
        )
        assert bind_result.is_success(), f"Binding {comp_type} failed: {bind_result.error}"

    GLOG.INFO(f"[SMOKE] Portfolio ready: {portfolio_id}")
    yield portfolio_id

    # Cleanup
    try:
        portfolio_svc.delete(portfolio_id=portfolio_id)
        GLOG.INFO(f"[SMOKE] Cleaned up portfolio {portfolio_id}")
    except Exception as e:
        GLOG.WARN(f"[SMOKE] Cleanup warning: {e}")


# ===========================================================================
# Smoke tests
# ===========================================================================


class TestOrchestratorSmoke:
    """End-to-end smoke tests for BacktestOrchestrator."""

    def test_import_chain(self):
        """Verify all imports resolve without error."""
        from ginkgo.trading.services.backtest_orchestrator import BacktestOrchestrator
        from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator
        from ginkgo.workers.backtest_worker.task_helpers import (
            load_portfolio_components,
            build_engine_data,
            build_portfolio_config,
        )

        assert BacktestOrchestrator is not None
        assert BacktestResultAggregator is not None
        assert load_portfolio_components is not None

    def test_component_loading_format(self, portfolio_with_components):
        """Verify load_portfolio_components returns categorized dict, not flat list."""
        from ginkgo.workers.backtest_worker.task_helpers import load_portfolio_components

        components = load_portfolio_components(portfolio_with_components)

        # Must be a dict with category keys
        assert isinstance(components, dict)
        for key in ("strategies", "selectors", "sizers", "risk_managers"):
            assert key in components, f"Missing key '{key}' in components"
            assert isinstance(components[key], list), f"components['{key}'] must be a list"

        # Our portfolio should have at least a strategy
        assert len(components["strategies"]) > 0, "No strategies loaded"
        GLOG.INFO(f"[SMOKE] Components: {', '.join(f'{k}={len(v)}' for k, v in components.items())}")

    def test_portfolio_metadata_loading(self, portfolio_with_components):
        """Verify portfolio_service.get() returns usable metadata."""
        portfolio_svc = container.portfolio_service()
        result = portfolio_svc.get(portfolio_id=portfolio_with_components)

        assert result.is_success(), f"get() failed: {result.error}"
        assert result.data, "get() returned empty data"

        data = result.data[0] if isinstance(result.data, list) else result.data
        assert hasattr(data, 'uuid') or 'uuid' in str(type(data))
        GLOG.INFO(f"[SMOKE] Portfolio metadata loaded: {getattr(data, 'name', '?')}")

    def test_full_orchestrator_run(self, portfolio_with_components):
        """Run a minimal backtest through the orchestrator end-to-end."""
        from ginkgo.trading.services.backtest_orchestrator import BacktestOrchestrator
        from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator
        from ginkgo.workers.backtest_worker.models import BacktestConfig

        portfolio_id = portfolio_with_components
        task_id = f"smoke-test-{portfolio_id[:8]}"

        config = BacktestConfig(
            start_date="2025-05-01",
            end_date="2025-05-15",
            initial_cash=100000,
            commission_rate=0.0003,
            slippage_rate=0.0001,
            benchmark_return=0.0,
            max_position_ratio=0.3,
            stop_loss_ratio=0.05,
            take_profit_ratio=0.15,
            frequency="DAY",
            analyzers=[],
        )

        backtest_task_svc = container.backtest_task_service()
        aggregator = BacktestResultAggregator(
            analyzer_service=container.analyzer_service(),
            backtest_task_service=backtest_task_svc,
        )

        from ginkgo import services
        orchestrator = BacktestOrchestrator(
            assembly_service=services.trading.services.engine_assembly_service(),
            portfolio_service=container.portfolio_service(),
            task_service=backtest_task_svc,
            result_aggregator=aggregator,
        )

        result = orchestrator.run(
            task_id=task_id,
            config=config,
            portfolio_id=portfolio_id,
            timeout=120.0,
        )

        assert result.is_success(), f"Orchestrator run failed: {result.error}"
        GLOG.INFO(f"[SMOKE] Orchestrator completed: {result.data}")
