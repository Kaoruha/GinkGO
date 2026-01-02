# Upstream: SC-005 性能要求 (用户软删除级联操作响应时间 < 100ms)
# Downstream: tasks.md T186 验证
# Role: 性能验证测试 - 验证用户软删除级联操作满足性能要求

"""
Performance verification test for SC-005: User cascade delete latency.

SC-005 Requirement: 用户软删除级联操作响应时间 < 100ms

Test Strategy:
1. 创建用户及其关联数据（联系方式、用户组映射）
2. 执行软删除操作
3. 验证级联删除生效
4. 测量响应时间
5. 验证响应时间 < 100ms
"""

import pytest
import time

from ginkgo.enums import USER_TYPES, CONTACT_TYPES


@pytest.mark.integration
@pytest.mark.performance
class TestSC005CascadeDeletePerformance:
    """SC-005: 用户软删除级联操作响应时间 < 100ms"""

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

    def test_sc005_cascade_delete_latency(self):
        """
        SC-005: 验证用户软删除级联操作响应时间 < 100ms

        测试步骤：
        1. 创建用户及其关联数据
        2. 执行软删除操作
        3. 测量响应时间
        4. 验证级联删除生效
        5. 验证响应时间 < 100ms
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-005 Performance Test: Cascade Delete Latency")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 步骤 1: 创建测试用户和关联数据
        print(f"\nStep 1: Creating test user with associated data...")

        user_result = user_service.add_user(
            name=f"test_cascade_{unique_id}",
            user_type=USER_TYPES.PERSON,
            description=f"Cascade delete test user {unique_id}"
        )
        assert user_result.is_success, f"Failed to create user: {user_result.error}"
        user_uuid = user_result.data["uuid"]

        # 创建联系方式
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.EMAIL,
            address=f"test_{unique_id}@example.com",
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success, f"Failed to create contact: {contact_result.error}"

        # 创建用户组
        group_result = user_group_service.create_group(
            name=f"test_group_{unique_id}",
            description=f"Test group {unique_id}"
        )
        assert group_result.is_success, f"Failed to create group: {group_result.error}"
        group_uuid = group_result.data["uuid"]

        # 添加用户到组
        mapping_result = user_group_service.add_user_to_group(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )
        assert mapping_result.is_success, f"Failed to add user to group: {mapping_result.error}"

        print(f"  User created: {user_uuid}")
        print(f"  Contact created")
        print(f"  Group created: {group_uuid}")
        print(f"  Mapping created")

        # 步骤 2: 执行软删除操作并测量时间
        print(f"\nStep 2: Performing cascade delete...")

        start_time = time.time()
        delete_result = user_service.remove_user(user_uuid=user_uuid)
        delete_latency = (time.time() - start_time) * 1000  # 转换为毫秒

        assert delete_result.is_success, f"Failed to delete user: {delete_result.error}"

        print(f"  Delete completed in {delete_latency:.2f}ms")

        # 步骤 3: 验证级联删除生效
        print(f"\nStep 3: Verifying cascade deletion...")

        # 验证用户被标记为删除
        user_check = user_service.get_user_by_uuid(user_uuid=user_uuid)
        assert user_check.is_success, "Failed to check user status"
        assert user_check.data.get("is_del", False) == True, "User should be marked as deleted"
        print(f"  ✅ User marked as deleted")

        # 验证联系方式被级联删除
        contacts_result = user_service.get_contacts(user_uuid=user_uuid)
        assert contacts_result.is_success, "Failed to check contacts"
        contacts = contacts_result.data.get("contacts", [])
        assert all(c.get("is_del", False) for c in contacts), "All contacts should be marked as deleted"
        print(f"  ✅ Contact marked as deleted")

        # 验证用户组映射被级联删除
        mapping_check = user_group_service.get_user_groups(user_uuid=user_uuid)
        assert mapping_check.is_success, "Failed to check user groups"
        mappings = mapping_check.data.get("groups", [])
        assert all(m.get("is_del", False) for m in mappings), "All mappings should be marked as deleted"
        print(f"  ✅ Group mapping marked as deleted")

        # 步骤 4: 输出结果
        print("\n" + "="*70)
        print("SC-005 Cascade Delete Results")
        print("="*70)
        print(f"Delete Latency:        {delete_latency:.2f}ms")
        print(f"Requirement:           < 100ms")

        if delete_latency < 100:
            print(f"\nResult:                ✅ PASS (Latency = {delete_latency:.2f}ms)")
        else:
            print(f"\nResult:                ❌ FAIL (Latency = {delete_latency:.2f}ms)")

        print("="*70)

        # 验证响应时间 < 100ms
        assert delete_latency < 100, f"SC-005 FAILED: Delete latency {delete_latency:.2f}ms >= 100ms"

    def test_sc005_multiple_cascade_deletes(self):
        """
        SC-005: 验证多次级联删除的性能一致性

        测试步骤：
        1. 执行 10 次级联删除操作
        2. 记录每次操作的响应时间
        3. 验证所有操作都 < 100ms
        4. 计算平均响应时间
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()
        user_group_service = service_hub.data.user_group_service()

        print("\n" + "="*70)
        print("SC-005 Multiple Cascade Delete Test")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        num_tests = 10
        latencies = []

        # 创建并删除多个用户
        for i in range(num_tests):
            # 创建用户
            user_result = user_service.add_user(
                name=f"test_multi_cascade_{unique_id}_{i}",
                user_type=USER_TYPES.PERSON,
                description=f"Multi cascade test user {i}"
            )
            assert user_result.is_success
            user_uuid = user_result.data["uuid"]

            # 创建联系方式
            user_service.add_contact(
                user_uuid=user_uuid,
                contact_type=CONTACT_TYPES.EMAIL,
                address=f"test_{unique_id}_{i}@example.com",
                is_primary=True,
                is_active=True
            )

            # 执行删除并测量时间
            start_time = time.time()
            delete_result = user_service.remove_user(user_uuid=user_uuid)
            latency = (time.time() - start_time) * 1000

            assert delete_result.is_success, f"Delete {i} failed: {delete_result.error}"
            latencies.append(latency)

            print(f"  Test {i+1}/{num_tests}: {latency:.2f}ms")

        # 计算统计信息
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)

        print("\n" + "="*70)
        print("SC-005 Multiple Delete Results")
        print("="*70)
        print(f"Number of Tests:       {num_tests}")
        print(f"Average Latency:       {avg_latency:.2f}ms")
        print(f"Max Latency:           {max_latency:.2f}ms")
        print(f"Min Latency:           {min_latency:.2f}ms")
        print(f"Requirement:           < 100ms")

        if max_latency < 100:
            print(f"\nResult:                ✅ PASS (All operations < 100ms)")
        else:
            print(f"\nResult:                ❌ FAIL (Some operations >= 100ms)")

        print("="*70)

        # 验证所有操作都 < 100ms
        assert max(latencies) < 100, f"SC-005 FAILED: Max latency {max_latency:.2f}ms >= 100ms"
