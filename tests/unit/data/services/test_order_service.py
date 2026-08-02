"""
OrderService unit tests.

Covers #18: 补全订单业务服务实现

Run: pytest tests/unit/data/services/test_order_service.py -v -o "addopts="
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.data.services.order_service import OrderService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ORDERSTATUS_TYPES


@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def order_svc(mock_crud):
    return OrderService(crud_repo=mock_crud)


class TestGetOrdersByStatus:
    """See #18: get_orders_by_status 从空壳改为真实实现"""

    def test_returns_orders_matching_statuses(self, order_svc, mock_crud):
        order1 = MagicMock(status=ORDERSTATUS_TYPES.SUBMITTED)
        order2 = MagicMock(status=ORDERSTATUS_TYPES.PARTIAL_FILLED)
        mock_crud.find.side_effect = [[order1], [order2]]

        result = order_svc.get_orders_by_status(
            [ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.PARTIAL_FILLED]
        )

        assert result.is_success()
        assert len(result.data) == 2

    def test_returns_empty_when_no_matches(self, order_svc, mock_crud):
        mock_crud.find.return_value = []

        result = order_svc.get_orders_by_status([ORDERSTATUS_TYPES.FILLED])

        assert result.is_success()
        assert result.data == []

    def test_rejects_empty_status_list(self, order_svc):
        result = order_svc.get_orders_by_status([])

        assert result.is_failure()

    def test_queries_per_status_and_merges(self, order_svc, mock_crud):
        """When status list has multiple values, query each and merge."""
        a = MagicMock()
        b = MagicMock()
        mock_crud.find.side_effect = [[a], [b]]

        result = order_svc.get_orders_by_status(
            [ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.PARTIAL_FILLED]
        )

        assert mock_crud.find.call_count == 2
        assert len(result.data) == 2


class TestGetOrdersByPortfolio:
    """See #18: 按组合查询订单"""

    def test_returns_orders(self, order_svc, mock_crud):
        mock_crud.find_by_portfolio.return_value = [MagicMock()]

        result = order_svc.get_orders_by_portfolio("portfolio-123")

        assert result.is_success()
        assert len(result.data) == 1
        mock_crud.find_by_portfolio.assert_called_once_with(portfolio_id="portfolio-123")

    def test_passes_optional_filters(self, order_svc, mock_crud):
        mock_crud.find_by_portfolio.return_value = []

        order_svc.get_orders_by_portfolio(
            "p1", status=ORDERSTATUS_TYPES.FILLED, page=0, page_size=20
        )

        mock_crud.find_by_portfolio.assert_called_once_with(
            portfolio_id="p1", status=ORDERSTATUS_TYPES.FILLED, page=0, page_size=20
        )

    def test_passes_date_range_to_crud(self, order_svc, mock_crud):
        """start_date/end_date 透传到 crud.find_by_portfolio (#6030)"""
        mock_crud.find_by_portfolio.return_value = []

        order_svc.get_orders_by_portfolio(
            "p1", start_date="2026-06-23", end_date="2026-06-24"
        )

        mock_crud.find_by_portfolio.assert_called_once_with(
            portfolio_id="p1", start_date="2026-06-23", end_date="2026-06-24"
        )

    def test_date_omitted_when_not_passed(self, order_svc, mock_crud):
        """未传 date 时不进 kwargs（仿 status 模式，#6030）"""
        mock_crud.find_by_portfolio.return_value = []

        order_svc.get_orders_by_portfolio("p1")

        _, kwargs = mock_crud.find_by_portfolio.call_args
        assert "start_date" not in kwargs
        assert "end_date" not in kwargs

    def test_rejects_empty_portfolio_id(self, order_svc):
        result = order_svc.get_orders_by_portfolio("")

        assert result.is_failure()


class TestUpdateOrder:
    """See #18: update_order 从空壳改为真实实现"""

    def test_updates_existing_order(self, order_svc, mock_crud):
        order = MagicMock()
        order.uuid = "order-123"
        order.status = ORDERSTATUS_TYPES.FILLED
        mock_crud.modify.return_value = None

        result = order_svc.update_order(order)

        assert result.is_success()
        mock_crud.modify.assert_called_once()

    def test_rejects_order_without_uuid(self, order_svc):
        order = MagicMock()
        order.uuid = None

        result = order_svc.update_order(order)

        assert result.is_failure()


