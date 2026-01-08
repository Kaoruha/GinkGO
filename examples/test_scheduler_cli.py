"""
Scheduler CLI 测试脚本

测试 Ginkgo Scheduler CLI 的所有命令：
1. ginkgo scheduler --help
2. ginkgo scheduler status
3. ginkgo scheduler plan
4. ginkgo scheduler nodes
5. ginkgo scheduler migrate (帮助信息)
6. ginkgo scheduler reload (帮助信息)

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python examples/test_scheduler_cli.py
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
    print("  Scheduler CLI 测试")
    print("=" * 70)

    tests = [
        ("ginkgo scheduler --help", "测试 1: 帮助信息"),
        ("ginkgo scheduler status", "测试 2: Scheduler 状态"),
        ("ginkgo scheduler plan", "测试 3: 调度计划"),
        ("ginkgo scheduler nodes", "测试 4: ExecutionNode 列表"),
        ("ginkgo scheduler migrate --help", "测试 5: migrate 命令帮助"),
        ("ginkgo scheduler reload --help", "测试 6: reload 命令帮助"),
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

    print(f"\n📋 可用的 Scheduler CLI 命令：")
    print(f"   • ginkgo scheduler start [--interval] [--debug]")
    print(f"   • ginkgo scheduler status")
    print(f"   • ginkgo scheduler plan")
    print(f"   • ginkgo scheduler nodes")
    print(f"   • ginkgo scheduler migrate <portfolio_id> --target <node>")
    print(f"   • ginkgo scheduler reload <portfolio_id>")

if __name__ == "__main__":
    main()
