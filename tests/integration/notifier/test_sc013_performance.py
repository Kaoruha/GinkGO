# Upstream: SC-013 性能要求 (通知记录查询响应时间 < 200ms p95)
# Downstream: tasks.md T198 验证
# Role: 性能验证测试 - 验证通知历史查询满足 SC-013 性能要求


"""
Performance verification test for SC-013: Notification history query response time.

SC-013 Requirement: 通知记录查询响应时间 < 200ms p95

Test Strategy:
1. Generate 100 notification records
2. Execute 100 query operations
3. Calculate p95 response time
4. Verify p95 < 200ms
"""

import pytest
import time
import statistics
from typing import List, Dict
import numpy as np


@pytest.mark.integration
@pytest.mark.performance
class TestSC013NotificationHistoryPerformance:
    """SC-013: 通知记录查询响应时间 < 200ms p95"""

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

    def test_sc013_history_query_performance_p95(self):
        """
        SC-013: 验证通知记录查询响应时间 < 200ms p95

        测试步骤：
        1. 创建测试用户和联系方式
        2. 生成 100 条通知记录
        3. 执行 100 次查询操作（每次查询 50 条记录）
        4. 计算 p95 响应时间
        5. 验证 p95 < 200ms

        性能目标：
        - p50 < 50ms（中位数）
        - p95 < 200ms（95百分位）
        - p99 < 500ms（99百分位）
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"perf_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Performance Test User {unique_id}"
        )
        assert user_result.is_success, f"Failed to create user: {user_result.error}"
        user_uuid = user_result.data["uuid"]

        # 创建测试联系方式
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.WEBHOOK,
            address="https://example.com/webhook/perf_test",
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success, f"Failed to create contact: {contact_result.error}"

        try:
            # 生成 100 条通知记录
            print("\n" + "="*70)
            print("SC-013 Performance Test: Notification History Query")
            print("="*70)
            print(f"User: {user_name} (UUID: {user_uuid})")
            print(f"Generating 100 notification records...")

            record_count = 100
            for i in range(record_count):
                notification_service.send_sync(
                    content=f"Performance test notification #{i+1}",
                    title=f"Perf Test #{i+1}",
                    channels=["discord"],
                    user_uuid=user_uuid
                )
                if (i + 1) % 20 == 0:
                    print(f"  Generated {i+1}/{record_count} records...")

            print(f"✓ Generated {record_count} notification records")
            print(f"\nExecuting 100 query operations (each retrieving 50 records)...")

            # 执行 100 次查询操作
            query_count = 100
            response_times: List[float] = []

            for i in range(query_count):
                start_time = time.perf_counter()

                result = notification_service.get_notification_history(
                    user_uuid=user_uuid,
                    limit=50
                )

                end_time = time.perf_counter()
                response_time_ms = (end_time - start_time) * 1000  # 转换为毫秒
                response_times.append(response_time_ms)

                assert result.is_success, f"Query failed: {result.error}"

                if (i + 1) % 20 == 0:
                    print(f"  Executed {i+1}/{query_count} queries...")

            print(f"✓ Executed {query_count} query operations")

            # 计算统计数据
            response_times_array = np.array(response_times)
            p50 = np.percentile(response_times_array, 50)
            p90 = np.percentile(response_times_array, 90)
            p95 = np.percentile(response_times_array, 95)
            p99 = np.percentile(response_times_array, 99)
            mean = np.mean(response_times_array)
            std = np.std(response_times_array)
            min_time = np.min(response_times_array)
            max_time = np.max(response_times_array)

            # 打印结果
            print("\n" + "="*70)
            print("Performance Test Results")
            print("="*70)
            print(f"Total Queries:        {query_count}")
            print(f"Records per Query:    50")
            print(f"Total Records:        {record_count}")
            print(f"\nResponse Time Statistics (ms):")
            print(f"  Mean:               {mean:.2f}")
            print(f"  Std Dev:            {std:.2f}")
            print(f"  Min:                {min_time:.2f}")
            print(f"  Max:                {max_time:.2f}")
            print(f"\nPercentiles:")
            print(f"  p50 (Median):       {p50:.2f} ms")
            print(f"  p90:                {p90:.2f} ms")
            print(f"  p95:                {p95:.2f} ms  ⬅ SC-013 Requirement")
            print(f"  p99:                {p99:.2f} ms")
            print("="*70)

            # 验证 SC-013 要求
            print(f"\nSC-013 Verification:")
            print(f"  Required: p95 < 200ms")
            print(f"  Actual:   p95 = {p95:.2f} ms")

            if p95 < 200:
                print(f"  Result:   ✅ PASS - p95 ({p95:.2f}ms) < 200ms")
            else:
                print(f"  Result:   ❌ FAIL - p95 ({p95:.2f}ms) >= 200ms")

            # 断言验证
            assert p95 < 200, f"SC-013 FAILED: p95 response time {p95:.2f}ms >= 200ms"

            # 额外的性能目标验证（非强制，仅供参考）
            print(f"\nAdditional Performance Targets:")
            if p50 < 50:
                print(f"  ✅ p50 ({p50:.2f}ms) < 50ms (excellent)")
            else:
                print(f"  ⚠️  p50 ({p50:.2f}ms) >= 50ms (acceptable)")

            if p99 < 500:
                print(f"  ✅ p99 ({p99:.2f}ms) < 500ms (good)")
            else:
                print(f"  ⚠️  p99 ({p99:.2f}ms) >= 500ms (needs attention)")

            print("="*70 + "\n")

        finally:
            # 清理测试数据（可选）
            pass

    def test_sc013_history_query_performance_with_different_limits(self):
        """
        SC-013: 验证不同 limit 值的查询性能

        测试不同返回记录数对性能的影响：
        - limit=10 (小结果集)
        - limit=50 (中等结果集)
        - limit=100 (大结果集)
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"perf_limit_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Performance Limit Test User {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        # 创建联系方式
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.WEBHOOK,
            address="https://example.com/webhook/perf_limit_test",
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success

        try:
            # 生成 150 条记录
            print("\n" + "="*70)
            print("SC-013 Performance Test: Different Limits")
            print("="*70)

            record_count = 150
            for i in range(record_count):
                notification_service.send_sync(
                    content=f"Performance limit test #{i+1}",
                    channels=["discord"],
                    user_uuid=user_uuid
                )
            print(f"✓ Generated {record_count} notification records")

            # 测试不同的 limit 值
            limits = [10, 50, 100]
            results = {}

            for limit in limits:
                print(f"\nTesting limit={limit}...")
                response_times = []

                # 执行 50 次查询
                for _ in range(50):
                    start_time = time.perf_counter()
                    result = notification_service.get_notification_history(
                        user_uuid=user_uuid,
                        limit=limit
                    )
                    end_time = time.perf_counter()

                    assert result.is_success
                    response_times.append((end_time - start_time) * 1000)

                p95 = np.percentile(response_times, 95)
                results[limit] = {
                    'p50': np.percentile(response_times, 50),
                    'p95': p95,
                    'p99': np.percentile(response_times, 99),
                    'mean': np.mean(response_times)
                }

                status = "✅ PASS" if p95 < 200 else "❌ FAIL"
                print(f"  p50={results[limit]['p50']:.2f}ms, "
                      f"p95={results[limit]['p95']:.2f}ms, "
                      f"p99={results[limit]['p99']:.2f}ms {status}")

            print("="*70)

            # 验证所有 limit 值都满足 SC-013
            for limit, stats in results.items():
                assert stats['p95'] < 200, f"SC-013 FAILED for limit={limit}: p95={stats['p95']:.2f}ms >= 200ms"

            print(f"\n✅ All limit values satisfy SC-013 requirement (p95 < 200ms)\n")

        finally:
            pass

    def test_sc013_history_query_performance_with_filters(self):
        """
        SC-013: 验证带过滤条件的查询性能

        测试不同过滤条件对性能的影响：
        - 按 user_uuid 过滤
        - 按 status 过滤
        - 组合过滤
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"perf_filter_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Performance Filter Test User {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        # 创建联系方式
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.WEBHOOK,
            address="https://example.com/webhook/perf_filter_test",
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success

        try:
            # 生成 100 条记录
            print("\n" + "="*70)
            print("SC-013 Performance Test: Query Filters")
            print("="*70)

            record_count = 100
            for i in range(record_count):
                notification_service.send_sync(
                    content=f"Performance filter test #{i+1}",
                    channels=["discord"],
                    user_uuid=user_uuid
                )
            print(f"✓ Generated {record_count} notification records")

            # 测试不同的过滤条件
            test_cases = [
                ("user_uuid filter", {"user_uuid": user_uuid}),
                ("status filter (FAILED)", {"user_uuid": user_uuid, "status": NOTIFICATION_STATUS_TYPES.FAILED.value}),
                ("status filter (SENT)", {"user_uuid": user_uuid, "status": NOTIFICATION_STATUS_TYPES.SENT.value}),
            ]

            results = {}
            for test_name, filters in test_cases:
                print(f"\nTesting: {test_name}...")
                response_times = []

                # 执行 30 次查询
                for _ in range(30):
                    start_time = time.perf_counter()
                    result = notification_service.get_notification_history(
                        limit=50,
                        **filters
                    )
                    end_time = time.perf_counter()

                    assert result.is_success
                    response_times.append((end_time - start_time) * 1000)

                p95 = np.percentile(response_times, 95)
                results[test_name] = {
                    'p50': np.percentile(response_times, 50),
                    'p95': p95,
                    'p99': np.percentile(response_times, 99),
                }

                status = "✅ PASS" if p95 < 200 else "❌ FAIL"
                print(f"  p50={results[test_name]['p50']:.2f}ms, "
                      f"p95={results[test_name]['p95']:.2f}ms, "
                      f"p99={results[test_name]['p99']:.2f}ms {status}")

            print("="*70)

            # 验证所有过滤条件都满足 SC-013
            for test_name, stats in results.items():
                assert stats['p95'] < 200, f"SC-013 FAILED for {test_name}: p95={stats['p95']:.2f}ms >= 200ms"

            print(f"\n✅ All filter conditions satisfy SC-013 requirement (p95 < 200ms)\n")

        finally:
            pass
