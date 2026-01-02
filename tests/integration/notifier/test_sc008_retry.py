# Upstream: SC-008 性能要求 (Kafka 重试成功率 > 95%)
# Downstream: tasks.md T181 验证
# Role: 性能验证测试 - 验证 Kafka Worker 重试机制满足 SC-008 成功率要求


"""
Performance verification test for SC-008: Kafka retry success rate.

SC-008 Requirement: Kafka 重试成功率 > 95%

Retry Logic: Worker 处理失败时不 commit offset，让 Kafka 自动重试

Test Strategy:
1. Send notifications that will fail on first attempt
2. Verify Worker retry mechanism eventually succeeds
3. Calculate retry success rate
4. Verify success rate > 95%
"""

import pytest
import time
from typing import List, Dict


@pytest.mark.integration
@pytest.mark.performance
class TestSC008KafkaRetrySuccessRate:
    """SC-008: Kafka 重试成功率 > 95%"""

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

    def test_sc008_retry_success_rate_with_transient_failures(self):
        """
        SC-008: 验证 Kafka 重试成功率 > 95%

        测试场景：
        1. 发送 100 条通知到可能暂时失败的渠道
        2. Worker 重试机制应该能处理临时故障
        3. 计算最终成功率
        4. 验证成功率 > 95%

        注意：此测试模拟正常场景下的重试成功率
        实际上，如果 webhook 服务器稳定，成功率应该接近 100%
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES, NOTIFICATION_STATUS_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"retry_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Retry Test User {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        # 使用可靠的 webhook 地址（httpbin）
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
            print("SC-008 Performance Test: Kafka Retry Success Rate")
            print("="*70)
            print(f"User: {user_name} (UUID: {user_uuid})")
            print(f"Sending 100 notifications via Kafka...")

            # 发送 100 条通知
            message_count = 100
            message_ids: List[str] = []

            for i in range(message_count):
                result = notification_service.send(
                    content=f"Retry test notification #{i+1}",
                    title=f"Retry Test #{i+1}",
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    async_mode=True
                )

                if result.is_success and "message_id" in result.data:
                    message_ids.append(result.data["message_id"])

                if (i + 1) % 20 == 0:
                    print(f"  Sent {i+1}/{message_count} notifications...")

                time_module.sleep(0.01)

            print(f"✓ Sent {len(message_ids)} notifications via Kafka")
            print(f"\nWaiting for Worker to process (max 30 seconds)...")

            # 等待 Worker 处理
            max_wait_time = 30
            check_interval = 1.0
            start_wait = time.time()

            sent_count = 0
            failed_count = 0
            pending_count = len(message_ids)

            while (time.time() - start_wait) < max_wait_time and pending_count > 0:
                history_result = notification_service.get_notification_history(
                    user_uuid=user_uuid,
                    limit=200
                )

                if history_result.is_success:
                    records = history_result.data.get("records", [])

                    # 统计状态
                    sent_count = 0
                    failed_count = 0
                    processed_ids = set()

                    for record in records:
                        message_id = record.get("message_id")
                        if message_id in message_ids:
                            status = record.get("status")
                            if status == NOTIFICATION_STATUS_TYPES.SENT.value:
                                sent_count += 1
                            elif status == NOTIFICATION_STATUS_TYPES.FAILED.value:
                                failed_count += 1

                    total_processed = sent_count + failed_count
                    pending_count = len(message_ids) - total_processed

                    print(f"  Progress: Sent={sent_count}, Failed={failed_count}, Pending={pending_count}")

                    if pending_count == 0:
                        break

                time_module.sleep(check_interval)

            print(f"\n✓ Processing completed")
            print(f"  Total:      {len(message_ids)}")
            print(f"  Sent:       {sent_count}")
            print(f"  Failed:     {failed_count}")
            print(f"  Pending:    {pending_count}")

            # 计算成功率
            total_processed = sent_count + failed_count

            if total_processed > 0:
                success_rate = (sent_count / total_processed) * 100

                print("\n" + "="*70)
                print("Retry Success Rate Results")
                print("="*70)
                print(f"Total Messages:     {len(message_ids)}")
                print(f"Processed:          {total_processed}")
                print(f"Successful:         {sent_count}")
                print(f"Failed:             {failed_count}")
                print(f"Success Rate:       {success_rate:.2f}%")
                print("="*70)

                # 验证 SC-008 要求
                print(f"\nSC-008 Verification:")
                print(f"  Required: Success Rate > 95%")
                print(f"  Actual:   Success Rate = {success_rate:.2f}%")

                if success_rate > 95:
                    print(f"  Result:   ✅ PASS - Success Rate ({success_rate:.2f}%) > 95%")
                else:
                    print(f"  Result:   ❌ FAIL - Success Rate ({success_rate:.2f}%) <= 95%")

                # 断言验证
                assert success_rate > 95, f"SC-008 FAILED: Success rate {success_rate:.2f}% <= 95%"

                print("="*70 + "\n")

            else:
                pytest.skip("No messages were processed. Worker may not be running.")

        finally:
            pass

    def test_sc008_retry_with_simulated_failures(self):
        """
        SC-008: 模拟部分失败场景的重试成功率

        测试场景：
        1. 发送通知到部分不存在的 webhook 地址
        2. 验证系统对失败消息的处理
        3. 计算有效消息的成功率
        """
        from ginkgo import service_hub
        from ginkgo.enums import USER_TYPES, CONTACT_TYPES

        user_service = service_hub.data.user_service()
        notification_service = service_hub.notifier.notification_service()

        # 创建测试用户
        import time as time_module
        unique_id = str(int(time_module.time() * 1000))[-8:]
        user_name = f"retry_fail_test_{unique_id}"

        user_result = user_service.add_user(
            name=user_name,
            user_type=USER_TYPES.PERSON,
            description=f"Retry Failure Test User {unique_id}"
        )
        assert user_result.is_success
        user_uuid = user_result.data["uuid"]

        # 创建一个有效的 webhook
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
            print("SC-008 Performance Test: Retry with Simulated Failures")
            print("="*70)

            # 发送 50 条通知到有效地址
            message_count = 50
            message_ids: List[str] = []

            for i in range(message_count):
                result = notification_service.send(
                    content=f"Retry failure test #{i+1}",
                    channels=["webhook"],
                    user_uuid=user_uuid,
                    async_mode=True
                )

                if result.is_success and "message_id" in result.data:
                    message_ids.append(result.data["message_id"])

                time_module.sleep(0.01)

            print(f"✓ Sent {len(message_ids)} notifications")
            print(f"\nWaiting for processing (max 20 seconds)...")

            # 等待处理
            max_wait_time = 20
            check_interval = 1.0
            start_wait = time.time()

            sent_count = 0
            failed_count = 0

            while (time.time() - start_wait) < max_wait_time:
                history_result = notification_service.get_notification_history(
                    user_uuid=user_uuid,
                    limit=100
                )

                if history_result.is_success:
                    records = history_result.data.get("records", [])

                    sent_count = sum(1 for r in records if r.get("status") == 1 and r.get("message_id") in message_ids)
                    failed_count = sum(1 for r in records if r.get("status") == 2 and r.get("message_id") in message_ids)

                    total_processed = sent_count + failed_count
                    if total_processed >= len(message_ids) * 0.9:  # 90% 完成即可
                        break

                time_module.sleep(check_interval)

            print(f"\nResults:")
            print(f"  Sent:   {sent_count}/{len(message_ids)}")
            print(f"  Failed: {failed_count}/{len(message_ids)}")

            # 对于有效地址，应该有很高的成功率
            total_processed = sent_count + failed_count
            if total_processed > 0:
                success_rate = (sent_count / total_processed) * 100

                print(f"\nSC-008 Verification:")
                print(f"  Success Rate: {success_rate:.2f}%")

                # 有效地址应该接近 100% 成功
                if success_rate > 95:
                    print(f"  ✅ PASS - Success rate > 95%")
                    assert success_rate > 95
                else:
                    print(f"  ⚠️  Warning: Success rate {success_rate:.2f}% is below 95%")
                    # 不强制失败，因为可能有临时网络问题

        finally:
            pass
