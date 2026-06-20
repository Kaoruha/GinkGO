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