class TestUpsertOrder:
    """ADR-029 Task 7：upsert_order seam（暂不被调，为 Task 8 实盘订单持久化铺路）。

    存在判断：order_crud.get_by_uuid。
      - 存在 → 复用 update_order（modify 语义，仅更可变字段）
      - 不存在 → OrderMapper.entity_to_model → order_crud.add
    """

    def test_insert_when_not_exists(self, order_svc, mock_crud):
        """uuid 不存在 → mapper.entity_to_model → crud.add（insert 分支）。"""
        from ginkgo.entities import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        mock_crud.get_by_uuid.return_value = None
        mock_crud.add.return_value = None

        order = Order(
            portfolio_id="p1", engine_id="e1", task_id="t1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100, limit_price=10.0,
        )

        result = order_svc.upsert_order(order)

        assert result.is_success()
        assert result.data["action"] == "insert"
        mock_crud.get_by_uuid.assert_called_once_with(order.uuid)
        mock_crud.add.assert_called_once()
        # add 收到的是 MOrder（经 OrderMapper.entity_to_model）
        added = mock_crud.add.call_args[0][0]
        from ginkgo.data.models import MOrder
        assert isinstance(added, MOrder)
        assert added.code == "000001.SZ"

    def test_update_when_exists(self, order_svc, mock_crud):
        """uuid 存在 → 走 update_order（modify 分支，不调 add）。"""
        from ginkgo.entities import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        existing = MagicMock()
        existing.uuid = "existing-uuid"
        mock_crud.get_by_uuid.return_value = existing
        mock_crud.modify.return_value = None

        order = Order(
            portfolio_id="p1", engine_id="e1", task_id="t1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.FILLED,
            volume=100, limit_price=10.0,
            uuid="existing-uuid",
        )

        result = order_svc.upsert_order(order)

        assert result.is_success()
        assert result.data["action"] == "update"
        mock_crud.get_by_uuid.assert_called_once_with("existing-uuid")
        mock_crud.add.assert_not_called()
        mock_crud.modify.assert_called_once()

    def test_rejects_order_without_uuid(self, order_svc):
        # Order Entity 构造时 uuid="" 会自动生成（Base.__init__）；用 MagicMock
        # 模拟无 uuid 的订单对象，覆盖守卫分支。
        order = MagicMock()
        order.uuid = None

        result = order_svc.upsert_order(order)
        assert result.is_failure()


class TestGetOrderSummary:
    """See #18: 订单统计分析，从 CRUD 查询后计算指标"""

    def test_returns_summary_with_counts(self, order_svc, mock_crud):
        filled = MagicMock()
        filled.volume = 100
        filled.transaction_price = 10.0
        filled.fee = 5.0
        mock_crud.find_by_portfolio.return_value = [filled]
        mock_crud.count_by_portfolio.return_value = 1

        result = order_svc.get_order_summary("portfolio-123")

        assert result.is_success()
        data = result.data
        assert "total_orders" in data
        assert "total_volume" in data
        assert "total_fee" in data

    def test_rejects_empty_portfolio_id(self, order_svc):
        result = order_svc.get_order_summary("")

        assert result.is_failure()


class TestDeleteOrdersByPortfolio:
    """See #18: 删除组合的所有订单"""

    def test_deletes_orders(self, order_svc, mock_crud):
        result = order_svc.delete_orders_by_portfolio("portfolio-123")

        assert result.is_success()
        mock_crud.delete_by_portfolio.assert_called_once_with("portfolio-123")


class TestUpsertOrderStatusOverride:
    """ADR-029 Task 8：upsert_order ``status_override``（回测 4 态接线）。

    回测事件链中 order.status 是事件前状态（NEW/SUBMITTED），MOrder 须写事件后状态。
    - insert 分支：mapper 后 model.status 用 effective_status
    - update 分支：updates['status'] 用 effective_status（不走 update_order 因硬读 order.status）
    - None 回退 order.status（向后兼容 Task 7）
    """

    def _make_order(self, status=None, uuid=None):
        from ginkgo.entities import Order
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        return Order(
            portfolio_id="p1", engine_id="e1", task_id="t1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=status or ORDERSTATUS_TYPES.NEW,
            volume=100, limit_price=10.0,
            uuid=uuid or "",
        )

    def test_insert_with_status_override(self, order_svc, mock_crud):
        """insert 分支：status_override 写入 model.status（非 order.status）。"""
        from ginkgo.enums import ORDERSTATUS_TYPES

        mock_crud.get_by_uuid.return_value = None
        mock_crud.add.return_value = None

        order = self._make_order(status=ORDERSTATUS_TYPES.NEW)

        result = order_svc.upsert_order(
            order, status_override=ORDERSTATUS_TYPES.FILLED
        )

        assert result.is_success()
        assert result.data["action"] == "insert"
        added = mock_crud.add.call_args[0][0]
        # status_override 写入 model.status（非 order.status=NEW）
        assert added.status == ORDERSTATUS_TYPES.FILLED

    def test_update_with_status_override(self, order_svc, mock_crud):
        """update 分支：updates['status'] = status_override（非 order.status）。"""
        from ginkgo.enums import ORDERSTATUS_TYPES

        existing = MagicMock()
        existing.uuid = "existing-uuid"
        mock_crud.get_by_uuid.return_value = existing
        mock_crud.modify.return_value = None

        order = self._make_order(
            status=ORDERSTATUS_TYPES.NEW, uuid="existing-uuid"
        )

        result = order_svc.upsert_order(
            order, status_override=ORDERSTATUS_TYPES.REJECTED
        )

        assert result.is_success()
        assert result.data["action"] == "update"
        updates = mock_crud.modify.call_args.kwargs["updates"]
        # status_override 写入 updates（非 order.status=NEW）
        assert updates["status"] == ORDERSTATUS_TYPES.REJECTED
        mock_crud.add.assert_not_called()

    def test_none_override_falls_back_to_order_status(self, order_svc, mock_crud):
        """None override → 用 order.status（向后兼容 Task 7）。"""
        from ginkgo.enums import ORDERSTATUS_TYPES

        mock_crud.get_by_uuid.return_value = None
        mock_crud.add.return_value = None

        order = self._make_order(status=ORDERSTATUS_TYPES.NEW)

        result = order_svc.upsert_order(order, status_override=None)

        assert result.is_success()
        added = mock_crud.add.call_args[0][0]
        assert added.status == ORDERSTATUS_TYPES.NEW


