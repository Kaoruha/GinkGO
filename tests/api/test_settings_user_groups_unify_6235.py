# Issue #6235: 统一 UserGroupService 到 user 版（消除 data/user 双版本）
# Upstream: api.api.settings.list_user_groups
# Downstream: ginkgo.user.services.user_group_service.UserGroupService（容器装配的那份）
# Role: tracer bullet —— 端点走 container.user_group_service()（user 版）后，
#       user 版 service 须满足 list_groups（dict 契约）+ count_all_members（裸 dict 契约）。
#
# RED 驱动三件事：
#   1. user 版补 count_all_members（MagicMock(spec=UserGroupService) 强制，缺则 AttributeError）
#   2. settings.py 端点切 container.user_group_service()（patch api.settings.container 生效）
#   3. list_groups 解包适配 user 版 dict（data={"groups":[...],"count":N}，非 data 版裸 list）

import asyncio
from unittest.mock import patch, MagicMock

import pytest

from ginkgo.user.services.user_group_service import UserGroupService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    """连 test 库（Debug 模式），真实 service 冒烟隔离生产库。"""
    GCONF.set_debug(True)


class TestListUserGroupsUnify:
    """list_user_groups 端点统一到 user 版 service 的契约测试。"""

    def test_uses_container_user_version_service(self):
        """端点走 container.user_group_service()（user 版），list_groups 返 dict 解包适配。

        user 版 list_groups 返回 dict {"groups":[...],"count":N}（CLI 契约，与 data 版
        裸 list 不同）。端点须按 dict 解包；count_all_members 返裸 dict（端点 :785 直接用）。
        """
        mock_svc = MagicMock(spec=UserGroupService)
        # user 版 list_groups 返 dict（非 data 版裸 list）
        mock_svc.list_groups.return_value = ServiceResult.success(
            data={"groups": [{"uuid": "g-1", "name": "Group1", "description": "d"}], "count": 1}
        )
        # user 版须有 count_all_members（spec 强制；缺则 AttributeError = RED）
        mock_svc.count_all_members.return_value = {"g-1": 3}

        from api.settings import list_user_groups

        with patch("api.settings.container") as mock_container:
            mock_container.user_group_service.return_value = mock_svc
            result = asyncio.run(list_user_groups())

        assert result["code"] == 0
        assert len(result["data"]) == 1
        assert result["data"][0]["uuid"] == "g-1"
        assert result["data"][0]["user_count"] == 3
        mock_svc.list_groups.assert_called_once()
        mock_svc.count_all_members.assert_called_once()
