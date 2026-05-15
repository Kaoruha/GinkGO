"""
SignalService smoke test.

Verifies the core business methods of SignalService against real database:
- delete_signals_by_portfolio
- delete_signals_by_portfolio_and_date_range

Run: pytest tests/integration/data/services/test_signal_service.py -v -s
"""

import pytest

from ginkgo.data.containers import container
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GCONF


@pytest.fixture(scope="module", autouse=True)
def ensure_debug():
    GCONF.set_debug(True)


@pytest.fixture(scope="module")
def signal_service():
    return container.signal_service()


@pytest.fixture(scope="module")
def sample_signal_data(signal_service):
    """Create a test signal, yield (portfolio_id, task_id), cleanup after."""
    signal_crud = container.cruds.signal()
    portfolio_id = "SMOKE_TEST_SIGNAL_SVC"
    task_id = "smoke-task-signal-svc"

    # Insert a test signal via CRUD
    signal_crud.create(
        portfolio_id=portfolio_id,
        engine_id="smoke-engine",
        task_id=task_id,
        code="000001.SZ",
        direction=1,
        reason="smoke test",
        source=SOURCE_TYPES.TEST.value,
        timestamp="2025-05-01",
    )

    yield portfolio_id, task_id

    # Cleanup
    try:
        signal_crud.remove(filters={"portfolio_id": portfolio_id})
    except Exception:
        pass


class TestSignalServiceSmoke:
    """Core business methods of SignalService."""

    def test_delete_signals_by_portfolio(self, signal_service, sample_signal_data):
        portfolio_id, task_id = sample_signal_data

        # Verify signal exists
        signal_crud = container.cruds.signal()
        found = signal_crud.find(filters={"portfolio_id": portfolio_id})
        assert len(found) > 0

        # Delete via service
        result = signal_service.delete_signals_by_portfolio(portfolio_id)
        assert result.is_success()

        # Verify deleted
        found = signal_crud.find(filters={"portfolio_id": portfolio_id})
        assert len(found) == 0

    def test_delete_by_portfolio_rejects_empty_id(self, signal_service):
        result = signal_service.delete_signals_by_portfolio("")
        assert not result.is_success()

    def test_delete_by_date_range(self, signal_service):
        """Insert two signals, delete only one by date range."""
        signal_crud = container.cruds.signal()
        portfolio_id = "SMOKE_TEST_DATE_RANGE"
        from datetime import datetime

        # Two signals with different dates
        signal_crud.create(
            portfolio_id=portfolio_id, engine_id="e", task_id="t",
            code="000001.SZ", direction=1, reason="old",
            source=SOURCE_TYPES.TEST.value,
            timestamp=datetime(2025, 1, 1),
        )
        signal_crud.create(
            portfolio_id=portfolio_id, engine_id="e", task_id="t",
            code="000002.SZ", direction=2, reason="new",
            source=SOURCE_TYPES.TEST.value,
            timestamp=datetime(2025, 6, 1),
        )

        # Delete only signals before 2025-03-01
        result = signal_service.delete_signals_by_portfolio_and_date_range(
            portfolio_id=portfolio_id,
            start_date="2025-01-01",
            end_date="2025-03-01",
        )
        assert result.is_success()

        # Only the newer signal should remain
        remaining = signal_crud.find(filters={"portfolio_id": portfolio_id})
        assert len(remaining) == 1
        assert remaining[0].code == "000002.SZ"

        # Cleanup
        signal_crud.remove(filters={"portfolio_id": portfolio_id})
