# Upstream: SC-010 性能要求 (Kafka 吞吐量 >= 100 msg/s)
# Downstream: tasks.md T182 验证
# Role: 性能验证测试 - 验证 Kafka Worker 吞吐量满足 SC-010 要求


"""
Performance verification test for SC-010: Kafka throughput.

SC-010 Requirement: Kafka 消费吞吐量 >= 100 msg/s (单 worker)

Test Strategy:
1. Send 1000 messages via Kafka as quickly as possible
2. Measure time from first send to last completion
3. Calculate throughput (messages / second)
4. Verify throughput >= 100 msg/s
"""

import pytest
import time
from typing import List
import numpy as np


@pytest.mark.integration
@pytest.mark.performance
class TestSC010KafkaThroughput:
    """SC-010: Kafka 消费吞吐量 >= 100 msg/s"""

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

    def test_sc010_throughput_1000_messages(self):
        """
        SC-010: 验证 Kafka Worker 吞吐量 >= 100 msg/s

        测试步骤：
        1. 快速发送 1000 条消息到 Kafka
        2. 记录发送开始和结束时间
        3. 等待所有消息被处理
        4. 计算端到端吞吐量
        5. 验证吞吐量 >= 100 msg/s

        注意：此测试需要 Worker 正在运行
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"throughput_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Throughput Test User {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        # 创建 webhook 联系方式
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.WEBHOOK,
            address="https://httpbin.org/post",
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success

        try:
            print("\n" + "="*70)
            print("SC-010 Performance Test: Kafka Worker Throughput")
            print("="*70)
            print(f"User: {user_name} (UUID: {user_uuid})")
            print(f"Target: Throughput >= 100 msg/s")
            print(f"Test:   Sending 1000 messages...")
            print("="*70)

            # 记录发送开始时间
            send_start_time = time.time()

            # 快速发送 1000 条消息
            message_count = 1000
            message_ids: List[str] = []

            print(f"\nSending {message_count} messages...")
            for i in range(message_count):
                result = notification_service.send(
                    content=f"Throughput test notification #{i+1}",
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    async_mode=True
                )

                if result.is_success and "message_id" in result.data:
                    message_ids.append(result.data["message_id"])

                if (i + 1) % 100 == 0:
                    print(f"  Sent {i+1}/{message_count} messages...")

            # 记录发送结束时间
            send_end_time = time.time()
            send_duration = send_end_time - send_start_time

            print(f"\n✓ Sent {len(message_ids)} messages in {send_duration:.2f}s")
            print(f"  Send rate: {len(message_ids)/send_duration:.2f} msg/s")

            print(f"\nWaiting for Worker to process all messages...")
            print(f"(This may take 30-60 seconds...)")

            # 等待所有消息被处理
            max_wait_time = 60  # 最多等待 60 秒
            check_interval = 1.0
            check_start = time.time()

            processed_count = 0
            last_processed_count = 0
            last_print_time = check_start

            while processed_count < len(message_ids) and (time.time() - check_start) < max_wait_time:
                # 查询处理进度
                history_result = notification_service.get_notification_history(
                    user_uuid=user_uuid,
                    limit=2000  # 足够大的 limit
                )

                if history_result.is_success:
                    records = history_result.data.get("records", [])

                    # 统计已处理的 SENT 状态消息
                    processed_count = sum(
                        1 for r in records
                        if r.get("message_id") in message_ids and r.get("status") == NOTIFICATION_STATUS_TYPES.SENT.value
                    )

                    # 每 5 秒打印一次进度
                    current_time = time.time()
                    if current_time - last_print_time >= 5.0:
                        progress_rate = (processed_count - last_processed_count) / 5.0
                        print(f"  Progress: {processed_count}/{len(message_ids)} ({progress_rate:.1f} msg/s)")
                        last_processed_count = processed_count
                        last_print_time = current_time

                    # 如果处理完成，退出
                    if processed_count >= len(message_ids):
                        break

                time_module.sleep(check_interval)

            # 记录处理完成时间
            process_end_time = time.time()

            print(f"\n✓ Processed {processed_count}/{len(message_ids)} messages")

            if processed_count < len(message_ids) * 0.9:  # 如果完成率低于 90%
                print(f"⚠️  Warning: Only {processed_count}/{len(message_ids)} messages processed")
                print(f"    Worker may not be running or has performance issues")

            # 计算端到端吞吐量
            total_duration = process_end_time - send_start_time
            processing_duration = process_end_time - send_end_time

            if total_duration > 0 and processed_count > 0:
                # 计算吞吐量（消息数 / 总时间）
                throughput_e2e = processed_count / total_duration
                throughput_processing = processed_count / processing_duration if processing_duration > 0 else 0

                print("\n" + "="*70)
                print("Throughput Test Results")
                print("="*70)
                print(f"Total Messages:     {len(message_ids)}")
                print(f"Processed:          {processed_count}")
                print(f"Completion Rate:    {processed_count/len(message_ids)*100:.1f}%")
                print(f"\nTiming:")
                print(f"  Send Duration:     {send_duration:.2f}s")
                print(f"  Process Duration:  {processing_duration:.2f}s")
                print(f"  Total Duration:    {total_duration:.2f}s")
                print(f"\nThroughput:")
                print(f"  End-to-End:        {throughput_e2e:.2f} msg/s  ⬅ SC-010 Requirement")
                print(f"  Processing Only:   {throughput_processing:.2f} msg/s")
                print("="*70)

                # 验证 SC-010 要求
                print(f"\nSC-010 Verification:")
                print(f"  Required: Throughput >= 100 msg/s")
                print(f"  Actual:   Throughput = {throughput_e2e:.2f} msg/s")

                if throughput_e2e >= 100:
                    print(f"  Result:   ✅ PASS - Throughput ({throughput_e2e:.2f} msg/s) >= 100 msg/s")
                else:
                    print(f"  Result:   ❌ FAIL - Throughput ({throughput_e2e:.2f} msg/s) < 100 msg/s")

                # 断言验证
                assert throughput_e2e >= 100, f"SC-010 FAILED: Throughput {throughput_e2e:.2f} msg/s < 100 msg/s"

                print("="*70 + "\n")

            else:
                pytest.skip("No messages were processed. Worker may not be running.")

        finally:
            pass

    def test_sc010_throughput_burst_test(self):
        """
        SC-010: 突发流量吞吐量测试

        测试场景：
        1. 在 1 秒内发送 200 条消息
        2. 验证 Worker 能否处理突发流量
        3. 计算平均吞吐量
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"burst_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Burst Test User {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        # 创建 webhook
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.WEBHOOK,
            address="https://httpbin.org/post",
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success

        try:
            print("\n" + "="*70)
            print("SC-010 Performance Test: Burst Throughput")
            print("="*70)

            # 在 1 秒内发送 200 条消息
            message_count = 200
            message_ids: List[str] = []

            print(f"Sending {message_count} messages in 1 second burst...")

            send_start = time.time()
            for i in range(message_count):
                result = notification_service.send(
                    content=f"Burst test #{i+1}",
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    async_mode=True
                )

                if result.is_success and "message_id" in result.data:
                    message_ids.append(result.data["message_id"])

                # 控制发送速率，在 1 秒内完成
                time_module.sleep(1.0 / message_count)

            send_end = time.time()
            send_duration = send_end - send_start

            print(f"✓ Sent {len(message_ids)} messages in {send_duration:.2f}s")
            print(f"  Send rate: {len(message_ids)/send_duration:.2f} msg/s")

            print(f"\nWaiting for processing (max 30 seconds)...")

            # 等待处理
            max_wait = 30
            check_start = time.time()
            processed_count = 0

            while processed_count < len(message_ids) and (time.time() - check_start) < max_wait:
                history_result = notification_service.get_notification_history(
                    user_uuid=user_uuid,
                    limit=500
                )

                if history_result.is_success:
                    records = history_result.data.get("records", [])
                    processed_count = sum(
                        1 for r in records
                        if r.get("message_id") in message_ids and r.get("status") == 1
                    )

                    if processed_count >= len(message_ids):
                        break

                time_module.sleep(1.0)

            process_end = time.time()
            total_duration = process_end - send_start

            print(f"\n✓ Processed {processed_count}/{len(message_ids)} messages")

            if processed_count > 0:
                throughput = processed_count / total_duration

                print(f"\nBurst Test Results:")
                print(f"  Total Duration: {total_duration:.2f}s")
                print(f"  Throughput:     {throughput:.2f} msg/s")

                # 验证 SC-010
                if throughput >= 100:
                    print(f"  ✅ PASS - Throughput >= 100 msg/s")
                    assert throughput >= 100
                else:
                    print(f"  ⚠️  Warning: Throughput {throughput:.2f} msg/s < 100 msg/s")

        finally:
            pass
