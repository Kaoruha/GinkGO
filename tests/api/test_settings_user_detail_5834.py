"""#5834: GET /settings/users/{uuid} 返回 405 Method Not Allowed。

根因：api/api/settings.py 注册了 list/POST/PUT{uuid}/DELETE{uuid}，唯独缺
GET /users/{uuid} 单条详情路由。Service 层 UserService.get_user_full_info 已实现
（聚合 basic + contacts + groups）。本测试覆盖端点装配层：
  - admin 守卫（_require_admin，与 PUT /users/{uuid} 一致）
  - 调 service.get_user_full_info(uuid)
  - not found → 404 错误码映射

参考 [[arch_api_test_root_main_shadow]]：端点测试走 from api.settings import 纯函数，
避开 api/main.py app 启动；sys.path.insert api/ 双层目录约定（同 test_settings_error_sanitization）。
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from ginkgo.data.services.base_service import ServiceResult

_api_dir = str(Path(__file__).parent.parent.parent / "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

from api.settings import get_user_detail  # noqa: E402  端点（待实现）


def run_async(coro):
    return asyncio.run(coro)


def _full_info(uuid_="u-1"):
    return {
        "uuid": uuid_,
        "username": "admin",
        "display_name": "Admin",
        "email": "a@t.com",
        "description": "",
        "user_type": "ADMIN",
        "is_active": True,
        "source": "LOCAL",
        "create_at": "2025-01-01T00:00:00",
        "update_at": None,
        "contacts": [],
        "groups": [],
    }


class TestGetUserDetail:
    """GET /settings/users/{uuid} 端点装配（#5834）"""

    def test_returns_full_info_on_success(self):
        """happy path: admin 请求已存在 uuid → 返 200 + full info dict，service 收到正确 uuid"""
        mock_service = MagicMock()
        # _require_admin → _resolve_is_admin → get_credential(is_admin=True)
        mock_service.get_credential.return_value = MagicMock(is_admin=True)
        full = _full_info("u-1")
        mock_service.get_user_full_info.return_value = ServiceResult.success(data=full, message="ok")

        req = MagicMock()
        req.state.user_uuid = "u-admin"

        with patch("api.settings.get_user_service", return_value=mock_service):
            result = run_async(get_user_detail(req=req, uuid="u-1"))

        mock_service.get_user_full_info.assert_called_once_with("u-1")
        assert result["data"] == full

    def test_not_found_returns_404(self):
        """uuid 不存在 → service 返 error('User not found') → 端点 404"""
        mock_service = MagicMock()
        mock_service.get_credential.return_value = MagicMock(is_admin=True)
        mock_service.get_user_full_info.return_value = ServiceResult.error(
            "User not found: u-missing", message="User does not exist"
        )

        req = MagicMock()
        req.state.user_uuid = "u-admin"

        with patch("api.settings.get_user_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(get_user_detail(req=req, uuid="u-missing"))

        assert exc.value.status_code == 404
        assert exc.value.detail == "User not found"

    def test_requires_admin(self):
        """非 admin 请求 → _require_admin 抛 403，service.get_user_full_info 不被调用"""
        mock_service = MagicMock()
        # 当前用户非 admin（fail-closed）
        mock_service.get_credential.return_value = MagicMock(is_admin=False)

        req = MagicMock()
        req.state.user_uuid = "u-ordinary"

        with patch("api.settings.get_user_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(get_user_detail(req=req, uuid="u-1"))

        assert exc.value.status_code == 403
        mock_service.get_user_full_info.assert_not_called()
