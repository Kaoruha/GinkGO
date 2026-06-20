# Issue: #5625 — GET /api/v1/user-groups 空响应/500；#5601 — POST 创建空响应
# Upstream: api.api.settings.list_user_groups / create_user_group
# Downstream: ginkgo.user.services.user_group_service.UserGroupService（user 版本）
# Role: 验证 user-groups 端点适配 user 版本 UserGroupService 的方法签名与返回结构

"""
user-groups 端点适配测试

根因（端点按 data 版本 UserGroupService 写，但容器注入的是 user 版本）：
1. list_groups(is_del=False) → user 版本签名 list_groups(is_active, limit)，无 is_del 参数 → TypeError
2. result.data 当 list 迭代 → user 版本返回 {groups, count} dict，迭代 dict keys → str 索引 TypeError
3. count_all_members() → user 版本无此方法 → AttributeError

适配 user 版本：list_groups() 取 data["groups"]，user_count 逐组 get_group_members() 取 count。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.base_service import ServiceResult


def run_async(coro):
    return asyncio.run(coro)


def make_group(uuid="g1", name="admins", description="d", is_active=True):
    return {"uuid": uuid, "name": name, "description": description, "is_active": is_active}


class TestUserGroupsEndpoint:
    """#5625 #5601: user-groups 端点适配 user 版本 UserGroupService"""

    def test_list_returns_groups(self):
        """TDD Red: GET /user-groups 返回实际组列表（不抛 TypeError / 不空）"""
        mock_svc = MagicMock()
        mock_svc.list_groups.return_value = ServiceResult.success(
            data={"groups": [make_group("g1", "admins")], "count": 1}
        )
        mock_svc.get_group_members.return_value = ServiceResult.success(
            data={"members": [{}, {}], "count": 2}
        )

        from api.settings import list_user_groups

        with patch("api.settings.get_user_group_service", return_value=mock_svc):
            result = run_async(list_user_groups())

        # 修复前：list_groups(is_del=False) TypeError → HTTPException 500
        assert result.get("code") == 0
        assert len(result["data"]) == 1
        assert result["data"][0]["name"] == "admins"
        assert result["data"][0]["user_count"] == 2

    def test_create_returns_created_group(self):
        """TDD Red: POST /user-groups 返回创建的组（不抛 TypeError / 不空）"""
        mock_svc = MagicMock()
        mock_svc.list_groups.return_value = ServiceResult.success(
            data={"groups": [], "count": 0}  # 无重名
        )
        mock_svc.create_group.return_value = ServiceResult.success(
            data={"uuid": "g-new", "name": "test-group"}
        )

        from api.settings import create_user_group

        # UserGroupCreate schema 字段：用 MagicMock 满足属性访问
        payload = MagicMock()
        payload.name = "test-group"
        payload.description = "desc"
        payload.permissions = []

        with patch("api.settings.get_user_group_service", return_value=mock_svc):
            result = run_async(create_user_group(payload))

        # 修复前：list_groups(is_del=False) TypeError → HTTPException 500
        assert result.get("code") == 0
        assert result["data"]["uuid"] == "g-new"
