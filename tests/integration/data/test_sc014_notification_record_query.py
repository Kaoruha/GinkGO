# Upstream: SC-014 性能要求 (通知记录查询响应时间 < 200ms p95)
# Downstream: tasks.md T292 验证
# Role: 性能验证测试 - 验证通知记录查询满足性能要求

"""
Performance verification test for SC-014: Notification record query latency.

SC-014 Requirement: 通知记录查询响应时间 < 200ms (p95)

Test Strategy:
1. 创建 1000 条通知记录
2. 执行多种查询操作（按用户、按状态、按时间范围）
3. 记录每次查询的响应时间
4. 计算 p95 延迟
5. 验证 p95 < 200ms
"""

import pytest
import time
from typing import List
from datetime import datetime, timedelta

from ginkgo.data.models import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES, SOURCE_TYPES, CONTACT_TYPES


@pytest.mark.integration
@pytest.mark.performance
class TestSC014NotificationRecordQueryPerformance:
    """SC-014: 通知记录查询响应时间 < 200ms (p95)"""

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

    def test_sc014_query_by_user_latency(self):
        """
        SC-014: 验证按用户查询通知记录的延迟 < 200ms p95

        测试步骤：
        1. 创建 1000 条通知记录（100 个用户，每个用户 10 条记录）
        2. 对每个用户执行查询操作
        3. 记录每次查询的响应时间
        4. 计算 p95 延迟
        5. 验证 p95 < 200ms
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-014 Performance Test: Notification Record Query by User")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 步骤 1: 创建 1000 条记录
        print(f"\nStep 1: Creating 1000 notification records...")
        num_users = 100
        records_per_user = 10
        user_uuids = []

        for user_idx in range(num_users):
            user_uuid = f"test_user_{unique_id}_{user_idx:03d}"
            user_uuids.append(user_uuid)

            for record_idx in range(records_per_user):
                record = MNotificationRecord(
                    user_uuid=user_uuid,
                    content=f"Test notification {record_idx} for user {user_idx}",
                    title=f"Test {record_idx}",
                    channel_type="webhook",
                    status=NOTIFICATION_STATUS_TYPES.PENDING,
                    source=SOURCE_TYPES.SYSTEM,
                    message_id=f"msg_{unique_id}_{user_idx}_{record_idx}"
                )
                record_crud.add(record)

        print(f"  Created {num_users * records_per_user} records for {num_users} users")

        try:
            # 步骤 2: 对每个用户执行查询
            print(f"\nStep 2: Querying records by user...")
            query_latencies: List[float] = []

            for user_uuid in user_uuids:
                start_time = time.time()
                result = record_crud.get_notification_records_by_user(
                    user_uuid=user_uuid,
                    limit=100
                )
                elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
                query_latencies.append(elapsed)

            # 步骤 3: 计算 p95 延迟
            p95_latency = self._calculate_p95(query_latencies)
            avg_latency = sum(query_latencies) / len(query_latencies)

            print("\n" + "="*70)
            print("SC-014 Query by User Results")
            print("="*70)
            print(f"Total Queries:          {len(query_latencies)}")
            print(f"Average Latency:        {avg_latency:.2f}ms")
            print(f"P95 Latency:            {p95_latency:.2f}ms")
            print(f"Requirement:            < 200ms")

            if p95_latency < 200:
                print(f"\nResult:                 ✅ PASS (p95 = {p95_latency:.2f}ms)")
            else:
                print(f"\nResult:                 ❌ FAIL (p95 = {p95_latency:.2f}ms)")

            print("="*70)

            # 验证 p95 < 200ms
            assert p95_latency < 200, f"SC-014 FAILED: p95 {p95_latency:.2f}ms >= 200ms"

        finally:
            # 清理测试数据
            for user_uuid in user_uuids:
                try:
                    record_crud.delete_notification_records_by_user(user_uuid=user_uuid)
                except:
                    pass

    def test_sc014_query_with_filters_latency(self):
        """
        SC-014: 验证带过滤条件的查询延迟

        测试步骤：
        1. 创建不同状态和时间范围的记录
        2. 执行带过滤条件的查询
        3. 测量响应时间
        4. 验证 p95 < 200ms
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-014 Performance Test: Query with Filters")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建不同状态的记录
        print(f"\nStep 1: Creating records with different statuses...")
        statuses = [
            NOTIFICATION_STATUS_TYPES.PENDING,
            NOTIFICATION_STATUS_TYPES.SENT,
            NOTIFICATION_STATUS_TYPES.FAILED
        ]

        user_uuid = f"test_user_{unique_id}"
        num_per_status = 100

        for status in statuses:
            for i in range(num_per_status):
                record = MNotificationRecord(
                    user_uuid=user_uuid,
                    content=f"Test notification with status {status.name}",
                    title=f"Status Test {i}",
                    channel_type="webhook",
                    status=status,
                    source=SOURCE_TYPES.SYSTEM,
                    message_id=f"msg_{unique_id}_{status.name}_{i}"
                )
                record_crud.add(record)

        print(f"  Created {len(statuses) * num_per_status} records")

        try:
            # 步骤 2: 执行带过滤条件的查询
            print(f"\nStep 2: Querying with status filter...")
            filter_latencies: List[float] = []

            for status in statuses:
                start_time = time.time()
                result = record_crud.get_notification_records_by_user(
                    user_uuid=user_uuid,
                    status=status.value,
                    limit=100
                )
                elapsed = (time.time() - start_time) * 1000
                filter_latencies.append(elapsed)

            p95_latency = self._calculate_p95(filter_latencies)
            avg_latency = sum(filter_latencies) / len(filter_latencies)

            print("\n" + "="*70)
            print("SC-014 Filter Query Results")
            print("="*70)
            print(f"Filter Queries:         {len(filter_latencies)}")
            print(f"Average Latency:        {avg_latency:.2f}ms")
            print(f"P95 Latency:            {p95_latency:.2f}ms")
            print(f"Requirement:            < 200ms")

            if p95_latency < 200:
                print(f"\nResult:                 ✅ PASS (p95 = {p95_latency:.2f}ms)")
            else:
                print(f"\nResult:                 ❌ FAIL (p95 = {p95_latency:.2f}ms)")

            print("="*70)

            assert p95_latency < 200, f"SC-014 FAILED: p95 {p95_latency:.2f}ms >= 200ms"

        finally:
            # 清理测试数据
            try:
                record_crud.delete_notification_records_by_user(user_uuid=user_uuid)
            except:
                pass

    def test_sc014_pagination_query_latency(self):
        """
        SC-014: 验证分页查询性能

        测试步骤：
        1. 创建大量通知记录
        2. 执行分页查询
        3. 测量每页的响应时间
        4. 验证 p95 < 200ms
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-014 Performance Test: Pagination Query")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        # 创建大量记录
        print(f"\nStep 1: Creating 500 notification records...")
        user_uuid = f"test_user_pagination_{unique_id}"
        num_records = 500

        for i in range(num_records):
            record = MNotificationRecord(
                user_uuid=user_uuid,
                content=f"Pagination test notification {i}",
                title=f"Pagination {i}",
                channel_type="webhook",
                status=NOTIFICATION_STATUS_TYPES.SENT,
                source=SOURCE_TYPES.SYSTEM,
                message_id=f"msg_{unique_id}_{i}"
            )
            record_crud.add(record)

        print(f"  Created {num_records} records")

        try:
            # 步骤 2: 执行分页查询
            print(f"\nStep 2: Querying with pagination...")
            page_size = 50
            num_pages = 10
            page_latencies: List[float] = []

            for page in range(num_pages):
                offset = page * page_size
                start_time = time.time()
                result = record_crud.get_notification_records_by_user(
                    user_uuid=user_uuid,
                    limit=page_size,
                    offset=offset
                )
                elapsed = (time.time() - start_time) * 1000
                page_latencies.append(elapsed)

            p95_latency = self._calculate_p95(page_latencies)
            avg_latency = sum(page_latencies) / len(page_latencies)

            print("\n" + "="*70)
            print("SC-014 Pagination Query Results")
            print("="*70)
            print(f"Pages Queried:          {len(page_latencies)}")
            print(f"Records Per Page:       {page_size}")
            print(f"Average Latency:        {avg_latency:.2f}ms")
            print(f"P95 Latency:            {p95_latency:.2f}ms")
            print(f"Requirement:            < 200ms")

            if p95_latency < 200:
                print(f"\nResult:                 ✅ PASS (p95 = {p95_latency:.2f}ms)")
            else:
                print(f"\nResult:                 ❌ FAIL (p95 = {p95_latency:.2f}ms)")

            print("="*70)

            assert p95_latency < 200, f"SC-014 FAILED: p95 {p95_latency:.2f}ms >= 200ms"

        finally:
            # 清理测试数据
            try:
                record_crud.delete_notification_records_by_user(user_uuid=user_uuid)
            except:
                pass

    @staticmethod
    def _calculate_p95(latencies: List[float]) -> float:
        """计算 p95 延迟"""
        if not latencies:
            return 0.0
        sorted_latencies = sorted(latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
