"""
Tests for BaseService._paginated_query() (#4589).

Verifies the common pagination method extracted into BaseService
for reuse across PortfolioService, ValidationService, etc.

Issue: #4589
"""

import pytest
from unittest.mock import MagicMock

from ginkgo.data.services.base_service import BaseService, ServiceResult


class TestBaseServicePaginatedQuery:
    """BaseService._paginated_query should provide common find+count pagination."""

    def test_returns_service_result_with_items_and_total(self):
        mock_crud = MagicMock()
        mock_crud.find.return_value = [MagicMock(uuid="a"), MagicMock(uuid="b")]
        mock_crud.count.return_value = 42

        svc = BaseService(crud_repo=mock_crud)
        result = svc._paginated_query(
            filters={"name": "test"},
            page=1,
            page_size=20,
            order_by="update_at",
            desc_order=True,
        )

        assert isinstance(result, ServiceResult)
        assert result.success
        assert result.data["total"] == 42
        assert len(result.data["items"]) == 2
        mock_crud.find.assert_called_once_with(
            filters={"name": "test"},
            page=1, page_size=20,
            order_by="update_at", desc_order=True,
        )
        mock_crud.count.assert_called_once_with(filters={"name": "test"})

    def test_returns_empty_when_crud_returns_none(self):
        mock_crud = MagicMock()
        mock_crud.find.return_value = None
        mock_crud.count.return_value = 0

        svc = BaseService(crud_repo=mock_crud)
        result = svc._paginated_query()

        assert result.success
        assert result.data["items"] == []
        assert result.data["total"] == 0

    def test_returns_error_on_exception(self):
        mock_crud = MagicMock()
        mock_crud.find.side_effect = Exception("DB down")

        svc = BaseService(crud_repo=mock_crud)
        result = svc._paginated_query()

        assert not result.success
        assert "DB down" in result.error

    def test_uses_custom_crud_repo_when_provided(self):
        """crud_repo 参数允许 Service 查询非默认 CRUD 实例。"""
        default_crud = MagicMock()
        custom_crud = MagicMock()
        custom_crud.find.return_value = [MagicMock(uuid="x")]
        custom_crud.count.return_value = 1

        svc = BaseService(crud_repo=default_crud)
        result = svc._paginated_query(crud_repo=custom_crud)

        assert result.success
        assert result.data["total"] == 1
        custom_crud.find.assert_called_once()
        default_crud.find.assert_not_called()
