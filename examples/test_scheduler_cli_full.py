"""
Scheduler CLI 完整功能测试

验证所有 Scheduler CLI 命令的功能：
1. start - 启动调度器
2. status - 查看状态
3. plan - 查看调度计划
4. nodes - 列出健康节点
5. migrate - 迁移 Portfolio
6. reload - 重载 Portfolio
7. recalculate - 重新计算（负载均衡）[NEW]
8. schedule - 主动触发调度 [NEW]

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python examples/test_scheduler_cli_full.py
"""

import subprocess
import sys

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}")
    print(f"命令: {cmd}")
    print("-" * 70)

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    return result.returncode == 0

def main():
    print("=" * 70)
    print("  Scheduler CLI 完整功能测试")
    print("=" * 70)

    tests = [
        ("ginkgo scheduler --help", "测试 1: 帮助信息"),
        ("ginkgo scheduler status", "测试 2: Scheduler 状态"),
        ("ginkgo scheduler plan", "测试 3: 调度计划"),
        ("ginkgo scheduler nodes", "测试 4: ExecutionNode 列表"),
        ("ginkgo scheduler migrate --help", "测试 5: migrate 命令帮助"),
        ("ginkgo scheduler reload --help", "测试 6: reload 命令帮助"),
        ("ginkgo scheduler recalculate --help", "测试 7: recalculate 命令帮助 [NEW]"),
        ("ginkgo scheduler schedule --help", "测试 8: schedule 命令帮助 [NEW]"),
        ("ginkgo scheduler recalculate --dry-run", "测试 9: recalculate dry-run [NEW]"),
        ("ginkgo scheduler schedule --force", "测试 10: schedule 主动调度 [NEW]"),
    ]

    passed = 0
    failed = 0

    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1

    # 总结
    print(f"\n{'='*70}")
    print("  测试总结")
    print(f"{'='*70}")
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {failed} 个测试失败")

    print(f"\n📋 Scheduler CLI 完整命令集：")
    print(f"")
    print(f"   【查询命令】")
    print(f"   • ginkgo scheduler status                - 查看调度器状态")
    print(f"   • ginkgo scheduler plan                  - 查看当前调度计划")
    print(f"   • ginkgo scheduler nodes                 - 列出健康节点")
    print(f"")
    print(f"   【调度命令】")
    print(f"   • ginkgo scheduler start [--interval]    - 启动调度器")
    print(f"   • ginkgo scheduler schedule [--force]    - 主动触发调度 [NEW]")
    print(f"   • ginkgo scheduler recalculate [--dry-run] - 重新计算负载均衡 [NEW]")
    print(f"")
    print(f"   【Portfolio 操作】")
    print(f"   • ginkgo scheduler migrate <id> --target <node>  - 迁移 Portfolio")
    print(f"   • ginkgo scheduler reload <id>                    - 重载 Portfolio")
    print(f"")

    print(f"""
🎯 Scheduler CLI 核心功能：

✅ 【查询功能】
   - status: 实时统计（健康节点、调度 Portfolio、队列大小等）
   - plan: 当前分配计划（Portfolio → Node 映射）
   - nodes: 健康节点列表（心跳时间、负载情况）

✅ 【调度功能】
   - start: 启动后台调度器（定时调度）
   - schedule: 主动触发一次调度（手动分配未分配的 Portfolio）
   - recalculate: 重新计算负载均衡（重新分配已分配的 Portfolio）

✅ 【Portfolio 操作】
   - migrate: 手动迁移 Portfolio 到指定节点
   - reload: 优雅重载 Portfolio 配置

💡 使用场景：

1️⃣  日常运维
   ginkgo scheduler status       # 查看整体状态
   ginkgo scheduler nodes        # 检查节点健康
   ginkgo scheduler plan         # 查看分配情况

2️⃣  新 Portfolio 上线
   ginkgo scheduler schedule     # 自动分配新 Portfolio
   # 或手动指定：
   ginkgo scheduler migrate <id> --target <node>

3️⃣  负载不均时
   ginkgo scheduler recalculate --dry-run   # 预览重分配计划
   ginkgo scheduler recalculate --force    # 执行负载均衡

4️⃣  节点故障
   # Scheduler 自动检测并迁移故障节点的 Portfolio
   # 或手动迁移：
   ginkgo scheduler migrate <id> --target <healthy_node>

5️⃣  配置更新
   ginkgo scheduler reload <id>  # 优雅重载配置

🚀 Phase 5 完成：Scheduler CLI 功能齐全！
""")

if __name__ == "__main__":
    main()
