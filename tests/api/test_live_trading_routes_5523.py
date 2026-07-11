# Issue: #5523
# Role: WebUI live-trading API contract must have matching backend routes.

import pytest
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "api"


def _ensure_api_path():
    api_dir = str(API_DIR)
    if sys.path[:1] != [api_dir]:
        sys.path.insert(0, api_dir)


def _load_api_main():
    _ensure_api_path()
    from fastapi import FastAPI

    if not hasattr(FastAPI, "add_websocket_route"):
        FastAPI.add_websocket_route = FastAPI.add_api_websocket_route

    spec = importlib.util.spec_from_file_location("ginkgo_api_main_5523", API_DIR / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _route_methods(app):
    methods_by_path = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path and methods:
            methods_by_path.setdefault(path, set()).update(methods)
    return methods_by_path


def test_live_trading_frontend_routes_are_registered():
    """The WebUI trading.ts live calls must not resolve to 404 route misses."""
    main = _load_api_main()

    routes = _route_methods(main.app)
    expected = {
        ("/api/v1/live-trading/accounts", "GET"),
        ("/api/v1/live-trading/accounts/{account_id}/connect", "POST"),
        ("/api/v1/live-trading/accounts/{account_id}/disconnect", "POST"),
        ("/api/v1/live-trading/{account_id}/positions", "GET"),
        ("/api/v1/live-trading/{account_id}/active-orders", "GET"),
        ("/api/v1/live-trading/{account_id}/orders/{order_id}", "DELETE"),
        ("/api/v1/live-trading/{account_id}/capital", "GET"),
        ("/api/v1/live-trading/{account_id}/risk/status", "GET"),
        ("/api/v1/live-trading/{account_id}/risk/circuit-breaker", "POST"),
        ("/api/v1/live-trading/logs", "GET"),
    }

    missing = sorted(f"{method} {path}" for path, method in expected if method not in routes.get(path, set()))
    assert missing == []


def test_live_trading_router_is_shallow_backend_compatibility_layer():
    """The compatibility router should exist as a thin API layer, not a frontend mock."""
    _ensure_api_path()
    from api import live_trading

    paths = {getattr(route, "path", "") for route in live_trading.router.routes}
    assert "/accounts" in paths
    assert "/{account_id}/positions" in paths
    assert "/{account_id}/capital" in paths
