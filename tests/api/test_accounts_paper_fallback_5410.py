# Issue #5410: /accounts balance/positions should accept paper account portfolio UUIDs.

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

from ginkgo.data.services.base_service import ServiceResult


def run_async(coro):
    return asyncio.run(coro)


def test_account_balance_falls_back_to_paper_portfolio(api_modules, monkeypatch):
    """live_account 查不到时，PAPER Portfolio uuid 应返回模拟盘余额。"""
    from api import accounts as accounts_api
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    live_service = MagicMock()
    live_service.get_account_balance.return_value = {
        "success": False,
        "message": "Account not found: paper-1",
    }

    portfolio = SimpleNamespace(
        uuid="paper-1",
        mode=PORTFOLIO_MODE_TYPES.PAPER,
        cash=45000,
        frozen=500,
        initial_capital=50000,
    )
    portfolio_service = MagicMock()
    portfolio_service.get.return_value = ServiceResult.success([portfolio])

    monkeypatch.setattr(accounts_api, "get_live_account_service", lambda: live_service)
    monkeypatch.setattr(accounts_api, "_get_portfolio_service", lambda: portfolio_service)
    monkeypatch.setattr(accounts_api, "_query_paper_positions", lambda _account_id: [{"market_value": 2500.0}])

    result = run_async(accounts_api.get_account_balance("paper-1"))

    assert result["data"]["total_equity"] == "48000.0"
    assert result["data"]["available_balance"] == "45000.0"
    assert result["data"]["frozen_balance"] == "500.0"
    assert result["data"]["currency_balances"][0]["balance"] == "48000.0"


def test_account_positions_falls_back_to_paper_positions(api_modules, monkeypatch):
    """live_account 查不到时，PAPER Portfolio uuid 应返回模拟盘持仓。"""
    from api import accounts as accounts_api
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    live_service = MagicMock()
    live_service.get_account_positions.return_value = {
        "success": False,
        "message": "Account not found: paper-1",
    }

    portfolio = SimpleNamespace(uuid="paper-1", mode=PORTFOLIO_MODE_TYPES.PAPER)
    portfolio_service = MagicMock()
    portfolio_service.get.return_value = ServiceResult.success([portfolio])

    positions = [
        {
            "code": "000001",
            "shares": 100,
            "cost": 900.0,
            "current": 10.0,
            "market_value": 1000.0,
            "pnl": 100.0,
            "pnl_ratio": 11.11,
        }
    ]

    monkeypatch.setattr(accounts_api, "get_live_account_service", lambda: live_service)
    monkeypatch.setattr(accounts_api, "_get_portfolio_service", lambda: portfolio_service)
    monkeypatch.setattr(accounts_api, "_query_paper_positions", lambda _account_id: positions)

    result = run_async(accounts_api.get_account_positions("paper-1"))

    assert result["data"]["positions"] == [
        {
            "symbol": "000001",
            "side": "long",
            "size": "100",
            "avg_price": "9.0",
            "current_price": "10.0",
            "unrealized_pnl": "100.0",
            "unrealized_pnl_percentage": "11.11",
            "margin": "0",
        }
    ]
