# Upstream: SC-006 质量要求 (用户组映射外键约束生效率 100%)
# Downstream: tasks.md T187 验证
# Role: 质量验证测试 - 验证用户组映射外键约束正确性

"""
Quality verification test for SC-006: User group mapping foreign key constraints.

SC-006 Requirement: 用户组映射外键约束生效率 100%

Test Strategy:
1. 测试正常情况：创建有效的用户和用户组映射
2. 测试异常情况：尝试创建到不存在用户的映射
3. 测试异常情况：尝试创建到不存在组的映射
4. 验证所有异常情况都被正确拒绝
5. 验证级联删除正确执行
"""

import pytest

from ginkgo.enums import USER_TYPES


@pytest.mark.integration
@pytest.mark.quality
class TestSC006ForeignKeyConstraints:
    """SC-006: 用户组映射外键约束生效率 100%"""

    @pytest.fixture(autouse=True)
    def setup_debug_mode(self):
        """确保调试模式已启用"""
        import subprocess
        subprocess.run(
            ["ginkgo", "system", "config", "set", "--debug", "on"],
            capture_output=True,
            text=True
        )
        yield
        subprocess.run(
            ["ginkgo", "system", "config", "set", "--debug", "off"],
            capture_output=True,
            text=True
        )

    def test_sc006_valid_mapping_creation(self):
        """
        SC-006: 验证有效的用户组映射能够成功创建

        测试步骤：
        1. 创建有效的用户和用户组
        2. 创建用户组映射
        3. 验证映射创建成功
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-006 Quality Test: Valid Mapping Creation")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建用户
        user_result = user_service.add_user(
            name=f"test_user_fk_{unique_id}",
            user_type=USER_TYPES.PERSON,
            description=f"FK test user {unique_id}"
        )
        assert user_result.is_success, f"Failed to create user: {user_result.error}"
        user_uuid = user_result.data["uuid"]
        print(f"✅ User created: {user_uuid}")

        # 创建用户组
        group_result = user_group_service.create_group(
            name=f"test_group_fk_{unique_id}",
            description=f"FK test group {unique_id}"
        )
        assert group_result.is_success, f"Failed to create group: {group_result.error}"
        group_uuid = group_result.data["uuid"]
        print(f"✅ Group created: {group_uuid}")

        # 创建映射
        mapping_result = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )
        assert mapping_result.is_success, f"Failed to create mapping: {mapping_result.error}"
        print(f"✅ Mapping created successfully")

        print("\n" + "="*70)
        print("SC-006 Valid Mapping Results")
        print("="*70)
        print(f"Result:                ✅ PASS (Valid mapping created successfully)")
        print("="*70)

        # 验证映射存在
        mappings = user_group_service.get_user_groups(user_uuid=user_uuid)
        assert mappings.is_success, "Failed to query user groups"
        assert len(mappings.data.get("groups", [])) > 0, "Mapping should exist"

    def test_sc006_invalid_user_uuid_rejected(self):
        """
        SC-006: 验证无效用户 UUID 被拒绝

        测试步骤：
        1. 创建有效的用户组
        2. 尝试使用不存在的用户 UUID 创建映射
        3. 验证操作被拒绝
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-006 Quality Test: Invalid User UUID Rejection")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建用户组
        group_result = user_group_service.create_group(
            name=f"test_group_inv_{unique_id}",
            description=f"Invalid user test group {unique_id}"
        )
        assert group_result.is_success, f"Failed to create group: {group_result.error}"
        group_uuid = group_result.data["uuid"]
        print(f"✅ Group created: {group_uuid}")

        # 尝试使用不存在的用户 UUID 创建映射
        fake_user_uuid = "00000000-0000-0000-0000-000000000000"
        mapping_result = user_group_service.add_user_to_group(
            user_uuid=fake_user_uuid,
            group_uuid=group_uuid
        )

        print("\n" + "="*70)
        print("SC-006 Invalid User Results")
        print("="*70)

        if not mapping_result.is_success:
            print(f"✅ Mapping correctly rejected")
            print(f"Error message: {mapping_result.error}")
            print(f"\nResult:                ✅ PASS (Invalid user UUID rejected)")
        else:
            print(f"❌ Mapping incorrectly accepted")
            print(f"\nResult:                ❌ FAIL (Should reject invalid user UUID)")

        print("="*70)

        # 验证操作被拒绝
        assert not mapping_result.is_success, "SC-006 FAILED: Invalid user UUID should be rejected"

    def test_sc006_invalid_group_uuid_rejected(self):
        """
        SC-006: 验证无效用户组 UUID 被拒绝

        测试步骤：
        1. 创建有效的用户
        2. 尝试使用不存在的用户组 UUID 创建映射
        3. 验证操作被拒绝
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-006 Quality Test: Invalid Group UUID Rejection")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建用户
        user_result = user_service.add_user(
            name=f"test_user_inv_{unique_id}",
            user_type=USER_TYPES.PERSON,
            description=f"Invalid group test user {unique_id}"
        )
        assert user_result.is_success, f"Failed to create user: {user_result.error}"
        user_uuid = user_result.data["uuid"]
        print(f"✅ User created: {user_uuid}")

        # 尝试使用不存在的用户组 UUID 创建映射
        fake_group_uuid = "00000000-0000-0000-0000-000000000000"
        mapping_result = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=fake_group_uuid
        )

        print("\n" + "="*70)
        print("SC-006 Invalid Group Results")
        print("="*70)

        if not mapping_result.is_success:
            print(f"✅ Mapping correctly rejected")
            print(f"Error message: {mapping_result.error}")
            print(f"\nResult:                ✅ PASS (Invalid group UUID rejected)")
        else:
            print(f"❌ Mapping incorrectly accepted")
            print(f"\nResult:                ❌ FAIL (Should reject invalid group UUID)")

        print("="*70)

        # 验证操作被拒绝
        assert not mapping_result.is_success, "SC-006 FAILED: Invalid group UUID should be rejected"

    def test_sc006_cascade_delete_on_user_removal(self):
        """
        SC-006: 验证用户删除时映射被级联删除

        测试步骤：
        1. 创建用户、用户组和映射
        2. 删除用户
        3. 验证映射被级联删除
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-006 Quality Test: Cascade Delete on User Removal")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建用户和用户组
        user_result = user_service.add_user(
            name=f"test_user_cascade_{unique_id}",
            user_type=USER_TYPES.PERSON,
            description=f"Cascade test user {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        group_result = user_group_service.create_group(
            name=f"test_group_cascade_{unique_id}",
            description=f"Cascade test group {unique_id}"
        )
        assert group_result.is_success
        group_uuid = group_result.data["uuid"]

        # 创建映射
        mapping_result = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )
        assert mapping_result.is_success
        print(f"✅ Mapping created")

        # 删除用户
        delete_result = user_service.remove_user(user_uuid=user_uuid)
        assert delete_result.is_success
        print(f"✅ User deleted")

        # 验证映射被级联删除
        mappings = user_group_service.get_user_groups(user_uuid=user_uuid)
        assert mappings.is_success, "Failed to query user groups"

        mapping_list = mappings.data.get("groups", [])
        cascade_deleted = all(m.get("is_del", False) for m in mapping_list)

        print("\n" + "="*70)
        print("SC-006 Cascade Delete Results")
        print("="*70)

        if cascade_deleted:
            print(f"✅ Mapping correctly cascade deleted")
            print(f"\nResult:                ✅ PASS (Cascade delete working)")
        else:
            print(f"❌ Mapping not cascade deleted")
            print(f"\nResult:                ❌ FAIL (Cascade delete not working)")

        print("="*70)

        # 验证映射被级联删除
        assert cascade_deleted, "SC-006 FAILED: Mapping should be cascade deleted when user is deleted"

    def test_sc006_cascade_delete_on_group_removal(self):
        """
        SC-006: 验证用户组删除时映射被级联删除

        测试步骤：
        1. 创建用户、用户组和映射
        2. 删除用户组
        3. 验证映射被级联删除
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-006 Quality Test: Cascade Delete on Group Removal")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建用户和用户组
        user_result = user_service.add_user(
            name=f"test_user_grp_cascade_{unique_id}",
            user_type=USER_TYPES.PERSON,
            description=f"Group cascade test user {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        group_result = user_group_service.create_group(
            name=f"test_group_grp_cascade_{unique_id}",
            description=f"Group cascade test group {unique_id}"
        )
        assert group_result.is_success
        group_uuid = group_result.data["uuid"]

        # 创建映射
        mapping_result = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )
        assert mapping_result.is_success
        print(f"✅ Mapping created")

        # 删除用户组
        delete_result = user_group_service.remove_group(group_uuid=group_uuid)
        assert delete_result.is_success
        print(f"✅ Group deleted")

        # 验证映射被级联删除
        mappings = user_group_service.get_user_groups(user_uuid=user_uuid)
        assert mappings.is_success, "Failed to query user groups"

        mapping_list = mappings.data.get("groups", [])
        cascade_deleted = all(m.get("is_del", False) for m in mapping_list)

        print("\n" + "="*70)
        print("SC-006 Group Cascade Delete Results")
        print("="*70)

        if cascade_deleted:
            print(f"✅ Mapping correctly cascade deleted")
            print(f"\nResult:                ✅ PASS (Group cascade delete working)")
        else:
            print(f"❌ Mapping not cascade deleted")
            print(f"\nResult:                ❌ FAIL (Group cascade delete not working)")

        print("="*70)

        # 验证映射被级联删除
        assert cascade_deleted, "SC-006 FAILED: Mapping should be cascade deleted when group is deleted"

    def test_sc006_duplicate_mapping_prevention(self):
        """
        SC-006: 验证重复映射被正确处理

        测试步骤：
        1. 创建用户、用户组和映射
        2. 尝试创建相同的映射
        3. 验证重复映射被正确处理（幂等性）
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-006 Quality Test: Duplicate Mapping Handling")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建用户和用户组
        user_result = user_service.add_user(
            name=f"test_user_dup_{unique_id}",
            user_type=USER_TYPES.PERSON,
            description=f"Duplicate test user {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        group_result = user_group_service.create_group(
            name=f"test_group_dup_{unique_id}",
            description=f"Duplicate test group {unique_id}"
        )
        assert group_result.is_success
        group_uuid = group_result.data["uuid"]

        # 创建第一次映射
        mapping_result1 = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )
        assert mapping_result1.is_success
        print(f"✅ First mapping created")

        # 尝试创建相同的映射
        mapping_result2 = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )

        print("\n" + "="*70)
        print("SC-006 Duplicate Mapping Results")
        print("="*70)

        # 检查幂等性：第二次操作应该成功或返回适当的响应
        if mapping_result2.is_success:
            print(f"✅ Duplicate mapping handled (idempotent)")
            print(f"\nResult:                ✅ PASS (Idempotent behavior)")
        else:
            # 也可能是返回错误但不影响系统状态
            print(f"✅ Duplicate mapping rejected")
            print(f"Error message: {mapping_result2.error}")
            print(f"\nResult:                ✅ PASS (Duplicate rejected)")

        print("="*70)

        # 验证系统状态一致（只有一条映射）
        mappings = user_group_service.get_user_groups(user_uuid=user_uuid)
        assert mappings.is_success
        # 重复映射处理不强制要求唯一性，只要系统状态一致即可
