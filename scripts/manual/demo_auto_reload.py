#!/usr/bin/env python3
"""
演示：自动配置重载（文件监控方式）

当配置文件被修改时，自动调用 reload_config()
"""

import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigFileHandler(FileSystemEventHandler):
    """配置文件变化监听器"""

    def __init__(self, timer):
        self.timer = timer
        self.last_reload = time.time()
        self.reload_cooldown = 2  # 重载冷却时间（秒）

    def on_modified(self, event):
        """文件被修改时触发"""
        if event.src_path.endswith('task_timer.yml'):
            # 避免频繁重载（冷却时间）
            if time.time() - self.last_reload < self.reload_cooldown:
                return

            print(f"[{time.strftime('%H:%M:%S')}] 检测到配置文件变化，自动重载...")
            result = self.timer.reload_config()

            if result:
                print(f"[{time.strftime('%H:%M:%S')}] ✓ 配置重载成功")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] ✗ 配置重载失败")

            self.last_reload = time.time()

def setup_file_watcher(timer):
    """设置文件监控"""
    config_dir = os.path.expanduser("~/.ginkgo")

    event_handler = ConfigFileHandler(timer)
    observer = Observer()
    observer.schedule(event_handler, config_dir, recursive=False)
    observer.start()

    print(f"✓ 文件监控已启动，监控目录: {config_dir}")
    print("  修改 task_timer.yml 后将自动重载配置")

    return observer

# 使用示例
def main():
    from ginkgo.livecore.task_timer import TaskTimer

    # 启动 TaskTimer
    timer = TaskTimer()
    timer.start()

    # 启动文件监控（后台线程）
    observer = setup_file_watcher(timer)

    try:
        print("\nTaskTimer 运行中，配置文件监控已启动...")
        print("按 Ctrl+C 停止\n")

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止 TaskTimer...")
        timer.stop()
        observer.stop()
        print("✓ 已停止")

if __name__ == "__main__":
    main()
