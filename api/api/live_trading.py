"""
Live Trading compatibility API routes.

These routes match the legacy WebUI trading.ts live-trading contract while
delegating account data to the existing live account service layer.
"""

from fastapi import APIRouter, Query, Request
from typing import Optional

from api import accounts
from core.exceptions import BusinessError, NotFoundError
from core.response import ok

router = APIRouter()


def _status_for_trading(account_status: str) -> str:
    if account_status in ("enabled", "connecting"):
        return "connected"
    if account_status == "error":
        return "error"
    return "disconnected"


def _float_value(data: dict, *keys: str) -> float:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _require_owned_account(account_id: str, request: Request) -> dict:
    service = accounts.get_live_account_service()
    result = service.get_account_by_uuid(account_id)
    if not result.get("success") or not result.get("data"):
        raise NotFoundError("Account", account_id)
    account_data = result["data"]
    accounts._require_account_ownership(account_data, accounts._get_user_id(request))
    return account_data


@router.get("/accounts")
async def list_live_trading_accounts(request: Request):
    """List live accounts using the legacy trading.ts response shape."""
    service = accounts.get_live_account_service()
    user_id = accounts._get_user_id(request)
    result = service.get_user_accounts(user_id=user_id, page=1, page_size=100)
    if not result.get("success"):
        raise BusinessError(result.get("message", "Failed to list live accounts"))

    payload = result.get("data") or {}
    account_rows = payload.get("accounts", payload if isinstance(payload, list) else [])
    live_accounts = [
        {
            "uuid": account.get("uuid", ""),
            "name": account.get("name", ""),
            "broker_type": account.get("exchange", ""),
            "status": _status_for_trading(account.get("status", "")),
            "total_asset": 0,
            "available_cash": 0,
            "position_value": 0,
            "today_pnl": 0,
        }
        for account in account_rows
    ]
    return ok(data=live_accounts, message="Live trading accounts retrieved successfully")


@router.post("/accounts/{account_id}/connect")
async def connect_broker(account_id: str, request: Request):
    """Enable a live account for broker connection workflows."""
    _require_owned_account(account_id, request)
    service = accounts.get_live_account_service()
    result = service.update_account_status(account_id, "enabled")
    if not result.get("success"):
        raise BusinessError(result.get("message", "Failed to connect broker"))
    return ok(data={"success": True}, message="Broker connection enabled")


@router.post("/accounts/{account_id}/disconnect")
async def disconnect_broker(account_id: str, request: Request):
    """Disable a live account for broker connection workflows."""
    _require_owned_account(account_id, request)
    service = accounts.get_live_account_service()
    result = service.update_account_status(account_id, "disabled")
    if not result.get("success"):
        raise BusinessError(result.get("message", "Failed to disconnect broker"))
    return ok(data={"success": True}, message="Broker connection disabled")


@router.get("/{account_id}/positions")
async def get_live_positions(account_id: str, request: Request):
    _require_owned_account(account_id, request)
    return await accounts.get_account_positions(account_id)


@router.get("/{account_id}/active-orders")
async def get_live_active_orders(account_id: str, request: Request):
    _require_owned_account(account_id, request)
    return ok(data=[], message="Live active orders are not available yet")


@router.delete("/{account_id}/orders/{order_id}")
async def cancel_live_order(account_id: str, order_id: str, request: Request):
    _require_owned_account(account_id, request)
    raise BusinessError("Live order cancellation is not implemented", code=501)


@router.get("/{account_id}/capital")
async def get_live_capital(account_id: str, request: Request):
    _require_owned_account(account_id, request)
    result = await accounts.get_account_balance(account_id)
    balance = result.get("data") or {}
    total_asset = _float_value(balance, "total_asset", "total_equity", "balance")
    available_cash = _float_value(balance, "available_cash", "available_balance", "available")
    frozen_cash = _float_value(balance, "frozen_cash", "frozen_balance", "frozen")
    return ok(
        data={
            "total_asset": total_asset,
            "available_cash": available_cash,
            "position_value": max(total_asset - available_cash - frozen_cash, 0),
            "frozen_cash": frozen_cash,
            "today_pnl": _float_value(balance, "today_pnl"),
        },
        message="Live capital retrieved successfully",
    )


@router.get("/{account_id}/risk/status")
async def get_live_risk_status(account_id: str, request: Request):
    _require_owned_account(account_id, request)
    return ok(
        data={
            "account_id": account_id,
            "position_ratio": 0,
            "total_pnl_ratio": 0,
            "max_drawdown": 0,
            "status": "normal",
            "warnings": [],
        },
        message="Live risk status retrieved successfully",
    )


@router.post("/{account_id}/risk/circuit-breaker")
async def trigger_circuit_breaker(account_id: str, request: Request):
    _require_owned_account(account_id, request)
    raise BusinessError("Live circuit breaker is not implemented", code=501)


@router.get("/logs")
async def get_trading_logs(
    request: Request,
    account_id: str = Query(...),
    account_type: str = Query("live"),
    log_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    _require_owned_account(account_id, request)
    return ok(data=[], message="Live trading logs are not available yet")
