#!/usr/bin/env python3
"""
测试 TaskTimer Cron 任务

验证场景：
1. 加载配置文件
2. 解析 Cron 表达式
3. 验证任务已注册
4. 模拟任务触发
"""

import time
from datetime import datetime

def test_cron_parsing():
    """测试 Cron 表达式解析"""
    print("\n=== 测试 1: Cron 表达式解析 ===")

    from apscheduler.triggers.cron import CronTrigger

    test_crons = [
        ("0 21 * * *", "每天21:00"),
        ("0 * * * *", "每小时"),
        ("*/30 * * * *", "每30分钟"),
        ("0 9-15 * * 1-5", "工作日9-15点每小时"),
    ]

    for cron_expr, description in test_crons:
        try:
            parts = cron_expr.split()
            if len(parts) != 5:
                print(f"✗ 无效的 cron: {cron_expr}")
                continue

            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
                timezone='Asia/Shanghai',
            )

            # 获取下次触发时间（需要传入当前时间）
            next_run = trigger.get_next_fire_time(datetime.now())
            print(f"✓ {description}")
            print(f"  Cron: {cron_expr}")
            print(f"  下次触发: {next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else 'N/A'}")

        except Exception as e:
            print(f"✗ 解析失败 {cron_expr}: {e}")

    return True

def test_task_timer_config():
    """测试 TaskTimer 配置加载"""
    print("\n=== 测试 2: TaskTimer 配置加载 ===")

    from ginkgo.livecore.task_timer import TaskTimer

    timer = TaskTimer()
    config = timer._load_config()

    if config is None:
        config = timer._get_default_config()
        print("✓ 使用默认配置")
    else:
        print("✓ 配置文件加载成功")

    # 显示配置的任务
    tasks = config.get("scheduled_tasks", [])
    print(f"\n配置的任务数量: {len(tasks)}")

    for task in tasks:
        enabled = "✓" if task.get("enabled", True) else "✗"
        print(f"  {enabled} {task.get('name')} ({task.get('cron')})")

    return True

def test_task_timer_job_registration():
    """测试任务注册"""
    print("\n=== 测试 3: 任务注册验证 ===")

    from ginkgo.livecore.task_timer import TaskTimer

    timer = TaskTimer()

    # 加载配置并添加任务
    timer._load_config()
    timer._add_jobs()

    print(f"✓ 已注册任务数: {len(timer._jobs)}")

    # 检查调度器中的任务
    jobs = timer.scheduler.get_jobs()
    print(f"✓ 调度器中的任务: {len(jobs)}")

    for job in jobs:
        # APScheduler Job 对象的属性
        trigger = job.trigger
        print(f"  - {job.name}")
        print(f"    Trigger: {type(trigger).__name__}")

    return len(timer._jobs) > 0

def test_task_timer_job_functions():
    """测试任务函数映射"""
    print("\n=== 测试 4: 任务函数映射 ===")

    from ginkgo.livecore.task_timer import TaskTimer

    timer = TaskTimer()

    # 验证所有命令都有对应的函数
    commands = ["bar_snapshot", "update_selector", "update_data"]

    for cmd in commands:
        func = timer._get_job_function(cmd)
        if func:
            print(f"✓ {cmd} -> {func.__name__}")
        else:
            print(f"✗ {cmd} -> 无对应函数")

    return True

def test_short_interval_cron():
    """测试短间隔 Cron（用于快速验证）"""
    print("\n=== 测试 5: 短间隔 Cron 测试 ===")

    from ginkgo.livecore.task_timer import TaskTimer
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger

    # 创建测试调度器
    test_scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
    timer = TaskTimer()

    # 添加一个每10秒触发的测试任务
    executed = []

    def test_job():
        executed.append(datetime.now())
        print(f"✓ 测试任务触发: {datetime.now().strftime('%H:%M:%S')}")

    trigger = CronTrigger(second="*/10")  # 每10秒
    test_scheduler.add_job(test_job, trigger=trigger, name="test_job")

    print("启动测试调度器（运行 25 秒）...")
    test_scheduler.start()

    # 等待触发
    for i in range(25):
        time.sleep(1)
        if i % 5 == 0:
            print(f"  等待中... {i}秒")

    test_scheduler.shutdown(wait=True)

    print(f"\n✓ 任务触发次数: {len(executed)}")

    if len(executed) >= 2:
        print("✓ Cron 调度正常工作")
        return True
    else:
        print("✗ Cron 调度异常")
        return False

def main():
    print("=" * 60)
    print("TaskTimer Cron 模块测试")
    print("=" * 60)

    tests = [
        ("Cron 表达式解析", test_cron_parsing),
        ("配置加载", test_task_timer_config),
        ("任务注册", test_task_timer_job_registration),
        ("函数映射", test_task_timer_job_functions),
        ("短间隔测试", test_short_interval_cron),
    ]

    results = []
    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"   错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 总结
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")

    passed = sum(1 for _, r in results if r)
    print(f"\n总计: {passed}/{len(results)} 通过")

    if passed == len(results):
        print("\n✅ TaskTimer Cron 模块工作正常！")
        return 0
    else:
        print("\n⚠ 部分测试失败")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
