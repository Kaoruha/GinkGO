"""
#5694: GET /engines 列表分页端点测试。

直调端点函数（避开 app 启动 / root main.py 遮蔽），
patch get_engine_service 注入 mock。
"""

import asyncio
from unittest.mock import patch, MagicMock

from ginkgo.data.services.base_service import ServiceResult


def _engine(uuid, name="engine", start=None, end=None):
    """构造引擎 mock（属性式，匹配端点 getattr 取值路径）。"""
    e = MagicMock()
    e.uuid = uuid
    e.name = name
    e.backtest_start_date = start
    e.backtest_end_date = end
    return e


class TestListBacktestEnginesPagination:
    """GET /engines 分页契约（#5694）。"""

    def test_pagination_passes_page_and_returns_paginated(self):
        """传 page/page_size → service.get 传 0-based page，返回 paginated(items, total)。"""
        from api.backtest import list_backtest_engines

        mock_service = MagicMock()
        sr = ServiceResult.success(data=[_engine("e1"), _engine("e2")])
        sr.set_metadata("total", 15)
        mock_service.get.return_value = sr

        with patch("api.backtest.get_engine_service", return_value=mock_service):
            result = asyncio.run(list_backtest_engines(is_live=False, page=2, page_size=10))

        # page=2(1-based) → service 传 page=1(0-based)
        mock_service.get.assert_called_once_with(is_live=0, page=1, page_size=10)
        assert result["code"] == 0
        assert result["meta"]["total"] == 15
        assert result["meta"]["page"] == 2
        assert result["meta"]["page_size"] == 10
        assert len(result["data"]) == 2
        assert result["data"][0]["uuid"] == "e1"

    def test_page_one_maps_to_zero_based(self):
        """page=1(首页, 1-based) → service 传 page=0(0-based) 转换正确。

        注：Query 默认值由 FastAPI 框架保证（HTTP 请求路径），直调端点
        无法触发默认值注入（arch_api_test_query_default_direct_await），
        故此处显式传 page=1 验证 1-based→0-based 转换逻辑。
        """
        from api.backtest import list_backtest_engines

        mock_service = MagicMock()
        sr = ServiceResult.success(data=[])
        sr.set_metadata("total", 0)
        mock_service.get.return_value = sr

        with patch("api.backtest.get_engine_service", return_value=mock_service):
            result = asyncio.run(list_backtest_engines(is_live=False, page=1, page_size=20))

        # page=1(1-based) → service page=0(0-based)
        mock_service.get.assert_called_once_with(is_live=0, page=0, page_size=20)
        assert result["meta"]["page"] == 1
        assert result["meta"]["total"] == 0

    def test_service_missing_total_defaults_to_zero(self):
        """service 未设 total（异常分支）→ paginated total 兜底 0 不崩。"""
        from api.backtest import list_backtest_engines

        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=[])  # 无 metadata

        with patch("api.backtest.get_engine_service", return_value=mock_service):
            result = asyncio.run(list_backtest_engines(is_live=False, page=1, page_size=5))

        assert result["code"] == 0
        assert result["meta"]["total"] == 0
