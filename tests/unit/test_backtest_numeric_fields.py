"""#5864: 回测 Positions/Orders 数值字段应返回 JSON number 类型。

根因：BacktestPositionItem/BacktestOrderItem schema 数值字段声明为 str，
service.list_positions/list_orders 填充时用 str() 包装 Decimal/float。
双层修复：schema str→float + service 去掉 str()。
"""
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService


def _make_service():
    """绕过 __init__（需 crud_repo 依赖），直接构造实例 + stub _resolve_task_id。"""
    svc = object.__new__(BacktestTaskService)
    svc._resolve_task_id = lambda uuid: ("task-1", "pf-1", None)
    return svc


def _make_position(cost=19.81, volume=50, price=19.81, fee=5):
    p = MagicMock()
    p.uuid = "p1"; p.portfolio_id = "pf"; p.engine_id = "e"; p.task_id = "t"
    p.code = "000001.SZ"; p.cost = cost; p.volume = volume
    p.frozen_volume = 0; p.price = price; p.fee = fee
    return p


def _make_order(limit_price=0, transaction_price=19.81, fee=5):
    o = MagicMock()
    o.uuid = "o1"; o.portfolio_id = "pf"; o.engine_id = "e"; o.task_id = "t"
    o.code = "000001.SZ"; o.direction = 1; o.order_type = 1; o.status = 2
    o.volume = 50; o.limit_price = limit_price
    o.transaction_price = transaction_price; o.transaction_volume = 50
    o.fee = fee; o.timestamp = None
    return o


class TestPositionNumericFields:
    """#5864: positions cost/price/fee 应为 float 非 str。"""

    def test_cost_is_float_not_string(self):
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_positions.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_position()], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_positions("x")
        item = result.data[0]
        assert isinstance(item.cost, float)
        assert not isinstance(item.cost, str)
        assert item.cost == pytest.approx(19.81)

    def test_price_is_float_not_string(self):
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_positions.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_position(price=20.5)], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_positions("x")
        assert isinstance(result.data[0].price, float)
        assert result.data[0].price == pytest.approx(20.5)

    def test_fee_is_float_not_string(self):
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_positions.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_position(fee=5)], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_positions("x")
        assert isinstance(result.data[0].fee, float)
        assert result.data[0].fee == pytest.approx(5.0)


class TestOrderNumericFields:
    """#5864: orders transaction_price/fee 应为 float；limit_price=0（市价单）应返 None。"""

    def test_transaction_price_is_float_not_string(self):
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_orders.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_order()], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_orders("x")
        item = result.data[0]
        assert isinstance(item.transaction_price, float)
        assert not isinstance(item.transaction_price, str)
        assert item.transaction_price == pytest.approx(19.81)

    def test_fee_is_float_not_string(self):
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_orders.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_order(fee=5)], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_orders("x")
        assert isinstance(result.data[0].fee, float)
        assert result.data[0].fee == pytest.approx(5.0)

    def test_limit_price_zero_returns_none(self):
        """#5864 验收：limit_price=0（市价单无限制价格）应返 None 非 "0"。"""
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_orders.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_order(limit_price=0)], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_orders("x")
        assert result.data[0].limit_price is None

    def test_limit_price_nonzero_is_float(self):
        """限价单 limit_price 非 0 时应返 float。"""
        svc = _make_service()
        mock_rs = MagicMock()
        mock_rs.get_orders.return_value = MagicMock(
            is_success=lambda: True, data={"data": [_make_order(limit_price=20.5)], "total": 1}
        )
        with patch("ginkgo.data.containers.container.result_service", return_value=mock_rs):
            result = svc.list_orders("x")
        assert isinstance(result.data[0].limit_price, float)
        assert result.data[0].limit_price == pytest.approx(20.5)
