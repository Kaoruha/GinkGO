"""deploy handler 的 deployment.changed WS 广播单测（ADR-046）。"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import websocket.events as events_mod


def _fake_saga(success: bool, data=None, error="boom"):
    saga = SimpleNamespace()
    saga.error = error
    saga.steps = [SimpleNamespace(result=SimpleNamespace(data=data if data is not None else {}))]

    async def _execute():
        return success

    saga.execute = _execute
    return saga


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.unit
def test_deploy_success_broadcasts_deployed():
    """成功路径：广播 deployment.changed，status 取 deploy_data.status。"""
    calls = []

    async def _fake_broadcast(event, entity, id, status=None, data=None):
        calls.append({"event": event, "id": id, "status": status, "data": data})

    req_data = {"portfolio_id": "pf-1", "mode": "paper"}
    from api.deployment import DeployRequest

    req = DeployRequest(**req_data)

    with patch("services.saga_transaction.PortfolioSagaFactory") as factory:
        factory.deploy_saga.return_value = _fake_saga(
            True, data={"uuid": "dep-1", "status": "DEPLOYED"})
        with patch.object(events_mod, "broadcast_event", _fake_broadcast):
            resp = _run(__import__("api.deployment", fromlist=["deploy"]).deploy(req))

    assert resp["data"]["uuid"] == "dep-1"
    assert len(calls) == 1
    assert calls[0]["event"] == "deployment.changed"
    assert calls[0]["id"] == "dep-1"
    assert calls[0]["status"] == "deployed"  # 归一小写
    assert calls[0]["data"]["mode"] == "paper"


@pytest.mark.unit
def test_deploy_failure_broadcasts_failed_and_raises():
    """失败路径：先广播 failed 再抛 BusinessError。"""
    calls = []

    async def _fake_broadcast(event, entity, id, status=None, data=None):
        calls.append({"event": event, "id": id, "status": status, "data": data})

    from api.deployment import DeployRequest
    from core.exceptions import BusinessError

    req = DeployRequest(portfolio_id="pf-2", mode="paper")

    with patch("services.saga_transaction.PortfolioSagaFactory") as factory:
        factory.deploy_saga.return_value = _fake_saga(False)
        with patch.object(events_mod, "broadcast_event", _fake_broadcast):
            with pytest.raises(BusinessError, match="部署失败"):
                _run(__import__("api.deployment", fromlist=["deploy"]).deploy(req))

    assert len(calls) == 1
    assert calls[0]["status"] == "failed"
    assert calls[0]["id"] == "pf-2"  # 无 deployment 记录时回退 portfolio_id
    assert "error" in calls[0]["data"]


@pytest.mark.unit
def test_broadcast_failure_never_fails_deploy():
    """WS 广播异常不影响部署结果（try/except 兜底）。"""
    from api.deployment import DeployRequest

    req = DeployRequest(portfolio_id="pf-3", mode="paper")

    async def _boom(*args, **kwargs):
        raise RuntimeError("ws down")

    with patch("services.saga_transaction.PortfolioSagaFactory") as factory:
        factory.deploy_saga.return_value = _fake_saga(True, data={"uuid": "dep-3"})
        with patch.object(events_mod, "broadcast_event", _boom):
            resp = _run(__import__("api.deployment", fromlist=["deploy"]).deploy(req))

    assert resp["data"]["uuid"] == "dep-3"
