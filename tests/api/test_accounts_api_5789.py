"""
#5789: PUT /accounts/{id} 的 status 字段应透传给 service 实际生效

表象: PUT /accounts/{id} {"status":"enabled"} 返回成功但状态未变更。
根因: UpdateLiveAccountRequest 无 status 字段 + handler 不透传。
契约: handler 收到 status 时必须传给 service.update_account。

注: api/ 非 Python 包(无 __init__.py), 经 tests/api/conftest 的 api_modules
fixture 临时加入 sys.path, 故 import 须延迟到测试函数内。
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pydantic import ValidationError


def test_put_account_handler_passes_status(api_modules, monkeypatch):
    """PUT /accounts/{id} handler 应将 status 透传给 service.update_account。"""
    from api import accounts as accounts_api
    from models.accounts import UpdateLiveAccountRequest, AccountStatus

    mock_service = Mock()
    # #5468: ownership 前置校验先经 get_account_by_uuid 查归属
    mock_service.get_account_by_uuid.return_value = {
        "success": True,
        "data": {"uuid": "test-uuid", "user_id": "test-user"},
    }
    mock_service.update_account.return_value = {
        "success": True,
        "data": {"uuid": "test-uuid"},
        "message": "Account updated successfully",
    }
    monkeypatch.setattr(accounts_api, "get_live_account_service", lambda: mock_service)

    # model 必须接受 status 字段（#5789 修复后）
    data = UpdateLiveAccountRequest(status=AccountStatus.ENABLED)
    # #5468: 端点新增 request 参数（ownership 校验需 request.state.user_id）
    req = SimpleNamespace(state=SimpleNamespace(user_id="test-user"))
    asyncio.run(accounts_api.update_account("test-uuid", data, req))

    # handler 必须把 status 透传给 service
    mock_service.update_account.assert_called_once()
    call_kwargs = mock_service.update_account.call_args.kwargs
    assert call_kwargs.get("status") == AccountStatus.ENABLED


def test_update_request_rejects_non_user_settable_status(api_modules):
    """#5789 / review #6213: PUT 仅允许 enabled/disabled。

    connecting/disconnected/error 是验证引擎派生态,禁止由 PUT 设置;
    model 应在边界拒绝,避免合法枚举进 service 才被 valid_statuses 拒。
    """
    from models.accounts import UpdateLiveAccountRequest, AccountStatus

    # 用户可设的两种状态仍合法
    UpdateLiveAccountRequest(status=AccountStatus.ENABLED)
    UpdateLiveAccountRequest(status=AccountStatus.DISABLED)
    UpdateLiveAccountRequest(status="enabled")
    UpdateLiveAccountRequest(status=None)

    # 派生态被边界拒绝
    for bad in (
        AccountStatus.CONNECTING,
        AccountStatus.DISCONNECTED,
        AccountStatus.ERROR,
        "connecting",
    ):
        with pytest.raises(ValidationError):
            UpdateLiveAccountRequest(status=bad)


def test_update_status_request_rejects_non_user_settable_status(api_modules):
    """PUT /accounts/{id}/status 同样只允许 enabled/disabled。

    该端点走 service.update_account_status(valid_statuses=[ENABLED,DISABLED]),
    且失败分支 raise NotFoundError —— 传 connecting 会被误导成"账号不存在"。
    model 应在边界拒绝派生态(422),与 UpdateLiveAccountRequest 一致。
    """
    from models.accounts import UpdateAccountStatusRequest, AccountStatus

    UpdateAccountStatusRequest(status=AccountStatus.ENABLED)
    UpdateAccountStatusRequest(status=AccountStatus.DISABLED)

    for bad in (
        AccountStatus.CONNECTING,
        AccountStatus.DISCONNECTED,
        AccountStatus.ERROR,
    ):
        with pytest.raises(ValidationError):
            UpdateAccountStatusRequest(status=bad)
