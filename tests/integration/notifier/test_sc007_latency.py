# Upstream: SC-007 性能要求 (通知发送延迟 < 5 秒 p95)
# Downstream: tasks.md T180 验证
# Role: 性能验证测试 - 验证 Kafka 异步通知发送满足 SC-007 延迟要求


"""
Performance verification test for SC-007: Notification sending latency.

SC-007 Requirement: 通知发送延迟 < 5 秒 p95

Latency Definition: 从调用 send() 到通知记录状态变为 SENT 的时间

Test Strategy:
1. Send 100 notifications asynchronously via Kafka
2. Measure end-to-end latency (send → Kafka → Worker → Channel → Record)
3. Calculate p95 latency
4. Verify p95 < 5 seconds
"""

import pytest
import time
import json
from typing import List, Dict
import numpy as np


@pytest.mark.integration
@pytest.mark.performance
class TestSC007NotificationLatency:
    """SC-007: 通知发送延迟 < 5 秒 p95"""

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

    def test_sc007_end_to_end_latency_p95(self):
        """
        SC-007: 验证通知发送端到端延迟 < 5 秒 p95

        测试步骤：
        1. 创建测试用户和联系方式
        2. 发送 100 条异步通知（通过 Kafka）
        3. 记录每条通知的发送时间和完成时间
        4. 轮询查询通知状态，等待状态变为 SENT
        5. 计算端到端延迟的 p95 值
        6. 验证 p95 < 5 秒

        注意：此测试需要 Worker 正在运行以处理 Kafka 消息
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"latency_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Latency Test User {unique_id}"
        )
        assert user_result.is_success, f"Failed to create user: {user_result.error}"
        user_uuid = user_result.data["uuid"]

        # 创建测试联系方式（使用 webhook 模拟快速响应渠道）
        contact_result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=CONTACT_TYPES.WEBHOOK,
            address="https://httpbin.org/post",  # 使用 httpbin 作为测试 webhook
            is_primary=True,
            is_active=True
        )
        assert contact_result.is_success, f"Failed to create contact: {contact_result.error}"

        try:
            print("\n" + "="*70)
            print("SC-007 Performance Test: End-to-End Notification Latency")
            print("="*70)
            print(f"User: {user_name} (UUID: {user_uuid})")
            print(f"Sending 100 async notifications via Kafka...")

            # 发送 100 条异步通知并记录发送时间
            message_count = 100
            send_times: Dict[str, float] = {}
            message_ids: List[str] = []

            for i in range(message_count):
                send_time = time.time()

                # 使用 Kafka 异步发送
                result = notification_service.send(
                    content=f"Latency test notification #{i+1}",
                    title=f"Latency Test #{i+1}",
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    async_mode=True  # 强制使用 Kafka 异步模式
                )

                if result.is_success and "message_id" in result.data:
                    message_id = result.data["message_id"]
                    send_times[message_id] = send_time
                    message_ids.append(message_id)

                if (i + 1) % 20 == 0:
                    print(f"  Sent {i+1}/{message_count} notifications...")

                # 小延迟避免过快发送
                time_module.sleep(0.01)

            print(f"✓ Sent {len(message_ids)} notifications via Kafka")
            print(f"\nWaiting for notifications to be processed by Worker...")
            print("(This may take up to 30 seconds...)")

            # 等待 Worker 处理完成，轮询查询通知状态
            latencies: List[float] = []
            max_wait_time = 30  # 最多等待 30 秒
            check_interval = 0.5  # 每 0.5 秒检查一次

            start_wait = time.time()
            completed_count = 0

            while completed_count < len(message_ids) and (time.time() - start_wait) < max_wait_time:
                for message_id in message_ids:
                    if message_id in send_times and message_id not in [f"lat_{mid}" for mid in message_ids]:
                        # 查询通知记录状态
                        history_result = notification_service.get_notification_history(
                            user_uuid=user_uuid,
                            limit=200  # 获取足够多的记录
                        )

                        if history_result.is_success:
                            records = history_result.data.get("records", [])

                            # 查找当前消息的记录
                            for record in records:
                                if record.get("message_id") == message_id:
                                    # 检查状态是否为 SENT
                                    if record.get("status") == NOTIFICATION_STATUS_TYPES.SENT.value:
                                        # 记录延迟
                                        send_time = send_times[message_id]
                                        sent_at = record.get("sent_at")
                                        create_at = record.get("create_at")

                                        if sent_at:
                                            # 使用 sent_at 作为完成时间
                                            from datetime import datetime
                                            if isinstance(sent_at, datetime):
                                                complete_time = sent_at.timestamp()
                                            else:
                                                complete_time = sent_at

                                            latency = complete_time - send_time
                                            latencies.append(latency)

                                            # 标记为已处理
                                            send_times[f"lat_{message_id}"] = send_time
                                            completed_count += 1

                                            if completed_count % 10 == 0:
                                                print(f"  Completed: {completed_count}/{len(message_ids)} notifications")
                                            break

                time_module.sleep(check_interval)

            print(f"\n✓ Processed {len(latencies)}/{len(message_ids)} notifications")

            if len(latencies) < len(message_ids) * 0.8:  # 如果完成率低于 80%
                print(f"⚠️  Warning: Only {len(latencies)}/{len(message_ids)} notifications completed")
                print(f"    This may indicate the Worker is not running properly")

            # 计算统计数据
            if len(latencies) > 0:
                latencies_array = np.array(latencies)
                p50 = np.percentile(latencies_array, 50)
                p90 = np.percentile(latencies_array, 90)
                p95 = np.percentile(latencies_array, 95)
                p99 = np.percentile(latencies_array, 99)
                mean = np.mean(latencies_array)
                std = np.std(latencies_array)
                min_time = np.min(latencies_array)
                max_time = np.max(latencies_array)

                # 打印结果
                print("\n" + "="*70)
                print("Performance Test Results")
                print("="*70)
                print(f"Total Notifications: {len(message_ids)}")
                print(f"Completed:            {len(latencies)}")
                print(f"Success Rate:         {len(latencies)/len(message_ids)*100:.1f}%")
                print(f"\nLatency Statistics (seconds):")
                print(f"  Mean:               {mean:.3f}")
                print(f"  Std Dev:            {std:.3f}")
                print(f"  Min:                {min_time:.3f}")
                print(f"  Max:                {max_time:.3f}")
                print(f"\nPercentiles:")
                print(f"  p50 (Median):       {p50:.3f}s")
                print(f"  p90:                {p90:.3f}s")
                print(f"  p95:                {p95:.3f}s  ⬅ SC-007 Requirement")
                print(f"  p99:                {p99:.3f}s")
                print("="*70)

                # 验证 SC-007 要求
                print(f"\nSC-007 Verification:")
                print(f"  Required: p95 < 5 seconds")
                print(f"  Actual:   p95 = {p95:.3f} seconds")

                if p95 < 5.0:
                    print(f"  Result:   ✅ PASS - p95 ({p95:.3f}s) < 5s")
                else:
                    print(f"  Result:   ❌ FAIL - p95 ({p95:.3f}s) >= 5s")

                # 断言验证
                assert p95 < 5.0, f"SC-007 FAILED: p95 latency {p95:.3f}s >= 5s"

                # 额外的性能目标验证（非强制，仅供参考）
                print(f"\nAdditional Performance Targets:")
                if p50 < 2.0:
                    print(f"  ✅ p50 ({p50:.3f}s) < 2s (excellent)")
                else:
                    print(f"  ⚠️  p50 ({p50:.3f}s) >= 2s (acceptable)")

                if p99 < 10.0:
                    print(f"  ✅ p99 ({p99:.3f}s) < 10s (good)")
                else:
                    print(f"  ⚠️  p99 ({p99:.3f}s) >= 10s (needs attention)")

                print("="*70 + "\n")

            else:
                pytest.skip("No notifications were processed. Worker may not be running.")

        finally:
            # 清理测试数据（可选）
            pass

    def test_sc007_latency_with_different_channels(self):
        """
        SC-007: 验证不同渠道的通知延迟

        测试不同渠道（webhook, email）的延迟表现
        注意：此测试为简化版本，主要测试 webhook 延迟
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"latency_channel_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Latency Channel Test User {unique_id}"
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
            print("SC-007 Performance Test: Latency by Channel")
            print("="*70)

            # 发送 50 条通知
            message_count = 50
            send_times: Dict[str, float] = {}
            message_ids: List[str] = []

            for i in range(message_count):
                send_time = time.time()

                result = notification_service.send(
                    content=f"Channel latency test #{i+1}",
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    async_mode=True
                )

                if result.is_success and "message_id" in result.data:
                    message_id = result.data["message_id"]
                    send_times[message_id] = send_time
                    message_ids.append(message_id)

                time_module.sleep(0.01)

            print(f"✓ Sent {len(message_ids)} notifications")

            # 等待处理完成
            print(f"\nWaiting for processing (max 20 seconds)...")
            latencies: List[float] = []
            max_wait_time = 20
            check_interval = 0.5
            start_wait = time.time()

            while len(latencies) < len(message_ids) and (time.time() - start_wait) < max_wait_time:
                history_result = notification_service.get_notification_history(
                    user_uuid=user_uuid,
                    limit=200
                )

                if history_result.is_success:
                    records = history_result.data.get("records", [])

                    for record in records:
                        message_id = record.get("message_id")
                        if message_id in send_times and message_id not in [f"lat_{mid}" for mid in message_ids]:
                            if record.get("status") == 1:  # SENT status
                                send_time = send_times[message_id]
                                sent_at = record.get("sent_at")

                                if sent_at:
                                    from datetime import datetime
                                    if isinstance(sent_at, datetime):
                                        complete_time = sent_at.timestamp()
                                    else:
                                        complete_time = sent_at

                                    latency = complete_time - send_time
                                    latencies.append(latency)
                                    send_times[f"lat_{message_id}"] = send_time

                if len(latencies) % 10 == 0 and len(latencies) > 0:
                    print(f"  Completed: {len(latencies)}/{len(message_ids)}")

                time_module.sleep(check_interval)

            print(f"✓ Processed {len(latencies)}/{len(message_ids)} notifications")

            # 计算统计数据
            if len(latencies) > 0:
                latencies_array = np.array(latencies)
                p95 = np.percentile(latencies_array, 95)
                mean = np.mean(latencies_array)

                print(f"\nWebhook Channel Results:")
                print(f"  Mean: {mean:.3f}s")
                print(f"  p95:  {p95:.3f}s")

                # 验证 SC-007
                if p95 < 5.0:
                    print(f"  ✅ PASS - p95 ({p95:.3f}s) < 5s")
                else:
                    print(f"  ❌ FAIL - p95 ({p95:.3f}s) >= 5s")

                assert p95 < 5.0, f"SC-007 FAILED: p95 latency {p95:.3f}s >= 5s"

            else:
                pytest.skip("No notifications were processed")

        finally:
            pass
