# Issue #5625: settings user-groups 端点适配 UserGroupService 真实契约
# Upstream: api.api.settings.list_user_groups / create_user_group / update_user_group
# Downstream: UserGroupService.list_groups
# Role: 验证端点按 service 真实返回结构 {"groups":[...],"count":N} 解包，且不传 is_del

"""
#5625 回归测试：settings user-groups 端点不可用。

根因1：端点 ``list_groups(is_del=False)``，但 UserGroupService.list_groups 签名为
``(is_active, limit)`` 无 is_del → TypeError。
根因2：端点把 ``result.data``（实为 ``{"groups":[...],"count":N}`` 字典）当列表遍历，
取 ``group_data["uuid"]`` → 字符串索引 TypeError。
两者叠加致 ``GET /user-groups`` 500、``POST/PUT`` 冲突检查崩。

注意：test_settings_n_plus_1.py 旧 mock 把 data 设成列表（不符 service 契约），
掩盖了根因2，本测试用真实字典结构复现。
"""
import asyncio

import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


def _groups_result(groups):
    """模拟 UserGroupService.list_groups 真实返回结构（data 为字典）。"""
    return MagicMock(success=True, data={"groups": groups, "count": len(groups)})


class TestListUserGroupsContract:
    """GET /user-groups 端点契约测试。"""

    def test_returns_code_0_with_group_list(self):
        """list_user_groups 返回 code=0 + 组列表（不再 500，#5625）。"""
        mock_service = MagicMock()
        mock_service.list_groups.return_value = _groups_result([
            {"uuid": "g-1", "name": "Group1", "description": "test"},
        ])
        mock_service.count_all_members.return_value = {"g-1": 3}

        from api.settings import list_user_groups

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            result = run_async(list_user_groups())

        assert result["code"] == 0
        assert len(result["data"]) == 1
        assert result["data"][0]["uuid"] == "g-1"
        assert result["data"][0]["user_count"] == 3


class TestListUserGroupsParams:
    """GET /user-groups 参数契约：不向 service 传 is_del。"""

    def test_list_groups_called_without_is_del(self):
        """端点不应向 list_groups 传 is_del（service 签名无此参数，#5625）。"""
        mock_service = MagicMock()
        mock_service.list_groups.return_value = _groups_result([])
        mock_service.count_all_members.return_value = {}

        from api.settings import list_user_groups

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            run_async(list_user_groups())

        mock_service.list_groups.assert_called_once_with()


class TestCreateUserGroupContract:
    """POST /user-groups 端点契约测试。"""

    def _req(self, name="test", description="desc"):
        req = MagicMock()
        req.name = name
        req.description = description
        req.permissions = []
        return req

    def test_create_returns_code_0_when_name_not_taken(self):
        """无重名时 create 返回 code=0 + 新组数据（#5625）。"""
        mock_service = MagicMock()
        mock_service.list_groups.return_value = _groups_result([])
        mock_service.create_group.return_value = MagicMock(
            success=True,
            data={"uuid": "g-new", "name": "test", "description": "desc"},
        )

        from api.settings import create_user_group

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            result = run_async(create_user_group(self._req()))

        assert result["code"] == 0
        assert result["data"]["uuid"] == "g-new"

    def test_create_raises_409_when_name_taken(self):
        """重名时抛 409（不再因解包崩成 500，#5625）。"""
        from fastapi import HTTPException

        mock_service = MagicMock()
        mock_service.list_groups.return_value = _groups_result([
            {"uuid": "g-old", "name": "test", "description": ""},
        ])

        from api.settings import create_user_group

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(create_user_group(self._req(name="test")))

        assert exc.value.status_code == 409


class TestUpdateUserGroupContract:
    """PUT /user-groups/{uuid} 端点契约测试。"""

    def test_update_raises_409_when_name_conflicts_other_group(self):
        """改名与他组冲突抛 409（不再因解包崩成 500，#5625）。"""
        from fastapi import HTTPException

        mock_service = MagicMock()
        mock_service.list_groups.return_value = _groups_result([
            {"uuid": "g-other", "name": "taken", "description": ""},
        ])

        data = MagicMock()
        data.name = "taken"
        data.description = None

        from api.settings import update_user_group

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            with pytest.raises(HTTPException) as exc:
                run_async(update_user_group("g-self", data))

        assert exc.value.status_code == 409
