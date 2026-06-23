# Issue: #5625 — GET /api/v1/user-groups 空响应/500；#5601 — POST 创建空响应；#6235 — 统一 user 版
# Upstream: api.api.settings.list_user_groups / create_user_group
# Downstream: ginkgo.user.services.user_group_service.UserGroupService（#6235 统一，容器注入）
# Role: 验证 user-groups 端点契约（list 迭代 + count_all_members 批量；端点 dict/list 双兼容）

"""
user-groups 端点契约测试（data 版本，#6227）

端点 get_user_group_service() 直接实例化 data 版 UserGroupService，其契约：
1. list_groups() 返回 list[dict]（非 {groups,count} dict）
2. count_all_members() 返回 {uuid: count} dict（一次 GROUP BY 批量，避免 N+1）
3. update_group(uuid, **updates) 存在（PUT 不再 AttributeError）
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
            data=[make_group("g1", "admins")]  # data 版返回 list
        )
        mock_svc.count_all_members.return_value = {"g1": 2}  # data 版批量成员数

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
            data=[]  # data 版返回 list，无重名
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
