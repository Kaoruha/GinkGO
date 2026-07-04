"""#5429: GET /{uuid}/orders 分页失效——端点忽略 page_size 返回全量。

本测试覆盖 API 路由层: 直调路由函数, mock task_service, 断言 /orders 端点
接受 page/page_size 并透传给 list_orders, 返回结构含独立 total(去重总数,
非当前页条数)。行为与同模块 /signals 端点对齐(参考 test_backtest_pagination)。
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.base_service import ServiceResult


def _mock_item(order_id):
    m = MagicMock()
    m.dict.return_value = {"order_id": order_id}
    return m


class TestBacktestOrdersPagination:
    """#5429: /{uuid}/orders 端点分页参数透传与返回结构。"""

    @pytest.mark.unit
    def test_orders_passes_pagination_to_service(self):
        """端点应接受 page/page_size 并透传给 task_service.list_orders。"""
        from api.backtest import get_backtest_orders

        items = [_mock_item("ord-A"), _mock_item("ord-B")]
        sr = ServiceResult(success=True, data=items)
        sr.set_metadata("total", 10)

        mock_svc = MagicMock()
        mock_svc.list_orders.return_value = sr

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            resp = asyncio.run(get_backtest_orders("any-uuid", page=1, page_size=2))

        # 透传: page/page_size 必须传给 list_orders
        mock_svc.list_orders.assert_called_once_with("any-uuid", page=1, page_size=2)
        # 返回结构: total 独立于当前页条数(2 条 data, total=10)
        assert len(resp["data"]) == 2
        assert resp["meta"]["total"] == 10
        assert resp["meta"]["page"] == 1
        assert resp["meta"]["page_size"] == 2

    @pytest.mark.unit
    def test_orders_default_page_size_is_fifty(self):
        """签名默认 page=1/page_size=50(对齐 agent brief, 非全量 max(total,1))。

        直调端点时 FastAPI Query 默认值不自动解析成 int(见 arch_api_test_
        query_default_direct_await), 故用 inspect 验证签名契约——签名默认值
        即 FastAPI 运行时实际下发的值。
        """
        import inspect
        from api.backtest import get_backtest_orders

        sig = inspect.signature(get_backtest_orders)
        page_default = sig.parameters["page"].default
        ps_default = sig.parameters["page_size"].default

        # Query 参数对象有 .default 属性; 裸 int 默认值没有, 故用 hasattr 鉴别。
        # ge/le 约束由 FastAPI 运行时校验, 签名声明见端点源码 Query(50, ge=1, le=500)。
        assert hasattr(page_default, "default") and page_default.default == 1
        assert hasattr(ps_default, "default"), "page_size 必须是 Query 参数对象, 非裸 int"
        assert ps_default.default == 50, "默认 page_size 应为 50, 非 max(total,1) 全量"

    @pytest.mark.unit
    def test_orders_total_independent_of_page_size(self):
        """不同 page_size 应返回相同 total(total=DB 去重总数, 非当前页条数)。"""
        from api.backtest import get_backtest_orders

        def make_sr(n_items, total):
            sr = ServiceResult(success=True, data=[_mock_item(f"o{i}") for i in range(n_items)])
            sr.set_metadata("total", total)
            return sr

        # page_size=2 返回 2 条
        mock_svc = MagicMock()
        mock_svc.list_orders.return_value = make_sr(2, 10)
        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            resp_small = asyncio.run(get_backtest_orders("any-uuid", page=1, page_size=2))
        assert len(resp_small["data"]) == 2
        assert resp_small["meta"]["total"] == 10

        # page_size=50 返回更多条, 但 total 仍应相同
        mock_svc.list_orders.return_value = make_sr(8, 10)
        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            resp_large = asyncio.run(get_backtest_orders("any-uuid", page=1, page_size=50))
        assert len(resp_large["data"]) == 8
        assert resp_large["meta"]["total"] == 10, "total 必须与 page_size 无关"
