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
        req.state.is_admin = True  # #5467: list_users 现需 admin 守卫放行

        with patch("api.settings.get_user_service", return_value=mock_service):
            result = run_async(list_users(req=req))

        # 不应逐条调 get_credential（N+1）
        mock_service.get_credential.assert_not_called()
        # 不需要 get_all_credentials，service 已在 dict 中返回 is_admin
        mock_service.get_all_credentials.assert_not_called()
        # 验证返回数据包含 roles
        assert result["data"][0]["roles"] == ["admin"]
        assert result["data"][1]["roles"] == []


class TestUserGroupsN1Fix:
    """用户组列表 N+1 修复测试"""

    def test_does_not_call_count_members_per_group(self):
        """TDD Red: list_user_groups 不应逐组调 count_members"""

        mock_service = MagicMock()
        mock_service.list_groups.return_value = MagicMock(
            success=True,
            data=[
                {"uuid": "g-1", "name": "Group1", "description": "test"},
                {"uuid": "g-2", "name": "Group2", "description": "test"},
            ],
        )
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
