# Issue: settings.py N+1 查询问题
# Upstream: api.api.settings.list_users, list_user_groups
# Downstream: UserService, UserGroupService
# Role: 验证用户列表和用户组列表使用批量查询而非 N+1

"""
settings N+1 查询修复测试

验证 list_users / list_user_groups 使用批量查询，
不再逐条查询凭证或成员数。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, call

from ginkgo.user.services.user_group_service import UserGroupService
from ginkgo.data.services.base_service import ServiceResult


def run_async(coro):
    return asyncio.run(coro)


class TestUsersN1Fix:
    """用户列表 N+1 修复测试"""

    def test_does_not_call_get_credential_per_user(self):
        """list_users 不应逐条调 get_credential，service 返回的 dict 已包含 is_admin"""

        mock_service = MagicMock()
        mock_service.list_users.return_value = MagicMock(
            success=True,
            data=[
                {"uuid": "u-1", "username": "admin", "display_name": "Admin",
                 "email": "a@t.com", "is_admin": True, "is_active": True,
                 "created_at": "2025-01-01T00:00:00Z"},
                {"uuid": "u-2", "username": "user2", "display_name": "User2",
                 "email": "b@t.com", "is_admin": False, "is_active": True,
                 "created_at": "2025-01-01T00:00:00Z"},
            ],
        )

        from api.settings import list_users

        req = MagicMock()
        req.state.user_uuid = "u-admin"  # #5467 review: 守卫按 DB 校验 is_admin
        mock_service.get_credential.return_value = MagicMock(is_admin=True)

        with patch("api.settings.get_user_service", return_value=mock_service):
            result = run_async(list_users(req=req))

        # #5467 review: _require_admin 鉴权调 get_credential 恰 1 次（O(1)，非 N+1）；
        # 业务层不得逐条查每个用户的凭证（N+1 才是问题）
        assert mock_service.get_credential.call_count == 1
        # 不需要 get_all_credentials，service 已在 dict 中返回 is_admin
        mock_service.get_all_credentials.assert_not_called()
        # 验证返回数据包含 roles
        assert result["data"][0]["roles"] == ["admin"]
        assert result["data"][1]["roles"] == []


class TestUserGroupsN1Fix:
    """用户组列表 N+1 修复测试"""

    def test_does_not_call_count_members_per_group(self):
        """TDD Red: list_user_groups 不应逐组调 count_members"""

        # #5625 review: spec 强制 mock 只暴露 UserGroupService 真实方法；
        # data 那份 list_groups 返回 ServiceResult，data 为 list（非字典）
        mock_service = MagicMock(spec=UserGroupService)
        mock_service.list_groups.return_value = ServiceResult.success([
            {"uuid": "g-1", "name": "Group1", "description": "test"},
            {"uuid": "g-2", "name": "Group2", "description": "test"},
        ])
        mock_service.count_all_members.return_value = {
            "g-1": 5,
            "g-2": 3,
        }

        from api.settings import list_user_groups

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            result = run_async(list_user_groups())

        # 不应逐组调 count_members（N+1）
        mock_service.count_members.assert_not_called()
        mock_service.count_all_members.assert_called_once()
