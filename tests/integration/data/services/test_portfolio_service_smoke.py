"""
PortfolioService smoke test.

Verifies the core portfolio lifecycle through real services:
create → bind components → get with details → delete

Run: pytest tests/integration/data/services/test_portfolio_service_smoke.py -v -s
"""

import time

import pytest

from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES
from ginkgo.libs import GCONF, GLOG


@pytest.fixture(scope="module", autouse=True)
def ensure_debug():
    GCONF.set_debug(True)


@pytest.fixture(scope="module")
def portfolio_with_components():
    """Create portfolio, bind components, yield UUID, cleanup."""
    portfolio_svc = container.portfolio_service()
    file_svc = container.file_service()
    mapping_svc = container.mapping_service()

    # Find component files
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
    risk_id, risk_name = _find_file("no_risk", FILE_TYPES.RISKMANAGER)

    assert strategy_id, "Strategy not found"

    # Create portfolio
    ts = int(time.time())
    result = portfolio_svc.add(
        name=f"smoke_port_{ts}",
        initial_capital=100000.0,
        mode="BACKTEST",
    )
    assert result.is_success(), f"Create failed: {result.error}"
    portfolio_id = result.data["uuid"]

    # Bind components
    for file_id, file_name, comp_type in [
        (strategy_id, strategy_name, FILE_TYPES.STRATEGY),
        (selector_id, selector_name, FILE_TYPES.SELECTOR) if selector_id else None,
        (risk_id, risk_name, FILE_TYPES.RISKMANAGER) if risk_id else None,
    ]:
        if file_id is None:
            continue
        bind_result = mapping_svc.create_portfolio_file_binding(
            portfolio_uuid=portfolio_id,
            file_uuid=file_id,
            file_name=file_name,
            file_type=comp_type,
        )
        assert bind_result.is_success(), f"Bind {comp_type} failed: {bind_result.error}"

    GLOG.INFO(f"[SMOKE] Portfolio ready: {portfolio_id}")
    yield portfolio_id

    try:
        portfolio_svc.delete(portfolio_id=portfolio_id)
    except Exception:
        pass


class TestPortfolioServiceSmoke:
    """Core portfolio lifecycle smoke test."""

    def test_create_and_get(self, portfolio_with_components):
        portfolio_svc = container.portfolio_service()
        result = portfolio_svc.get(portfolio_id=portfolio_with_components)
        assert result.is_success()
        data = result.data[0] if isinstance(result.data, list) else result.data
        assert data.uuid == portfolio_with_components

    def test_components_bound(self, portfolio_with_components):
        result = container.portfolio_service().get_components(
            portfolio_id=portfolio_with_components
        )
        assert result.is_success()
        components = result.data
        assert len(components) > 0
        types = [c.get("component_type") for c in components]
        assert "STRATEGY" in types or 6 in types or "6" in types

    def test_delete_portfolio(self, portfolio_with_components):
        portfolio_svc = container.portfolio_service()
        portfolio_id = portfolio_with_components

        # Verify exists
        result = portfolio_svc.get(portfolio_id=portfolio_id)
        assert result.is_success()

        # Delete
        del_result = portfolio_svc.delete(portfolio_id=portfolio_id)
        assert del_result.is_success()

        # Verify gone
        result = portfolio_svc.get(portfolio_id=portfolio_id)
        assert not result.is_success() or not result.data
