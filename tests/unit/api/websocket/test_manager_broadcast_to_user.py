"""ConnectionManager.broadcast_to_user 单测：定向、回退全员、异常清理。"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import pytest

from websocket.manager import ConnectionManager


class _FakeWebSocket:
    """最小 WebSocket mock：记录 send_text，可注入发送失败。"""

    def __init__(self, fail_send=False):
        self.sent = []
        self.fail_send = fail_send

    async def send_text(self, text):
        if self.fail_send:
            raise RuntimeError("connection closed")
        self.sent.append(text)


def _manager_with(*conns):
    """构造带 (conn, user_uuid) 注册的 manager。"""
    m = ConnectionManager()
    for conn, user_uuid in conns:
        m.active_connections.append(conn)
        m.connection_metadata[conn] = {"user_uuid": user_uuid, "topics": set()}
    return m


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_to_user_targets_only_matching():
    a, b, c = _FakeWebSocket(), _FakeWebSocket(), _FakeWebSocket()
    m = _manager_with((a, "user-a"), (b, "user-b"), (c, None))

    await m.broadcast_to_user(["user-a"], {"type": "event"}, fallback_all=False)

    assert len(a.sent) == 1
    assert b.sent == []
    assert c.sent == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_to_user_no_match_falls_back_to_all():
    a, b = _FakeWebSocket(), _FakeWebSocket()
    m = _manager_with((a, "user-a"), (b, "user-b"))

    await m.broadcast_to_user(["nobody"], {"type": "event"}, fallback_all=True)

    assert len(a.sent) == 1
    assert len(b.sent) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_to_user_no_match_no_fallback_sends_nothing():
    a = _FakeWebSocket()
    m = _manager_with((a, "user-a"))

    await m.broadcast_to_user(["nobody"], {"type": "event"}, fallback_all=False)

    assert a.sent == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_to_user_cleans_dead_connections():
    alive, dead = _FakeWebSocket(), _FakeWebSocket(fail_send=True)
    m = _manager_with((alive, "user-a"), (dead, "user-a"))

    await m.broadcast_to_user(["user-a"], {"type": "event"})

    assert len(alive.sent) == 1
    # 发送失败的连接被清理出活跃列表
    assert dead not in m.active_connections
    assert dead not in m.connection_metadata
