# Upstream: SC-001 性能要求 (MongoDB CRUD 操作响应时间 < 50ms p95)
# Downstream: tasks.md T183 验证
# Role: 性能验证测试 - 验证 MongoDB CRUD 操作满足性能要求

"""
Performance verification test for SC-001: MongoDB CRUD operation latency.

SC-001 Requirement: MongoDB CRUD 操作响应时间 < 50ms (p95)

Test Strategy:
1. 执行 100 次 MongoDB CRUD 操作（创建、读取、更新、删除）
2. 记录每次操作的响应时间
3. 计算 p95 延迟
4. 验证 p95 < 50ms
"""

import pytest
import time
from typing import List

from ginkgo.data.models import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES, SOURCE_TYPES


@pytest.mark.integration
@pytest.mark.performance
class TestSC001MongoDBCRUDPerformance:
    """SC-001: MongoDB CRUD 操作响应时间 < 50ms (p95)"""

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

    def test_sc001_crud_operations_p95_latency(self):
        """
        SC-001: 验证 MongoDB CRUD 操作 p95 延迟 < 50ms

        测试步骤：
        1. 创建 100 条通知记录（记录创建时间）
        2. 读取 100 次记录（记录查询时间）
        3. 更新 100 次记录（记录更新时间）
        4. 删除 100 条记录（记录删除时间）
        5. 计算 p95 延迟
        6. 验证 p95 < 50ms
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-001 Performance Test: MongoDB CRUD Operations")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        create_latencies: List[float] = []
        read_latencies: List[float] = []
        update_latencies: List[float] = []
        delete_latencies: List[float] = []

        # 步骤 1: 创建 100 条记录
        print(f"\nStep 1: Creating 100 notification records...")
        records = []
        for i in range(100):
            record = MNotificationRecord(
                user_uuid=f"test_user_{unique_id}_{i}",
                content=f"Test notification {i}",
                title=f"Test {i}",
                channel_type="webhook",
                status=NOTIFICATION_STATUS_TYPES.PENDING,
                source=SOURCE_TYPES.SYSTEM,
                message_id=f"msg_{unique_id}_{i}"
            )

            start_time = time.time()
            record_crud.add(record)
            elapsed = (time.time() - start_time) * 1000  # 转换为毫秒
            create_latencies.append(elapsed)
            records.append(record)

        print(f"  Created {len(records)} records")
        print(f"  Create latency p95: {self._calculate_p95(create_latencies):.2f}ms")

        # 步骤 2: 读取 100 次记录
        print(f"\nStep 2: Reading 100 notification records...")
        for i, record in enumerate(records):
            start_time = time.time()
            result = record_crud.get_by_uuid(record.uuid)
            elapsed = (time.time() - start_time) * 1000
            read_latencies.append(elapsed)

        print(f"  Read {len(read_latencies)} records")
        print(f"  Read latency p95: {self._calculate_p95(read_latencies):.2f}ms")

        # 步骤 3: 更新 100 次记录
        print(f"\nStep 3: Updating 100 notification records...")
        for i, record in enumerate(records):
            record.content = f"Updated notification {i}"
            start_time = time.time()
            record_crud.update(record)
            elapsed = (time.time() - start_time) * 1000
            update_latencies.append(elapsed)

        print(f"  Updated {len(update_latencies)} records")
        print(f"  Update latency p95: {self._calculate_p95(update_latencies):.2f}ms")

        # 步骤 4: 删除 100 条记录
        print(f"\nStep 4: Deleting 100 notification records...")
        for record in records:
            start_time = time.time()
            record_crud.delete(record.uuid)
            elapsed = (time.time() - start_time) * 1000
            delete_latencies.append(elapsed)

        print(f"  Deleted {len(delete_latencies)} records")
        print(f"  Delete latency p95: {self._calculate_p95(delete_latencies):.2f}ms")

        # 步骤 5: 计算并验证结果
        print("\n" + "="*70)
        print("SC-001 Performance Results")
        print("="*70)

        create_p95 = self._calculate_p95(create_latencies)
        read_p95 = self._calculate_p95(read_latencies)
        update_p95 = self._calculate_p95(update_latencies)
        delete_p95 = self._calculate_p95(delete_latencies)
        overall_p95 = self._calculate_p95(create_latencies + read_latencies + update_latencies + delete_latencies)

        print(f"Create Operation p95: {create_p95:.2f}ms")
        print(f"Read Operation p95:    {read_p95:.2f}ms")
        print(f"Update Operation p95:  {update_p95:.2f}ms")
        print(f"Delete Operation p95:  {delete_p95:.2f}ms")
        print(f"Overall p95:           {overall_p95:.2f}ms")
        print(f"\nSC-001 Requirement:    < 50ms")

        if overall_p95 < 50:
            print(f"Result:                ✅ PASS (p95 = {overall_p95:.2f}ms)")
        else:
            print(f"Result:                ❌ FAIL (p95 = {overall_p95:.2f}ms)")

        print("="*70)

        # 验证总体 p95 < 50ms
        assert overall_p95 < 50, f"SC-001 FAILED: Overall p95 {overall_p95:.2f}ms >= 50ms"

    def test_sc001_single_operation_performance(self):
        """
        SC-001: 验证单个 CRUD 操作性能

        测试各种 CRUD 操作的基本性能
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-001 Single Operation Performance Test")
        print("="*70)

        # 创建测试记录
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        record = MNotificationRecord(
            user_uuid=f"test_user_{unique_id}",
            content="Single operation test",
            title="Single Test",
            channel_type="webhook",
            status=NOTIFICATION_STATUS_TYPES.PENDING,
            source=SOURCE_TYPES.SYSTEM,
            message_id=f"msg_{unique_id}"
        )

        # 测试创建
        start_time = time.time()
        record_crud.add(record)
        create_latency = (time.time() - start_time) * 1000
        print(f"Single Create: {create_latency:.2f}ms")

        # 测试读取
        start_time = time.time()
        result = record_crud.get_by_uuid(record.uuid)
        read_latency = (time.time() - start_time) * 1000
        print(f"Single Read:    {read_latency:.2f}ms")

        # 测试更新
        record.content = "Updated content"
        start_time = time.time()
        record_crud.update(record)
        update_latency = (time.time() - start_time) * 1000
        print(f"Single Update:  {update_latency:.2f}ms")

        # 测试删除
        start_time = time.time()
        record_crud.delete(record.uuid)
        delete_latency = (time.time() - start_time) * 1000
        print(f"Single Delete:  {delete_latency:.2f}ms")

        print("\n" + "="*70)

        # 验证所有操作 < 50ms
        assert create_latency < 50, f"Create latency {create_latency:.2f}ms >= 50ms"
        assert read_latency < 50, f"Read latency {read_latency:.2f}ms >= 50ms"
        assert update_latency < 50, f"Update latency {update_latency:.2f}ms >= 50ms"
        assert delete_latency < 50, f"Delete latency {delete_latency:.2f}ms >= 50ms"

    @staticmethod
    def _calculate_p95(latencies: List[float]) -> float:
        """计算 p95 延迟"""
        if not latencies:
            return 0.0
        sorted_latencies = sorted(latencies)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]
