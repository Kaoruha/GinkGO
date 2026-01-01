#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notification 测试消息发送脚本

向 Kafka 发送测试消息，用于验证 NotificationWorker 功能。

Usage:
    python send_test_notification.py [--type TYPE] [--count COUNT]

Example:
    python send_test_notification.py --type webhook --count 5
"""

import argparse
import sys
import time
from datetime import datetime

from ginkgo.notifier.core.message_queue import MessageQueue
from ginkgo.libs import GLOG


def send_webhook_notification(queue: MessageQueue, index: int):
    """发送 Webhook 测试通知"""
    return queue.send_notification(
        content=f"测试消息 #{index} - {datetime.now().strftime('%H:%M:%S')}",
        channels=["webhook"],
        title="🔔 Webhook 测试通知",
        user_uuid="test-user",
        webhook_url="https://discord.com/api/webhooks/xxx/yyy",
        color=0x5865F2  # Discord 蓝色
    )


def send_email_notification(queue: MessageQueue, index: int):
    """发送 Email 测试通知"""
    return queue.send_notification(
        content=f"测试邮件 #{index}\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        channels=["email"],
        title="📧 Email 测试通知",
        user_uuid="test-user",
        to="test@example.com"
    )


def send_multi_channel_notification(queue: MessageQueue, index: int):
    """发送多渠道测试通知"""
    return queue.send_notification(
        content=f"多渠道测试消息 #{index} - {datetime.now().strftime('%H:%M:%S')}",
        channels=["webhook", "email"],
        title="📢 多渠道测试通知",
        user_uuid="test-user",
        webhook_url="https://discord.com/api/webhooks/xxx/yyy",
        to="test@example.com"
    )


def send_trading_signal(queue: MessageQueue, index: int):
    """发送交易信号通知"""
    symbols = ["AAPL", "GOOGL", "TSLA", "MSFT", "AMZN"]
    symbol = symbols[index % len(symbols)]

    return queue.send_notification(
        content=f"📈 {symbol} 突破关键位，建议关注",
        channels=["webhook"],
        title=f"交易信号: {symbol}",
        user_uuid="trader-001",
        webhook_url="https://discord.com/api/webhooks/xxx/yyy",
        color=0x00FF00  # 绿色
    )


def send_system_alert(queue: MessageQueue, index: int):
    """发送系统告警通知"""
    return queue.send_notification(
        content=f"⚠️ 检测到异常活动 #{index}\n\n请立即检查系统状态",
        channels=["webhook"],
        title="🚨 系统告警",
        user_uuid="admin",
        webhook_url="https://discord.com/api/webhooks/xxx/yyy",
        color=0xFF0000  # 红色
    )


def print_banner(message_type: str, count: int):
    """打印横幅"""
    print("\n" + "=" * 60)
    print(f"  发送测试消息: {message_type}")
    print(f"  数量: {count}")
    print("=" * 60 + "\n")


def send_notifications(
    message_type: str,
    count: int,
    delay: float = 1.0
):
    """
    发送测试通知

    Args:
        message_type: 消息类型
        count: 发送数量
        delay: 发送间隔（秒）
    """
    # 创建消息队列
    GLOG.INFO("Creating MessageQueue...")
    queue = MessageQueue()

    # 检查 Kafka 可用性
    if not queue.is_available:
        GLOG.ERROR("Kafka is not available! Please check:")
        GLOG.ERROR("  1. Kafka is running: docker ps | grep kafka")
        GLOG.ERROR("  2. Configuration is correct: ginkgo system config show")
        sys.exit(1)

    GLOG.INFO("✓ Kafka is available")

    # 打印横幅
    print_banner(message_type, count)

    # 选择发送函数
    senders = {
        "webhook": send_webhook_notification,
        "email": send_email_notification,
        "multi": send_multi_channel_notification,
        "trading": send_trading_signal,
        "alert": send_system_alert
    }

    sender = senders.get(message_type, send_webhook_notification)

    # 发送消息
    success_count = 0
    failure_count = 0
    start_time = time.time()

    for i in range(1, count + 1):
        try:
            success = sender(queue, i)

            if success:
                success_count += 1
                print(f"  [{i}/{count}] ✓ 发送成功")
            else:
                failure_count += 1
                print(f"  [{i}/{count}] ✗ 发送失败")

        except Exception as e:
            failure_count += 1
            print(f"  [{i}/{count}] ✗ 发送异常: {e}")

        # 间隔
        if i < count and delay > 0:
            time.sleep(delay)

    # 统计结果
    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("  发送完成")
    print("=" * 60)
    print(f"  总计:     {count}")
    print(f"  成功:     {success_count}")
    print(f"  失败:     {failure_count}")
    print(f"  成功率:   {(success_count/count*100):.1f}%")
    print(f"  总耗时:   {elapsed:.2f}s")
    print(f"  平均:     {(elapsed/count):.3f}s/条")
    print("=" * 60 + "\n")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Ginkgo Notification 测试消息发送工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
消息类型:
  webhook   - Webhook 通知（Discord）
  email     - Email 通知
  multi     - 多渠道通知（Webhook + Email）
  trading   - 交易信号通知
  alert     - 系统告警通知

Examples:
  # 发送 5 条 Webhook 测试消息
  python send_test_notification.py --type webhook --count 5

  # 发送 10 条交易信号，间隔 0.5 秒
  python send_test_notification.py --type trading --count 10 --delay 0.5

  # 快速发送（无间隔）
  python send_test_notification.py --type webhook --count 100 --delay 0
        """
    )

    parser.add_argument(
        '--type',
        type=str,
        choices=['webhook', 'email', 'multi', 'trading', 'alert'],
        default='webhook',
        help='消息类型 (default: webhook)'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=5,
        help='发送数量 (default: 5)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='发送间隔秒数 (default: 1.0, use 0 for no delay)'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║          Ginkgo Notification Test Sender                   ║")
    print("║          Kafka 测试消息发送工具                             ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    try:
        send_notifications(
            message_type=args.type,
            count=args.count,
            delay=args.delay
        )

    except KeyboardInterrupt:
        print("\n\n发送被中断")
        sys.exit(1)
    except Exception as e:
        GLOG.ERROR(f"Error sending notifications: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
