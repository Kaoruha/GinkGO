#!/usr/bin/env python3
"""
TaskTimer启动脚本

启动定时任务调度器，支持：
- 每分钟心跳测试（Discord通知）
- 每小时Selector更新
- 每天21:00 K线快照

使用方式:
    python start_task_timer.py

配置文件: ~/.ginkgo/task_timer.yml
"""

import sys
import signal
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from ginkgo.livecore.task_timer import TaskTimer


def main():
    """启动TaskTimer"""
    timer = TaskTimer()

    # 信号处理
    def signal_handler(signum, frame):
        print("\n\nReceived signal, stopping TaskTimer...")
        timer.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动
    print("Starting TaskTimer...")
    print("Configuration: ~/.ginkgo/task_timer.yml")
    print()

    success = timer.start()

    if not success:
        print("[ERROR] Failed to start TaskTimer")
        sys.exit(1)

    print()
    print("TaskTimer is running. Press Ctrl+C to stop.")
    print()

    # 保持运行
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping TaskTimer...")
        timer.stop()
        print("TaskTimer stopped.")


if __name__ == "__main__":
    main()
