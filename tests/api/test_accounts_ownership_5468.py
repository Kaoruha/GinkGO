"""#5468: 实盘账户 CRUD 端点 ownership 校验。

get_account/update_account/delete_account 三端点此前按 UUID 直接操作，
任意登录用户可读/改/删他人实盘账户（含脱敏前可能接触的凭据）。
本测试验证端点层 ownership 校验：非 owner → BusinessError(403)，owner 正常。

绕过 TestClient（arch_api_test_root_main_shadow）：直接 asyncio.run 端点，
req 用 SimpleNamespace 模拟 JWT 中间件注入 request.state.user_id。
"""
import asyncio
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from api.accounts import (
    get_account,
    update_account,
    delete_account,
    _require_account_ownership,
)
from core.exceptions import BusinessError


def _make_req(user_id):
    """模拟 JWT 中间件注入的 request.state.user_id（accounts 模块语义）。"""
    return SimpleNamespace(state=SimpleNamespace(user_id=user_id))


def _mock_account_data(owner_id, uuid="acc-1"):
    """service.get_account_by_uuid 返回 result['data']（to_dict，含 user_id）。"""
    return {
        "uuid": uuid,
        "user_id": owner_id,
        "exchange": "SIM",
        "name": "test-account",
        "status": "ACTIVE",
    }


def _patch_service(get_data=None, update_data=None, delete_success=True):
    """配置 mock live_account_service。

    get_data: get_account_by_uuid 返回的 data（None=not found）
    update_data: update_account 返回的 data
    delete_success: delete_account 是否成功

    用 @contextmanager yield svc，使 ``with _patch_service(...) as svc:`` 绑定
    端点实际调用的 service mock（而非 get_live_account_service 工厂 mock），
    断言 svc.xxx 才对应端点内 ``service.xxx`` 调用。
    """
    svc = MagicMock()
    get_result = {"success": bool(get_data), "data": get_data}
    update_result = {"success": bool(update_data), "data": update_data}
    delete_result = {"success": delete_success, "data": None}
    svc.get_account_by_uuid.return_value = get_result
    svc.update_account.return_value = update_result
    svc.delete_account.return_value = delete_result

    @contextmanager
    def _cm():
        with patch("api.accounts.get_live_account_service", return_value=svc):
            yield svc

    return _cm()


class TestRequireAccountOwnership:
    """#5468 helper: 校验 account 归属。"""

    def test_non_owner_raises_business_error_403(self):
        """非 owner → BusinessError(code=403, status_code=403)。"""
        account = _mock_account_data(owner_id="owner-x")
        with pytest.raises(BusinessError) as exc:
            _require_account_ownership(account, "attacker-y")
        assert exc.value.status_code == 403

    def test_owner_passes_without_raising(self):
        """owner → 不抛。"""
        account = _mock_account_data(owner_id="owner-x")
        _require_account_ownership(account, "owner-x")  # 不抛即通过


class TestGetAccountEndpointOwnership:
    """get_account 端点接线 ownership 校验（#5468 AC1/AC2）。"""

    def test_non_owner_forbidden(self):
        """非 owner 请求他人账户 → BusinessError(403)，不返回数据。"""
        account = _mock_account_data(owner_id="owner-x")
        with _patch_service(get_data=account):
            with pytest.raises(BusinessError) as exc:
                asyncio.run(get_account("acc-1", _make_req("attacker-y")))
        assert exc.value.status_code == 403

    def test_owner_retrieves_account(self):
        """owner → 不抛 403，正常返回。"""
        account = _mock_account_data(owner_id="owner-x")
        with _patch_service(get_data=account) as svc:
            resp = asyncio.run(get_account("acc-1", _make_req("owner-x")))
        svc.get_account_by_uuid.assert_called_once_with("acc-1")
        assert resp is not None


class TestUpdateAccountEndpointOwnership:
    """update_account 端点接线 ownership 校验（#5468 AC1/AC2）。"""

    def test_non_owner_forbidden_no_mutation(self):
        """非 owner 改他人账户 → 403，且 service.update_account 不被调用。"""
        account = _mock_account_data(owner_id="owner-x")
        data = MagicMock(name="UpdateLiveAccountRequest")
        with _patch_service(get_data=account) as svc:
            with pytest.raises(BusinessError) as exc:
                asyncio.run(update_account("acc-1", data, _make_req("attacker-y")))
        assert exc.value.status_code == 403
        svc.update_account.assert_not_called()


class TestDeleteAccountEndpointOwnership:
    """delete_account 端点接线 ownership 校验（#5468 AC1/AC2）。"""

    def test_non_owner_forbidden_no_deletion(self):
        """非 owner 删他人账户 → 403，且 service.delete_account 不被调用。"""
        account = _mock_account_data(owner_id="owner-x")
        with _patch_service(get_data=account) as svc:
            with pytest.raises(BusinessError) as exc:
                asyncio.run(delete_account("acc-1", _make_req("attacker-y")))
        assert exc.value.status_code == 403
        svc.delete_account.assert_not_called()
