"""
BacktestTaskService smoke test.

Verifies the core task lifecycle through real services:
create → get → update → delete

Run: pytest tests/integration/data/services/test_backtest_task_service_smoke.py -v -s
"""

import time

import pytest

from ginkgo.data.containers import container
from ginkgo.libs import GCONF


@pytest.fixture(scope="module", autouse=True)
def ensure_debug():
    GCONF.set_debug(True)


@pytest.fixture(scope="module")
def task_svc():
    return container.backtest_task_service()


@pytest.fixture(scope="module")
def sample_task(task_svc):
    """Create a backtest task, yield uuid, cleanup after."""
    ts = int(time.time())
    result = task_svc.create(
        name=f"smoke_task_{ts}",
        engine_id="smoke-engine",
        portfolio_id="smoke-portfolio",
    )
    assert result.is_success(), f"Create task failed: {result.error}"
    task_id = result.data.uuid

    yield task_id

    try:
        task_svc.delete(uuid=task_id)
    except Exception:
        pass


class TestBacktestTaskServiceSmoke:
    """Core BacktestTaskService lifecycle smoke test."""

    def test_health_check(self, task_svc):
        result = task_svc.health_check()
        assert result.is_success()
        assert result.data["status"] == "healthy"

    def test_create_and_get(self, task_svc, sample_task):
        result = task_svc.get_by_id(sample_task)
        assert result.is_success()
        assert result.data.uuid == sample_task
        assert result.data.status == "created"

    def test_list_includes_task(self, task_svc, sample_task):
        result = task_svc.list(status="created", page_size=100)
        assert result.is_success()
        uuids = [t.uuid for t in result.data["data"]]
        assert sample_task in uuids

    def test_update_name(self, task_svc, sample_task):
        result = task_svc.update(uuid=sample_task, name="renamed_smoke")
        assert result.is_success()
        assert "name" in result.data["updated_fields"]

        verify = task_svc.get_by_id(sample_task)
        assert verify.data.name == "renamed_smoke"

    def test_statistics_counts_task(self, task_svc, sample_task):
        result = task_svc.get_statistics()
        assert result.is_success()
        assert result.data["total"] > 0

    def test_delete_task(self, task_svc):
        # Create a separate task for deletion
        ts = int(time.time())
        create_result = task_svc.create(
            name=f"smoke_del_{ts}",
            engine_id="smoke-engine",
            portfolio_id="smoke-portfolio",
        )
        assert create_result.is_success()
        task_id = create_result.data.uuid

        del_result = task_svc.delete(uuid=task_id)
        assert del_result.is_success()

        exists_result = task_svc.exists(uuid=task_id)
        assert exists_result.is_success()
        assert exists_result.data["exists"] is False
