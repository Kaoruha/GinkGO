# Issue #6048: trading API today_pnl / daily_return use real net asset deltas.

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


def test_get_paper_report_total_and_daily_return_use_net_assets(api_modules):
    """日报收益率应基于现金+持仓市值；日收益基于上一条净值记录。"""
    from api.trading import get_paper_report
    from ginkgo.enums import ORDERSTATUS_TYPES

    portfolio = SimpleNamespace(uuid="acc-1", initial_capital=100000, cash=95000)
    positions = [
        SimpleNamespace(code="000001", price=10, volume=600, status=None),
        SimpleNamespace(code="600000", price=20, volume=200, status=None),
    ]
    orders = [SimpleNamespace(status=ORDERSTATUS_TYPES.FILLED)]

    result_service = MagicMock()
    result_service.get_orders_by_portfolio_date.return_value = ServiceResult.success(orders)
    result_service.get_current_positions.return_value = ServiceResult.success(positions)

    with (
        patch("api.trading._require_portfolio", return_value=[portfolio]),
        patch("api.trading._get_result_service", return_value=result_service),
        patch("api.trading._query_previous_net_asset", return_value=102000.0),
    ):
        result = run_async(get_paper_report("acc-1", date="2026-07-05"))

    data = result["data"]
    assert data["total_return"] == 5.0
    assert data["daily_return"] == 2.9412
    assert data["trades_count"] == 1
    assert data["positions_count"] == 2


def test_get_paper_account_today_pnl_uses_previous_net_asset(api_modules):
    """账户详情 today_pnl = 当前净资产 - 上一条净值记录。"""
    from api.trading import get_paper_account

    portfolio = SimpleNamespace(
        uuid="acc-1",
        name="paper",
        initial_capital=100000,
        cash=95000,
        create_at=None,
    )
    positions = [{"code": "000001", "market_value": 10000.0}]

    with (
        patch("api.trading._require_portfolio", return_value=[portfolio]),
        patch("api.trading._query_positions", return_value=positions),
        patch("api.trading._query_orders", return_value=[]),
        patch("api.trading._query_previous_net_asset", return_value=102000.0),
    ):
        result = run_async(get_paper_account("acc-1"))

    data = result["data"]
    assert data["total_asset"] == 105000.0
    assert data["today_pnl"] == 3000.0


def test_list_paper_accounts_today_pnl_uses_each_account_previous_net_asset(api_modules):
    """账户列表每个账户独立计算 today_pnl。"""
    from api.trading import list_paper_accounts

    p1 = SimpleNamespace(uuid="acc-1", name="a", initial_capital=100000, cash=95000, create_at=None)
    p2 = SimpleNamespace(uuid="acc-2", name="b", initial_capital=200000, cash=180000, create_at=None)

    portfolio_service = MagicMock()
    portfolio_service.get.return_value = ServiceResult.success([p1, p2])

    positions_map = {
        "acc-1": [{"market_value": 10000.0}],
        "acc-2": [{"market_value": 15000.0}],
    }
    previous_map = {"acc-1": 102000.0, "acc-2": 190000.0}

    with (
        patch("api.trading._get_portfolio_service", return_value=portfolio_service),
        patch("api.trading._query_positions", side_effect=lambda aid: positions_map[aid]),
        patch("api.trading._query_previous_net_asset", side_effect=lambda aid: previous_map[aid]),
    ):
        result = run_async(list_paper_accounts())

    accounts = result["data"]
    assert accounts[0]["today_pnl"] == 3000.0
    assert accounts[1]["today_pnl"] == 5000.0


def test_query_previous_net_asset_raises_on_db_failure(api_modules):
    """AnalyzerService DB 故障（ServiceResult.error）必须 loud raise HTTPException 500，
    不得静默归 None 让 today_pnl/daily_return 归 0（对齐 _query_positions, #5479 / 544c851c）。"""
    from api.trading import _query_previous_net_asset
    from fastapi import HTTPException

    analyzer_service = MagicMock()
    analyzer_service.find_latest_before.return_value = ServiceResult.error("DB connection lost")

    with patch("api.trading._get_analyzer_service", return_value=analyzer_service):
        with pytest.raises(HTTPException) as exc:
            _query_previous_net_asset("acc-1")

    assert exc.value.status_code == 500
    # DB 故障必须立即 raise，不得降级试 use_business_time=False
    assert analyzer_service.find_latest_before.call_count == 1


def test_query_previous_net_asset_returns_value_and_falls_back_to_timestamp(api_modules):
    """success + business_time 查空 → 降级 timestamp 查到 → 返回 value。"""
    from api.trading import _query_previous_net_asset

    record = SimpleNamespace(value=102000.0)
    analyzer_service = MagicMock()
    analyzer_service.find_latest_before.side_effect = [
        ServiceResult.success([]),  # use_business_time=True 空
        ServiceResult.success([record]),  # use_business_time=False 命中
    ]

    with patch("api.trading._get_analyzer_service", return_value=analyzer_service):
        value = _query_previous_net_asset("acc-1", target_date="2026-07-05")

    assert value == 102000.0
    assert analyzer_service.find_latest_before.call_count == 2
    _, kwargs_t = analyzer_service.find_latest_before.call_args_list[0]
    _, kwargs_f = analyzer_service.find_latest_before.call_args_list[1]
    assert kwargs_t["use_business_time"] is True
    assert kwargs_f["use_business_time"] is False


def test_get_paper_report_propagates_helper_http_exception(api_modules):
    """端点层须透传 _query_previous_net_asset 的 HTTPException(500)。

    DB 故障时 helper 已 loud raise HTTPException(500)（见
    test_query_previous_net_asset_raises_on_db_failure）；但 ``get_paper_report``
    的 ``except Exception`` 会把 HTTPException 吞成 BusinessError(400)（HTTPException
    继承 Exception，FastAPI 按 MRO 先于 HTTPException handler 匹配 except Exception），
    违反本 PR AC + 544c851c/#5479 立规。须 ``except HTTPException: raise`` 前置透传，
    对齐 list_paper_accounts / get_paper_account。
    """
    from api.trading import get_paper_report
    from fastapi import HTTPException

    portfolio = SimpleNamespace(uuid="acc-1", initial_capital=100000, cash=95000)
    result_service = MagicMock()
    result_service.get_orders_by_portfolio_date.return_value = ServiceResult.success([])
    result_service.get_current_positions.return_value = ServiceResult.success([])

    with (
        patch("api.trading._require_portfolio", return_value=[portfolio]),
        patch("api.trading._get_result_service", return_value=result_service),
        patch(
            "api.trading._query_previous_net_asset",
            side_effect=HTTPException(status_code=500, detail="查询上一日净资产失败: DB down"),
        ),
    ):
        with pytest.raises(HTTPException) as exc:
            run_async(get_paper_report("acc-1", date="2026-07-05"))

    assert exc.value.status_code == 500


def test_query_previous_net_asset_none_when_no_history(api_modules):
    """两次查询都空（无历史记录）→ 返回 None（合法，新账户未跑过）。"""
    from api.trading import _query_previous_net_asset

    analyzer_service = MagicMock()
    analyzer_service.find_latest_before.return_value = ServiceResult.success([])

    with patch("api.trading._get_analyzer_service", return_value=analyzer_service):
        value = _query_previous_net_asset("acc-1", target_date="2026-07-05")

    assert value is None
    assert analyzer_service.find_latest_before.call_count == 2
