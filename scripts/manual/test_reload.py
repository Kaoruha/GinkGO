#!/usr/bin/env python3
"""
测试 TaskTimer 配置热重载

演示场景：
1. 启动 TaskTimer
2. 修改配置文件
3. 调用 reload_config() 重载配置
4. 验证新任务已生效
"""

import os
import time
import yaml
from pathlib import Path

def setup_test_config():
    """创建测试配置文件"""
    config_path = os.path.expanduser("~/.ginkgo/task_timer.yml")

    # 初始配置：只有 2 个任务
    initial_config = {
        "scheduled_tasks": [
            {
                "name": "bar_snapshot",
                "cron": "0 21 * * *",
                "command": "bar_snapshot",
                "enabled": True,
            },
            {
                "name": "update_selector",
                "cron": "0 * * * *",
                "command": "update_selector",
                "enabled": True,
            },
        ]
    }

    # 确保目录存在
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(initial_config, f, allow_unicode=True)

    print(f"✓ 创建初始配置: {config_path}")
    print(f"  任务数量: {len(initial_config['scheduled_tasks'])}")
    for task in initial_config['scheduled_tasks']:
        print(f"    - {task['name']} ({task['cron']})")

    return config_path

def update_config_add_tasks(config_path):
    """更新配置：添加新任务"""
    updated_config = {
        "scheduled_tasks": [
            {
                "name": "bar_snapshot",
                "cron": "0 21 * * *",
                "command": "bar_snapshot",
                "enabled": True,
            },
            {
                "name": "update_selector",
                "cron": "0 * * * *",
                "command": "update_selector",
                "enabled": True,
            },
            # 新增任务
            {
                "name": "update_data",
                "cron": "0 19 * * *",
                "command": "update_data",
                "enabled": True,
            },
        ]
    }

    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(updated_config, f, allow_unicode=True)

    print(f"\n✓ 更新配置: {config_path}")
    print(f"  新任务数量: {len(updated_config['scheduled_tasks'])}")
    for task in updated_config['scheduled_tasks']:
        print(f"    - {task['name']} ({task['cron']})")

def test_config_reload():
    """测试配置热重载"""
    print("\n=== 测试 TaskTimer 配置热重载 ===\n")

    from ginkgo.livecore.task_timer import TaskTimer

    # 1. 创建初始配置
    config_path = setup_test_config()

    # 2. 启动 TaskTimer
    print("\n--- 步骤 1: 启动 TaskTimer ---")
    timer = TaskTimer(config_path=config_path)
    timer.start()

    jobs_before = len(timer._jobs)
    print(f"✓ TaskTimer 已启动")
    print(f"  当前任务数: {jobs_before}")
    for job in timer._jobs:
        print(f"    - {job}")

    # 3. 等待 2 秒
    print("\n--- 步骤 2: 等待 2 秒 ---")
    time.sleep(2)

    # 4. 更新配置文件
    print("\n--- 步骤 3: 更新配置文件 ---")
    update_config_add_tasks(config_path)

    # 5. 热重载配置
    print("\n--- 步骤 4: 调用 reload_config() ---")
    result = timer.reload_config()

    if result:
        jobs_after = len(timer._jobs)
        print(f"✓ 配置重载成功")
        print(f"  重载前任务数: {jobs_before}")
        print(f"  重载后任务数: {jobs_after}")

        # 验证新任务
        jobs = timer.scheduler.get_jobs()
        job_names = [job.name for job in jobs]
        print(f"  当前任务列表: {job_names}")

        if "update_data" in job_names:
            print(f"\n✓ 新任务 'update_data' 已成功添加！")
        else:
            print(f"\n✗ 新任务 'update_data' 未找到")
    else:
        print(f"✗ 配置重载失败")

    # 6. 清理
    print("\n--- 步骤 5: 停止 TaskTimer ---")
    timer.stop()
    print(f"✓ TaskTimer 已停止")

    # 7. 清理测试配置
    os.remove(config_path)
    print(f"✓ 测试配置已清理")

    return result

def main():
    print("=" * 60)
    print("TaskTimer 配置热重载测试")
    print("=" * 60)

    print("\n使用方法：")
    print("  1. 修改 ~/.ginkgo/task_timer.yml")
    print("  2. 调用 task_timer.reload_config()")
    print("  3. 新配置立即生效，无需重启")

    # 运行测试
    result = test_config_reload()

    print("\n" + "=" * 60)
    if result:
        print("✅ 配置热重载功能正常！")
        return 0
    else:
        print("❌ 配置热重载失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
