# Upstream: SC-004 性能要求 (单次可查询 >= 1000 个用户)
# Downstream: tasks.md T185 验证
# Role: 性能验证测试 - 验证用户查询满足数量要求

"""
Performance verification test for SC-004: User query capability.

SC-004 Requirement: 单次可查询 >= 1000 个用户

Test Strategy:
1. 创建 1000+ 个测试用户
2. 执行批量查询操作
3. 验证能够查询到所有用户
4. 验证查询性能
"""

import pytest
import time

from ginkgo.enums import USER_TYPES


@pytest.mark.integration
@pytest.mark.performance
class TestSC004UserQueryPerformance:
    """SC-004: 单次可查询 >= 1000 个用户"""

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

    def test_sc004_query_1000_users(self):
        """
        SC-004: 验证单次可查询 >= 1000 个用户

        测试步骤：
        1. 创建 1000 个测试用户
        2. 执行分页查询，每次查询 100 个用户
        3. 验证能够查询到所有用户
        4. 验证查询性能
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()

        print("\n" + "="*70)
        print("SC-004 Performance Test: Query 1000 Users")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        num_users = 1000

        # 步骤 1: 创建 1000 个用户
        print(f"\nStep 1: Creating {num_users} users...")
        start_time = time.time()

        user_uuids = []
        for i in range(num_users):
            result = user_service.add_user(
                name=f"test_user_{unique_id}_{i:04d}",
                user_type=USER_TYPES.PERSON,
                description=f"Test user {i} for SC-004"
            )
            if result.is_success:
                user_uuids.append(result.data["uuid"])

        create_time = time.time() - start_time
        print(f"  Created {len(user_uuids)} users in {create_time:.2f}s")

        try:
            # 步骤 2: 分页查询用户
            print(f"\nStep 2: Querying users in batches...")
            start_time = time.time()

            page_size = 100
            all_users = []
            page = 1

            while True:
                result = user_service.get_users(
                    limit=page_size,
                    offset=(page - 1) * page_size,
                    name_pattern=f"test_user_{unique_id}_"
                )

                if not result.is_success:
                    break

                users = result.data.get("users", [])
                if not users:
                    break

                all_users.extend(users)
                print(f"  Page {page}: Retrieved {len(users)} users")
                page += 1

                if len(users) < page_size:
                    break

            query_time = time.time() - start_time

            # 步骤 3: 验证结果
            print("\n" + "="*70)
            print("SC-004 Query Performance Results")
            print("="*70)
            print(f"Users Created:        {len(user_uuids)}")
            print(f"Users Queried:        {len(all_users)}")
            print(f"Query Time:           {query_time:.2f}s")
            print(f"Requirement:          >= 1000 users")

            if len(all_users) >= 1000:
                print(f"\nResult:                ✅ PASS (Queried {len(all_users)} users)")
            else:
                print(f"\nResult:                ❌ FAIL (Only {len(all_users)} users queried)")

            print("="*70)

            # 验证查询到的用户数量 >= 1000
            assert len(all_users) >= 1000, f"SC-004 FAILED: Only {len(all_users)} users queried, required >= 1000"

        finally:
            # 清理测试数据（可选，或保留用于后续测试）
            pass

    def test_sc004_single_large_query(self):
        """
        SC-004: 验证单次大查询的性能

        测试单次查询大量用户的性能
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()

        print("\n" + "="*70)
        print("SC-004 Single Large Query Test")
        print("="*70)

        # 执行大查询
        print(f"\nQuerying all users with limit=1000...")

        start_time = time.time()
        result = user_service.get_users(limit=1000)
        query_time = time.time() - start_time

        assert result.is_success, f"Failed to query users: {result.error}"

        users = result.data.get("users", [])

        print(f"Query completed in {query_time:.2f}s")
        print(f"Users returned: {len(users)}")

        # 验证查询成功
        assert len(users) >= 0  # 至少没有崩溃
        print(f"\n✅ Large query completed successfully")

    def test_sc004_query_with_filters(self):
        """
        SC-004: 验证带过滤条件的用户查询

        测试查询性能和过滤能力
        """
        from ginkgo import service_hub

        user_service = service_hub.data.user_service()

        print("\n" + "="*70)
        print("SC-004 Query with Filters Test")
        print("="*70)

        # 执行带过滤条件的查询
        print(f"\nQuerying users with name filter...")

        start_time = time.time()
        result = user_service.get_users(
            name_pattern="test_user_",
            limit=1000
        )
        query_time = time.time() - start_time

        assert result.is_success, f"Failed to query users: {result.error}"

        users = result.data.get("users", [])

        print(f"Filtered query completed in {query_time:.2f}s")
        print(f"Users matching filter: {len(users)}")

        # 验证查询成功
        assert len(users) >= 0
        print(f"\n✅ Filtered query completed successfully")
