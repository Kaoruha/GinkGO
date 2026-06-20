# Issue #5625: settings user-groups 端点装配正确的 UserGroupService（data 那份）
# Upstream: api.api.settings.list_user_groups / create_user_group / update_user_group
# Downstream: ginkgo.data.services.user_group_service.UserGroupService
# Role: 验证端点装配的 service 具备端点所需全部方法（spec 强制），且按
#       list_groups 返回的 list 结构解包（不再误用字典 ["groups"]）。

"""
#5625 回归测试（review 修正版）：settings user-groups 端点不可用。

初版修复只处理 ``list_groups(is_del)`` TypeError 与 ``result.data`` 解包，但端点还调用
``count_all_members`` / ``update_group`` 等方法——这些只在
``ginkgo.data.services.user_group_service`` 上存在，而容器装配的
``ginkgo.user.services.user_group_service`` 不具备，致 ``AttributeError`` 仍 500。
MagicMock auto-truthy 掩盖了缺失方法。

本测试用 ``MagicMock(spec=UserGroupService)`` 强制 mock 只暴露真实方法，
返回值用真实 ``ServiceResult``，避免再次掩盖契约不匹配。
"""
import asyncio

import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.user_group_service import UserGroupService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    """连 test 库（Debug 模式），真实 service 冒烟隔离生产库。"""
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


def _groups_result(groups):
    """data 那份 list_groups 返回 ServiceResult，data 为 list（非字典）。"""
    return ServiceResult.success(list(groups))


class TestListUserGroupsContract:
    """GET /user-groups 端点契约测试。"""

    def test_returns_code_0_with_group_list(self):
        """list_user_groups 返回 code=0 + 组列表（不再 500，#5625）。"""
        mock_service = MagicMock(spec=UserGroupService)
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
        # spec 强制：端点调用的方法真实存在于 UserGroupService（否则 AttributeError）
        mock_service.count_all_members.assert_called_once()


class TestListUserGroupsParams:
    """GET /user-groups 参数契约：不向 service 传 is_del。"""

    def test_list_groups_called_without_is_del(self):
        """端点不应向 list_groups 传 is_del（service 签名 **filters，#5625）。"""
        mock_service = MagicMock(spec=UserGroupService)
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
        mock_service = MagicMock(spec=UserGroupService)
        mock_service.list_groups.return_value = _groups_result([])
        mock_service.create_group.return_value = ServiceResult.success(
            {"uuid": "g-new", "name": "test"}
        )

        from api.settings import create_user_group

        with patch("api.settings.get_user_group_service", return_value=mock_service):
            result = run_async(create_user_group(self._req()))

        assert result["code"] == 0
        assert result["data"]["uuid"] == "g-new"
        mock_service.create_group.assert_called_once()

    def test_create_raises_409_when_name_taken(self):
        """重名时抛 409（不再因解包崩成 500，#5625）。"""
        from fastapi import HTTPException

        mock_service = MagicMock(spec=UserGroupService)
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
        """改名与他组冲突抛 409（不再因缺失 update_group 崩成 500，#5625）。"""
        from fastapi import HTTPException

        mock_service = MagicMock(spec=UserGroupService)
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


class TestListUserGroupsRealService:
    """真实 service 冒烟（不 mock）：端点不再 AttributeError/解包 500（review 核心）。"""

    def test_list_user_groups_returns_code_0(self):
        """真实 DataUserGroupService 跑通端点，证明 #5625 修复有效（不靠 mock）。"""
        from api.settings import list_user_groups

        result = run_async(list_user_groups())

        assert result["code"] == 0
        assert isinstance(result["data"], list)
