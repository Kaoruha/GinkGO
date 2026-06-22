# Issue #6048: trading API 股票名称查询（_query_positions/_query_orders 接 StockinfoService）
# Upstream: api.api.trading._query_positions / _query_orders
# Downstream: ginkgo.data.services.stockinfo_service.StockinfoService.get_stockinfos
# Role: 验证 positions/orders 返回的 name 从 stock_info 真实查询（不再硬编码 ""）。

"""
#6048 子集测试：trading 端点股票名称硬编码空。

``_query_positions`` (trading.py:556) 和 ``_query_orders`` (trading.py:613) 的
``name`` 字段是 TODO 桩（固定 ""），未接已存在的 ``StockinfoService``（容器已注入，
``get_stockinfos(code=)`` 返 ``ServiceResult.success(data=[StockInfo])``）。

本测试 mock result_service + stockinfo_service，断言 name 从 stockinfo 填充，
未查到的 code 降级为 ""（不崩）。
"""
import asyncio
from types import SimpleNamespace

import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


def _pos(code="000001", cost=10.0, price=11.0, volume=100):
    return SimpleNamespace(code=code, cost=cost, price=price, volume=volume)


def _order(code="000001"):
    return SimpleNamespace(
        code=code, direction=1, uuid="ord-1", limit_price=10.0, volume=100,
        transaction_volume=100, transaction_price=10.0, status=1,
        business_timestamp=None,
    )


def _stock(code="000001", name="平安银行"):
    # StockInfo Entity 中文字段是 code_name（非 name，arch_stockinfo_entity_code_name_field）；
    # SimpleNamespace 用 code_name 属性名对齐真实结构，避免伪造 name 属性掩盖提取 bug。
    return SimpleNamespace(code=code, code_name=name)


class TestQueryPositionsStockName:
    """_query_positions 从 stockinfo 填充 name（#6048）。"""

    def test_fills_name_from_stockinfo(self):
        """position name 从 StockinfoService 查询填充（不再 ""）。"""
        mock_result = MagicMock()
        mock_result.get_current_positions.return_value = ServiceResult.success(
            data=[_pos(code="000001")]
        )
        mock_stockinfo = MagicMock(spec=StockinfoService)
        mock_stockinfo.get_stockinfos.return_value = ServiceResult.success(
            data=[_stock(code="000001", name="平安银行")]
        )

        from api.trading import _query_positions

        with patch("api.trading._get_result_service", return_value=mock_result), \
             patch("api.trading._get_stockinfo_service", return_value=mock_stockinfo):
            positions = _query_positions("acc-1")

        assert len(positions) == 1
        assert positions[0]["name"] == "平安银行"

    def test_unknown_code_name_falls_back_to_empty(self):
        """stockinfo 未查到的 code，name 降级为 ""（不崩）。"""
        mock_result = MagicMock()
        mock_result.get_current_positions.return_value = ServiceResult.success(
            data=[_pos(code="999999")]
        )
        mock_stockinfo = MagicMock(spec=StockinfoService)
        mock_stockinfo.get_stockinfos.return_value = ServiceResult.success(data=[])  # 未查到

        from api.trading import _query_positions

        with patch("api.trading._get_result_service", return_value=mock_result), \
             patch("api.trading._get_stockinfo_service", return_value=mock_stockinfo):
            positions = _query_positions("acc-1")

        assert positions[0]["name"] == ""


class TestQueryOrdersStockName:
    """_query_orders 从 stockinfo 填充 name（#6048）。"""

    def test_fills_name_from_stockinfo(self):
        """order name 从 StockinfoService 查询填充（不再 ""）。"""
        mock_result = MagicMock()
        mock_result.get_orders_by_portfolio.return_value = ServiceResult.success(
            data={"data": [_order(code="600000")]}
        )
        mock_stockinfo = MagicMock(spec=StockinfoService)
        mock_stockinfo.get_stockinfos.return_value = ServiceResult.success(
            data=[_stock(code="600000", name="浦发银行")]
        )

        from api.trading import _query_orders

        with patch("api.trading._get_result_service", return_value=mock_result), \
             patch("api.trading._get_stockinfo_service", return_value=mock_stockinfo):
            orders = _query_orders("acc-1")

        assert len(orders) >= 1
        assert orders[0]["name"] == "浦发银行"

    def test_distinct_codes_dedup_stockinfo_queries(self):
        """多个 position 同 code 去重查询（避免 N+1，#5675 同类陷阱）。"""
        mock_result = MagicMock()
        mock_result.get_current_positions.return_value = ServiceResult.success(
            data=[_pos(code="000001"), _pos(code="000001"), _pos(code="000002")]
        )
        mock_stockinfo = MagicMock(spec=StockinfoService)
        mock_stockinfo.get_stockinfos.return_value = ServiceResult.success(data=[])

        from api.trading import _query_positions

        with patch("api.trading._get_result_service", return_value=mock_result), \
             patch("api.trading._get_stockinfo_service", return_value=mock_stockinfo):
            _query_positions("acc-1")

        # 去重后只查 2 次（000001 + 000002），不是 3 次
        assert mock_stockinfo.get_stockinfos.call_count == 2
