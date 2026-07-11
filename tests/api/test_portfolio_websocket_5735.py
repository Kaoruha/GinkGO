"""#5735: portfolio WebSocket subscribe must acknowledge channel payloads."""

import asyncio
import importlib
import importlib.util
from pathlib import Path

import pytest


class _FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


class _FakeConnectionManager:
    def __init__(self):
        self.subscribed = []

    async def subscribe(self, websocket, topic):
        self.subscribed.append((websocket, topic))


@pytest.mark.unit
def test_main_registers_portfolio_websocket_route(api_modules):
    api_main = Path(__file__).resolve().parents[2] / "api" / "main.py"
    spec = importlib.util.spec_from_file_location("ginkgo_api_main_ws_5735", str(api_main))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    paths = {route.path for route in mod.app.routes}

    assert "/ws/portfolio" in paths


@pytest.mark.unit
def test_portfolio_subscribe_accepts_channel_payload(monkeypatch):
    from websocket.handlers.portfolio_handler import PortfolioHandler

    portfolio_handler_module = importlib.import_module("websocket.handlers.portfolio_handler")
    fake_manager = _FakeConnectionManager()
    fake_ws = _FakeWebSocket()
    monkeypatch.setattr(portfolio_handler_module, "connection_manager", fake_manager)

    asyncio.run(
        PortfolioHandler()._handle_message(
            fake_ws,
            {"type": "subscribe", "channel": "portfolio_update"},
            user_uuid="user-1",
        )
    )

    assert fake_manager.subscribed == [(fake_ws, "portfolio_update")]
    assert fake_ws.sent == [{"type": "subscribed", "topic": "portfolio_update"}]
