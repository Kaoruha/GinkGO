"""Smoke tests for livecore.websocket_manager -- #3870"""
import pytest

try:
    from ginkgo.livecore.websocket_manager import (
        WebSocketManager, WebSocketConnection, WebSocketType, ConnectionState,
    )
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="websocket_manager not available")
class TestEnums:
    def test_websocket_type(self):
        assert hasattr(WebSocketType, 'PUBLIC')
        assert hasattr(WebSocketType, 'PRIVATE')

    def test_connection_state(self):
        assert hasattr(ConnectionState, 'DISCONNECTED')
        assert hasattr(ConnectionState, 'CONNECTING')
        assert hasattr(ConnectionState, 'CONNECTED')
        assert hasattr(ConnectionState, 'ERROR')


@pytest.mark.skipif(not HAS_MODULE, reason="websocket_manager not available")
class TestWebSocketConnection:
    def test_instantiation_public(self):
        conn = WebSocketConnection(WebSocketType.PUBLIC)
        assert conn is not None
        assert conn.ws_type == WebSocketType.PUBLIC

    def test_instantiation_private(self):
        creds = {"api_key": "test", "secret": "test", "passphrase": "test"}
        conn = WebSocketConnection(WebSocketType.PRIVATE, credentials=creds)
        assert conn is not None

    def test_get_endpoint(self):
        conn = WebSocketConnection(WebSocketType.PUBLIC)
        endpoint = conn.get_endpoint()
        assert isinstance(endpoint, str)
        assert len(endpoint) > 0

    def test_initial_state(self):
        conn = WebSocketConnection(WebSocketType.PUBLIC)
        assert conn.state == ConnectionState.DISCONNECTED
        assert conn.is_connected is False


@pytest.mark.skipif(not HAS_MODULE, reason="websocket_manager not available")
class TestWebSocketManager:
    def test_is_singleton(self):
        m1 = WebSocketManager()
        m2 = WebSocketManager()
        assert m1 is m2

    def test_get_public_ws(self):
        manager = WebSocketManager()
        conn = manager.get_public_ws()
        assert isinstance(conn, WebSocketConnection)

    def test_get_private_ws(self):
        manager = WebSocketManager()
        creds = {"api_key": "test", "secret": "test", "passphrase": "test"}
        conn = manager.get_private_ws(credentials=creds)
        assert isinstance(conn, WebSocketConnection)
