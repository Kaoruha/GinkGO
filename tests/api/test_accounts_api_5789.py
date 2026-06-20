"""
#5789: PUT /accounts/{id} 的 status 字段应透传给 service 实际生效

表象: PUT /accounts/{id} {"status":"enabled"} 返回成功但状态未变更。
根因: UpdateLiveAccountRequest 无 status 字段 + handler 不透传。
契约: handler 收到 status 时必须传给 service.update_account。

注: api/ 非 Python 包(无 __init__.py), 经 tests/api/conftest 的 api_modules
fixture 临时加入 sys.path, 故 import 须延迟到测试函数内。
"""

import asyncio
from unittest.mock import Mock


def test_put_account_handler_passes_status(api_modules, monkeypatch):
    """PUT /accounts/{id} handler 应将 status 透传给 service.update_account。"""
    from api import accounts as accounts_api
    from models.accounts import UpdateLiveAccountRequest, AccountStatus

    mock_service = Mock()
    mock_service.update_account.return_value = {
        "success": True,
        "data": {"uuid": "test-uuid"},
        "message": "Account updated successfully",
    }
    monkeypatch.setattr(accounts_api, "get_live_account_service", lambda: mock_service)

    # model 必须接受 status 字段（#5789 修复后）
    data = UpdateLiveAccountRequest(status=AccountStatus.ENABLED)
    asyncio.run(accounts_api.update_account("test-uuid", data))

    # handler 必须把 status 透传给 service
    mock_service.update_account.assert_called_once()
    call_kwargs = mock_service.update_account.call_args.kwargs
    assert call_kwargs.get("status") == AccountStatus.ENABLED
