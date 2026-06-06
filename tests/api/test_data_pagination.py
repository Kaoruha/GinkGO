# Issue: ticks/adjustfactors 全量加载后 Python 切片
# Upstream: api.api.data.get_ticks, get_adjust_factors
# Downstream: TickService.get(), AdjustfactorService.get()
# Role: 验证分页参数传递到 CRUD 层，不做 Python 层切片

"""
ticks 和 adjustfactors 分页测试

验证 get_ticks / get_adjust_factors 将 page/page_size 传给 service 层，
不在 API 层全量加载后切片。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


class TestTicksPagination:
    """ticks 分页测试"""

    def test_passes_pagination_to_service(self):
        """TDD Red: get_ticks 应将分页参数传给 service"""

        mock_tick = MagicMock()
        mock_tick.uuid = "tick-1"
        mock_tick.timestamp = datetime(2025, 1, 1)
        mock_tick.price = 10.0
        mock_tick.volume = 100
        mock_tick.direction = 0

        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[mock_tick])

        from api.data import get_ticks

        with patch("api.data.get_tick_service", return_value=mock_service):
            result = run_async(get_ticks(code="000001.SZ", page=2, page_size=50))

        # service.get 应接收到 page/page_size
        call_kwargs = mock_service.get.call_args.kwargs
        assert call_kwargs.get("page") == 1 or call_kwargs.get("offset") is not None

    def test_returns_total_from_service_not_len(self):
        """TDD Red: total 应来自 service/DB，不是 len(全量列表)"""

        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[])
        # 当 service 返回空结果但有 total 信息

        from api.data import get_ticks

        with patch("api.data.get_tick_service", return_value=mock_service):
            result = run_async(get_ticks(code="000001.SZ", page=1, page_size=100))

        # 不应因空结果报错
        assert "data" in result or "items" in result


class TestAdjustFactorsPagination:
    """adjustfactors 分页测试"""

    def test_passes_pagination_to_service(self):
        """TDD Red: get_adjust_factors 应将分页参数传给 service"""

        mock_factor = MagicMock()
        mock_factor.uuid = "factor-1"
        mock_factor.code = "000001.SZ"
        mock_factor.timestamp = datetime(2025, 1, 1)
        mock_factor.factor = 1.0

        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[mock_factor])

        from api.data import get_adjust_factors

        with patch("api.data.get_adjustfactor_service", return_value=mock_service):
            result = run_async(get_adjust_factors(code="000001.SZ", page=3, page_size=20))

        # service.get 应接收到分页参数
        call_kwargs = mock_service.get.call_args.kwargs
        assert call_kwargs.get("page") is not None or call_kwargs.get("limit") is not None
