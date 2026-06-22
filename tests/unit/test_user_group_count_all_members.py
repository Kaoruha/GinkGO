"""
#5675: ``UserGroupService.count_all_members()`` 字段错配测试。

根因：``count_all_members`` 用 ``model.group_id``（user_group_service.py:139,141），
但 ``MUserGroupMapping`` 模型字段实为 ``group_uuid``（model_user_group_mapping.py:34）。
``AttributeError`` 被 service 的 ``try/except`` 吞掉 → 返回 ``{}`` → 端点 ``member_count`` 永远 0。

漏测原因：端点测试 ``test_settings_user_groups.py:53`` 用
``mock_service.count_all_members.return_value = {"g-1": 3}`` mock 掉了 service 层，
掩盖了此 bug。本测试直连 Test DB 验证 service 真实行为（不 mock）。
"""
import pytest

from ginkgo.data.services.user_group_service import UserGroupService


@pytest.mark.integration
class TestCountAllMembersFieldMapping:
    """count_all_members 字段名错配回归（#5675）"""

    def test_returns_non_empty_dict_when_mappings_exist(self):
        """Test DB 存在 mappings 时，count_all_members 必须返回非空 dict。

        修复前：``model.group_id`` 不存在 → AttributeError 被吞 → 返回 ``{}``。
        """
        svc = UserGroupService()
        counts = svc.count_all_members()

        assert isinstance(counts, dict)
        assert len(counts) > 0, (
            "count_all_members 返回空——端点 member_count 将永远 0。"
            "检查 group_by 字段名是否与 MUserGroupMapping 一致（group_uuid 非 group_id）"
        )

    def test_keys_are_actual_group_uuids(self):
        """返回的键必须是真实 group_uuid，能与 list_groups 的 group 对上。

        修复前即使返回非空，键也来自不存在的 group_id，无法匹配。
        """
        svc = UserGroupService()
        counts = svc.count_all_members()
        groups = svc.group_crud.find(filters={"is_del": False})
        group_uuids = {g.uuid for g in groups}

        # 至少有一个 count 键能匹配到真实 group_uuid
        matched = [k for k in counts.keys() if k in group_uuids]
        assert len(matched) > 0, (
            f"count_all_members 的键 {list(counts.keys())[:3]} 不匹配任何真实 group_uuid"
        )
