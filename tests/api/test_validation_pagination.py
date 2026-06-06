# Issue: validation results 全量加载 + Python 切片
# Upstream: api.api.validation.list_results
# Downstream: ValidationService._result_crud
# Role: 验证分页参数传到 CRUD 层，不做 Python 切片

"""
验证结果分页测试

验证 list_results 将 page/page_size 传给 CRUD 层，
不在 API 层全量加载后切片。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


class TestValidationResultsPagination:
    """验证结果分页测试"""

    def test_passes_pagination_to_crud(self):
        """TDD Red: list_results 应将 page/page_size 传给 crud.find()"""

        mock_crud = MagicMock()
        mock_crud.find.return_value = []

        mock_service = MagicMock()
        mock_service._result_crud = mock_crud

        from api.validation import list_results

        with patch("api.validation.get_validation_service", return_value=mock_service):
            result = run_async(list_results(page=3, page_size=15))

        # crud.find 应接收到 page/page_size
        call_kwargs = mock_crud.find.call_args.kwargs
        assert call_kwargs.get("page") == 2  # 0-based
        assert call_kwargs.get("page_size") == 15

    def test_no_python_slicing(self):
        """TDD Red: 不应在 Python 层切片"""
        mock_record = MagicMock()
        mock_record.uuid = "r-1"
        mock_record.task_id = "t-1"
        mock_record.portfolio_id = "p-1"
        mock_record.method = "monte_carlo"
        mock_record.config = "{}"
        mock_record.result = "{}"
        mock_record.score = 0.8
        mock_record.status = "completed"
        mock_record.create_at = MagicMock()
        mock_record.create_at.isoformat.return_value = "2025-01-01T00:00:00"

        mock_crud = MagicMock()
        # crud 返回当前页数据（10条）
        mock_crud.find.return_value = [mock_record] * 10
        mock_crud.count.return_value = 42

        mock_service = MagicMock()
        mock_service._result_crud = mock_crud

        from api.validation import list_results

        with patch("api.validation.get_validation_service", return_value=mock_service):
            result = run_async(list_results(page=2, page_size=10))

        # 只拿到当前页 10 条，total 来自 crud.count
        assert result["meta"]["total"] == 42
        assert len(result["data"]) == 10
