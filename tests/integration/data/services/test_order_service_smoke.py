"""
OrderService smoke test.

Verifies core order service methods against real database:
get_orders_by_status, get_orders_by_portfolio, get_order_summary, delete

Run: pytest tests/integration/data/services/test_order_service_smoke.py -v -s
"""

import pytest

from ginkgo.data.containers import container
from ginkgo.enums import ORDERSTATUS_TYPES, ORDER_TYPES, DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import GCONF


@pytest.fixture(scope="module", autouse=True)
def ensure_debug():
    GCONF.set_debug(True)


@pytest.fixture(scope="module")
def order_svc():
    return container.order_service()


@pytest.fixture(scope="module")
def sample_orders(order_svc):
    """Create test orders, yield portfolio_id, cleanup after."""
    order_crud = container.cruds.order()
    portfolio_id = "SMOKE_TEST_ORDER_SVC"

    for i, status in enumerate([ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.FILLED]):
        order_crud.create(
            portfolio_id=portfolio_id,
            engine_id="smoke-engine",
            task_id="smoke-task",
            code=f"00000{i+1}.SZ",
            direction=DIRECTION_TYPES.LONG if i == 0 else DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.MARKETORDER,
            status=status,
            volume=100 * (i + 1),
            limit_price=10.0,
            frozen=0.0,
            transaction_price=10.0,
            transaction_volume=100 if status == ORDERSTATUS_TYPES.FILLED else 0,
            remain=0.0,
            fee=5.0,
            source=SOURCE_TYPES.TEST.value,
            timestamp="2025-05-01",
            business_timestamp=None,
        )

    yield portfolio_id

    try:
        order_crud.remove(filters={"portfolio_id": portfolio_id})
    except Exception:
        pass


class TestOrderServiceSmoke:
    """Core OrderService business methods."""

    def test_get_orders_by_status(self, order_svc, sample_orders):
        result = order_svc.get_orders_by_status([ORDERSTATUS_TYPES.SUBMITTED])
        assert result.is_success()
        assert len(result.data) > 0

    def test_get_orders_by_portfolio(self, order_svc, sample_orders):
        result = order_svc.get_orders_by_portfolio(sample_orders)
        assert result.is_success()
        assert len(result.data) == 2

    def test_get_order_summary(self, order_svc, sample_orders):
        result = order_svc.get_order_summary(sample_orders)
        assert result.is_success()
        assert result.data["total_orders"] >= 2

    def test_delete_orders_by_portfolio(self, order_svc):
        order_crud = container.cruds.order()
        portfolio_id = "SMOKE_TEST_ORDER_DEL"

        order_crud.create(
            portfolio_id=portfolio_id, engine_id="e", task_id="t",
            code="000001.SZ", direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED, volume=100,
            limit_price=10.0, frozen=0.0,
            transaction_price=0.0, transaction_volume=0,
            remain=0.0, fee=0.0,
            source=SOURCE_TYPES.TEST.value, timestamp="2025-05-01",
            business_timestamp=None,
        )

        result = order_svc.delete_orders_by_portfolio(portfolio_id)
        assert result.is_success()

        remaining = order_crud.find(filters={"portfolio_id": portfolio_id})
        assert len(remaining) == 0

    def test_rejects_empty_portfolio_id(self, order_svc):
        result = order_svc.get_orders_by_portfolio("")
        assert result.is_failure()

    def test_rejects_empty_status_list(self, order_svc):
        result = order_svc.get_orders_by_status([])
        assert result.is_failure()
