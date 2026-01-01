#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notification Worker 启动脚本

启动 Kafka 消费者 Worker，从 notifications topic 消费消息并调用相应渠道发送。

Usage:
    python start_notification_worker.py [--group-id GROUP_ID] [--auto-offset earliest|latest]

Example:
    python start_notification_worker.py
    python start_notification_worker.py --group-id custom_worker_group
"""

import signal
import sys
import time
import argparse
from datetime import datetime
from typing import Optional

from ginkgo.notifier.workers.notification_worker import (
    NotificationWorker,
    WorkerStatus,
    create_notification_worker
)
from ginkgo.data.crud import NotificationRecordCRUD
from ginkgo.libs import GLOG


# 全局 Worker 实例
worker: Optional[NotificationWorker] = None
shutdown_requested = False


def signal_handler(signum, frame):
    """
    处理停止信号（SIGINT, SIGTERM）

    Args:
        signum: 信号编号
        frame: 当前栈帧
    """
    global shutdown_requested, worker

    if shutdown_requested:
        GLOG.WARN("Force exit due to repeated signal")
        sys.exit(1)

    shutdown_requested = True
    signal_name = signal.Signals(signum).name
    GLOG.INFO(f"Received {signal_name}, shutting down gracefully...")

    if worker and worker.is_running:
        GLOG.INFO("Stopping worker...")
        stop_start = time.time()
        success = worker.stop(timeout=30.0)

        if success:
            elapsed = time.time() - stop_start
            GLOG.INFO(f"Worker stopped successfully in {elapsed:.2f}s")
        else:
            GLOG.WARN("Worker did not stop within timeout")

    sys.exit(0)


def print_worker_banner():
    """打印 Worker 启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          Ginkgo Notification Worker                           ║
