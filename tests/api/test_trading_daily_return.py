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
