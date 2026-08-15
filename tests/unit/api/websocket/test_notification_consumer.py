"""NotificationConsumer._process_message 单测：定向、回退、level 归一。"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import asyncio
import uuid

import pytest

import services.notification_consumer as nc
from services.notification_consumer import NotificationConsumer


@pytest.fixture()
def captured():
    """捕获 broadcast_event_to_users 调用（模块属性 patch，_process_message 内即时可见）。"""
    calls = []

    async def _fake(user_uuids, event, entity, id, status=None, data=None):
        calls.append({"user_uuids": user_uuids, "event": event,
                      "entity": entity, "id": id, "data": data})

    original = nc.broadcast_event_to_users
    nc.broadcast_event_to_users = _fake
    yield calls
    nc.broadcast_event_to_users = original


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.unit
def test_user_addressed_notification(captured):
    _run(NotificationConsumer()._process_message({
        "message_type": "custom_fields",
        "user_uuids": ["user-a", "user-b"],
        "title": "T", "content": "hello",
        "level": "WARN", "module": "paper",
    }))

    assert len(captured) == 1
    assert captured[0]["user_uuids"] == ["user-a", "user-b"]
    assert captured[0]["event"] == "notification"
    assert captured[0]["data"]["level"] == "warn"  # 归一小写
    assert captured[0]["data"]["title"] == "T"


@pytest.mark.unit
def test_single_user_uuid_field(captured):
    """兼容只有单 user_uuid 字段的消息。"""
    _run(NotificationConsumer()._process_message({
        "user_uuid": "user-solo", "content": "x",
    }))

    assert captured[0]["user_uuids"] == ["user-solo"]


@pytest.mark.unit
def test_group_addressed_falls_back_empty_list(captured):
    """无 user_uuids（群发）→ 空列表，broadcast_to_user 内部回退全员。"""
    _run(NotificationConsumer()._process_message({
        "message_type": "custom_fields", "content": "broadcast",
    }))

    assert captured[0]["user_uuids"] == []


@pytest.mark.unit
def test_level_defaults_info(captured):
    _run(NotificationConsumer()._process_message({"content": "x"}))
    assert captured[0]["data"]["level"] == "info"


@pytest.mark.unit
def test_missing_message_id_generates_uuid(captured):
    _run(NotificationConsumer()._process_message({"content": "x"}))
    # 合法 uuid 即可
    uuid.UUID(captured[0]["id"])
