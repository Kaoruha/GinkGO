# Upstream: SC-002 性能要求 (MongoDB 连接池支持 >= 10 个并发连接)
# Downstream: tasks.md T184 验证
# Role: 性能验证测试 - 验证 MongoDB 连接池满足并发要求

"""
Performance verification test for SC-002: MongoDB connection pool.

SC-002 Requirement: MongoDB 连接池支持 >= 10 个并发连接

Test Strategy:
1. 创建 20 个并发线程
2. 每个线程执行多次 MongoDB 操作
3. 验证所有线程都能成功完成操作
4. 验证连接池不会耗尽
"""

import pytest
import time
import threading
from typing import List

from ginkgo.data.models import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES, SOURCE_TYPES


@pytest.mark.integration
@pytest.mark.performance
class TestSC002MongoDBConnectionPool:
    """SC-002: MongoDB 连接池支持 >= 10 个并发连接"""

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

    def test_sc002_concurrent_connections_20_threads(self):
        """
        SC-002: 验证 MongoDB 连接池支持 >= 10 个并发连接

        测试步骤：
        1. 创建 20 个并发线程（超过要求的 10 个）
        2. 每个线程执行 10 次 MongoDB CRUD 操作
        3. 等待所有线程完成
        4. 验证所有操作都成功
        5. 验证连接池没有耗尽
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-002 Performance Test: MongoDB Connection Pool")
        print("="*70)

        # 准备测试数据
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        num_threads = 20  # 超过要求的 10 个并发连接
        operations_per_thread = 10

        results = {"success": 0, "failed": 0, "errors": []}
        lock = threading.Lock()

        def worker(thread_id: int):
            """工作线程函数"""
            try:
                from ginkgo import service_hub
                record_crud = service_hub.data.cruds.notification_record()

                for i in range(operations_per_thread):
                    # 创建记录
                    record = MNotificationRecord(
                        user_uuid=f"test_user_{unique_id}_t{thread_id}_o{i}",
                        content=f"Concurrent test from thread {thread_id}, operation {i}",
                        title=f"Thread {thread_id}",
                        channel_type="webhook",
                        status=NOTIFICATION_STATUS_TYPES.PENDING,
                        source=SOURCE_TYPES.SYSTEM,
                        message_id=f"msg_{unique_id}_t{thread_id}_o{i}"
                    )

                    # 执行 CRUD 操作
                    record_crud.add(record)
                    result = record_crud.get_by_uuid(record.uuid)
                    record.content = f"Updated by thread {thread_id}"
                    record_crud.update(record)
                    record_crud.delete(record.uuid)

                with lock:
                    results["success"] += 1

            except Exception as e:
                with lock:
                    results["failed"] += 1
                    results["errors"].append(f"Thread {thread_id}: {str(e)}")

        # 创建并启动线程
        print(f"\nStarting {num_threads} concurrent threads...")
        print(f"Each thread performs {operations_per_thread} CRUD operations...")

        threads = []
        start_time = time.time()

        for i in range(num_threads):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        elapsed_time = time.time() - start_time

        # 输出结果
        print(f"\nAll threads completed in {elapsed_time:.2f}s")
        print(f"Successful threads: {results['success']}/{num_threads}")
        print(f"Failed threads:      {results['failed']}/{num_threads}")

        if results["errors"]:
            print("\nErrors encountered:")
            for error in results["errors"]:
                print(f"  - {error}")

        print("\n" + "="*70)
        print("SC-002 Connection Pool Results")
        print("="*70)
        print(f"Concurrent Threads:   {num_threads}")
        print(f"Requirement:          >= 10 concurrent connections")
        print(f"Operations Performed: {num_threads * operations_per_thread * 4} CRUD ops")
        print(f"Time Taken:           {elapsed_time:.2f}s")

        if results["failed"] == 0:
            print(f"\nResult:               ✅ PASS (All {num_threads} threads succeeded)")
        else:
            print(f"\nResult:               ❌ FAIL ({results['failed']} threads failed)")

        print("="*70)

        # 验证所有线程都成功
        assert results["failed"] == 0, f"SC-002 FAILED: {results['failed']} threads failed"

        # 验证至少支持 10 个并发连接
        assert results["success"] >= 10, f"SC-002 FAILED: Only {results['success']} threads succeeded, required >= 10"

    def test_sc002_sustained_concurrent_load(self):
        """
        SC-002: 验证连接池在持续负载下的表现

        测试步骤：
        1. 持续创建并发连接
        2. 每轮使用不同的线程
        3. 验证连接池稳定性和复用能力
        """
        from ginkgo import service_hub

        record_crud = service_hub.data.cruds.notification_record()

        print("\n" + "="*70)
        print("SC-002 Sustained Load Test")
        print("="*70)

        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]

        num_rounds = 5
        threads_per_round = 15

        total_success = 0
        total_failed = 0

        for round_num in range(num_rounds):
            results = {"success": 0, "failed": 0}
            lock = threading.Lock()

            def worker(thread_id: int):
                try:
                    from ginkgo import service_hub
                    record_crud = service_hub.data.cruds.notification_record()

                    record = MNotificationRecord(
                        user_uuid=f"test_user_{unique_id}_r{round_num}_t{thread_id}",
                        content=f"Sustained load round {round_num}, thread {thread_id}",
                        title=f"Round {round_num}",
                        channel_type="webhook",
                        status=NOTIFICATION_STATUS_TYPES.PENDING,
                        source=SOURCE_TYPES.SYSTEM,
                        message_id=f"msg_{unique_id}_r{round_num}_t{thread_id}"
                    )

                    record_crud.add(record)
                    record_crud.delete(record.uuid)

                    with lock:
                        results["success"] += 1

                except Exception as e:
                    with lock:
                        results["failed"] += 1

            # 创建并启动线程
            threads = []
            for i in range(threads_per_round):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            # 等待完成
            for thread in threads:
                thread.join()

            total_success += results["success"]
            total_failed += results["failed"]

            print(f"Round {round_num + 1}/{num_rounds}: "
                  f"{results['success']}/{threads_per_round} threads succeeded")

            time_module.sleep(0.5)  # 短暂间隔

        print("\n" + "="*70)
        print("SC-002 Sustained Load Results")
        print("="*70)
        print(f"Total Rounds:        {num_rounds}")
        print(f"Threads Per Round:   {threads_per_round}")
        print(f"Total Successful:    {total_success}")
        print(f"Total Failed:        {total_failed}")

        if total_failed == 0:
            print(f"\nResult:              ✅ PASS (Connection pool stable under load)")
        else:
            print(f"\nResult:              ❌ FAIL (Connection pool degraded)")

        print("="*70)

        assert total_failed == 0, f"SC-002 FAILED: {total_failed} threads failed over {num_rounds} rounds"