║          Kafka Consumer for Async Notifications                ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_worker_status(worker: NotificationWorker):
    """
    打印 Worker 状态信息

    Args:
        worker: NotificationWorker 实例
    """
    stats = worker.stats
    health = worker.get_health_status()

    print("\n" + "=" * 60)
    print(f"  Worker Status Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"  Status:           {health['status']}")
    print(f"  Is Running:       {health['is_running']}")
    print(f"  Group ID:         {health['group_id']}")
    print(f"  Topic:            {health['topic']}")
    print("-" * 60)
    print(f"  Messages Consumed:    {stats['messages_consumed']:,}")
    print(f"  Messages Sent:        {stats['messages_sent']:,}")
    print(f"  Messages Failed:      {stats['messages_failed']:,}")
    print(f"  Messages Retried:     {stats['messages_retried']:,}")
    print("-" * 60)

    if stats.get('start_time'):
        uptime = stats.get('uptime_seconds', 0)
        hours, remainder = divmod(int(uptime), 3600)
        minutes, seconds = divmod(remainder, 60)
        print(f"  Uptime:            {hours}h {minutes}m {seconds}s")

    if health.get('last_message_time'):
        print(f"  Last Message:      {health['last_message_time']}")

    # 计算成功率
    consumed = stats['messages_consumed']
    if consumed > 0:
        success_rate = (stats['messages_sent'] / consumed) * 100
        print(f"  Success Rate:      {success_rate:.1f}%")

    print("=" * 60 + "\n")


def create_worker(
    group_id: Optional[str] = None,
    auto_offset_reset: str = "earliest"
) -> NotificationWorker:
    """
    创建 NotificationWorker 实例

    Args:
        group_id: Consumer group ID
        auto_offset_reset: Offset 重置策略

    Returns:
        NotificationWorker: Worker 实例
    """
    GLOG.INFO("Initializing NotificationWorker...")

    # 创建 CRUD 实例
    record_crud = NotificationRecordCRUD()

    # 创建 Worker
    worker = create_notification_worker(
        record_crud=record_crud,
        group_id=group_id
    )

    worker._auto_offset_reset = auto_offset_reset

    GLOG.INFO(f"Worker configuration:")
    GLOG.INFO(f"  Group ID:         {worker._group_id}")
    GLOG.INFO(f"  Topic:            {worker.NOTIFICATIONS_TOPIC}")
    GLOG.INFO(f"  Auto Offset Reset: {auto_offset_reset}")

    return worker


def start_worker(worker: NotificationWorker) -> bool:
    """
    启动 Worker

    Args:
        worker: NotificationWorker 实例

    Returns:
        bool: 是否成功启动
    """
    GLOG.INFO("Starting NotificationWorker...")

    if not worker.start():
        GLOG.ERROR("Failed to start worker")
        return False

    GLOG.INFO("✓ Worker started successfully")
    GLOG.info(f"  Status: {worker.status.name}")
    GLOG.info(f"  Thread: {worker._worker_thread.name}")

    return True


def run_worker(
    worker: NotificationWorker,
    status_interval: int = 60,
    initial_delay: int = 5
):
    """
    运行 Worker 主循环（定期输出状态）

    Args:
        worker: NotificationWorker 实例
        status_interval: 状态输出间隔（秒）
        initial_delay: 首次状态输出延迟（秒）
    """
    global shutdown_requested

    # 等待初始延迟
    time.sleep(initial_delay)

    # 首次状态输出
    print_worker_status(worker)

    last_stats_time = time.time()

    # 主循环：定期输出状态
    while not shutdown_requested:
        try:
            time.sleep(1)  # 每秒检查一次

            # 检查 Worker 是否还在运行
            if not worker.is_running:
                GLOG.WARN("Worker is no longer running")
                if worker.status == WorkerStatus.ERROR:
                    GLOG.ERROR("Worker is in ERROR state")
                break

            # 定期输出状态
            current_time = time.time()
            if current_time - last_stats_time >= status_interval:
                print_worker_status(worker)
                last_stats_time = current_time

        except KeyboardInterrupt:
            break
        except Exception as e:
            GLOG.ERROR(f"Error in worker monitoring loop: {e}")
            time.sleep(5)  # 避免紧密循环


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Ginkgo Notification Worker - Kafka Consumer for Async Notifications",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 使用默认配置启动
  python start_notification_worker.py

  # 使用自定义 group_id
  python start_notification_worker.py --group-id my_worker_group

  # 从最新的 offset 开始消费
  python start_notification_worker.py --auto-offset latest

  # 每 30 秒输出一次状态
  python start_notification_worker.py --status-interval 30
        """
    )

    parser.add_argument(
        '--group-id',
        type=str,
        default=None,
        help='Consumer group ID (default: notification_worker_group)'
    )

    parser.add_argument(
        '--auto-offset',
        type=str,
        choices=['earliest', 'latest'],
        default='earliest',
        help='Kafka auto offset reset policy (default: earliest)'
    )

    parser.add_argument(
        '--status-interval',
        type=int,
        default=60,
        help='Status report interval in seconds (default: 60)'
    )

    parser.add_argument(
        '--initial-delay',
        type=int,
        default=5,
        help='Initial status report delay in seconds (default: 5)'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='Ginkgo Notification Worker v1.0.0'
    )

    return parser.parse_args()


def main():
    """主函数"""
    global worker

    # 打印横幅
    print_worker_banner()

    # 解析命令行参数
    args = parse_arguments()

    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    GLOG.INFO("Signal handlers registered (SIGINT, SIGTERM)")

    try:
        # 创建 Worker
        worker = create_worker(
            group_id=args.group_id,
            auto_offset_reset=args.auto_offset
        )

        # 启动 Worker
        if not start_worker(worker):
            GLOG.ERROR("Failed to start worker, exiting...")
            sys.exit(1)

        # 运行 Worker 主循环
        run_worker(
            worker=worker,
            status_interval=args.status_interval,
            initial_delay=args.initial_delay
        )

    except KeyboardInterrupt:
        GLOG.INFO("Received keyboard interrupt")
    except Exception as e:
        GLOG.ERROR(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 清理资源
        if worker and worker.is_running:
            GLOG.INFO("Shutting down worker...")
            worker.stop(timeout=30.0)

        GLOG.INFO("Worker shutdown complete")


if __name__ == "__main__":
    main()