class TestCreateOrderRecord:
    """ADR-029 Task 8：MOrderRecord 写入收敛到 OrderService。

    原 result_service.create_order_record:648 写逻辑迁此。
    """

    def test_calls_order_record_crud_create(self, order_svc, monkeypatch):
        """create(**kwargs) 透传给 OrderRecordCRUD.create。"""
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        # 模拟 OrderRecordCRUD 懒 import
        mock_crud_module = MagicMock()
        mock_record_crud = MagicMock()
        mock_crud_module.OrderRecordCRUD.return_value = mock_record_crud
        import sys
        monkeypatch.setitem(
            sys.modules, "ginkgo.data.crud.order_record_crud", mock_crud_module
        )

        kwargs = dict(
            order_id="order-uuid-1",
            portfolio_id="p1",
            engine_id="e1",
            task_id="t1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0,
            frozen_money=1000.0,
            frozen_volume=0,
            transaction_price=0,
            transaction_volume=0,
            remain=100,
            fee=0,
            timestamp="2024-01-01",
            business_timestamp="2024-01-01",
        )

        result = order_svc.create_order_record(**kwargs)

        assert result.is_success()
        mock_crud_module.OrderRecordCRUD.assert_called_once()
        mock_record_crud.create.assert_called_once_with(**kwargs)

    def test_returns_error_on_exception(self, order_svc, monkeypatch):
        """OrderRecordCRUD.create 抛错 → ServiceResult.error（响亮失败非静默）。"""
        from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES

        mock_crud_module = MagicMock()
        mock_record_crud = MagicMock()
        mock_record_crud.create.side_effect = RuntimeError("DB connection failed")
        mock_crud_module.OrderRecordCRUD.return_value = mock_record_crud
        import sys
        monkeypatch.setitem(
            sys.modules, "ginkgo.data.crud.order_record_crud", mock_crud_module
        )

        result = order_svc.create_order_record(
            order_id="o1", portfolio_id="p1", code="000001.SZ",
            direction=DIRECTION_TYPES.LONG, order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW, volume=100, limit_price=10.0,
        )

        assert result.is_failure()
        assert "DB connection failed" in result.message

    def test_rejects_empty_portfolio_id(self, order_svc):
        result = order_svc.delete_orders_by_portfolio("")

        assert result.is_failure()


class TestGetOrdersDfFilters:
    """get_orders_df 的 engine_id/task_id 过滤透传（#4743）

    OrderModel 与 Signal/Position 对称持有 engine_id + task_id，
    但 order 的 filter builder 仅连了 portfolio_id。此处验证三维过滤透传。
    """

    def test_filters_by_engine_and_task(self, order_svc, mock_crud):
        """engine_id + task_id 应透传到 crud.find 的 filters"""
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        order_svc.get_orders_df(
            portfolio_id="p1", engine_id="e1", task_id="t1"
        )

        _, kwargs = mock_crud.find.call_args
        filters = kwargs["filters"]
        assert filters == {
            "is_del": False,
            "portfolio_id": "p1",
            "engine_id": "e1",
            "task_id": "t1",
        }

    def test_omits_unset_filters(self, order_svc, mock_crud):
        """未传的过滤维度不应进入 filters（避免误加 None）"""
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        order_svc.get_orders_df(portfolio_id="p1")

        _, kwargs = mock_crud.find.call_args
        assert kwargs["filters"] == {"is_del": False, "portfolio_id": "p1"}
