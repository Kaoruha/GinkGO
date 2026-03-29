#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证重构后的测试文件

展示如何使用pytest运行重构后的测试
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"运行: {description}")
    print(f"命令: {cmd}")
    print('='*60)

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("错误:", result.stderr)

    return result.returncode == 0


def main():
    """主函数"""
    print("Ginkgo 数据模型和驱动重构测试验证")
    print("="*60)

    # 切换到项目根目录
    project_root = Path(__file__).parent.parent.parent
    import os
    os.chdir(project_root)

    # 测试场景
    tests = [
        # 1. 运行单个测试
        (
            "pytest test/data/models/test_base_model_pytest.py::TestMBaseConstruction::test_mbase_can_be_instantiated -v",
            "单个测试 - MBase构造"
        ),

        # 2. 运行测试类
        (
            "pytest test/data/models/test_base_model_pytest.py::TestMBaseConstruction -v",
            "测试类 - MBase构造测试"
        ),

        # 3. 运行测试文件
        (
            "pytest test/data/models/test_base_model_pytest.py -v",
            "测试文件 - MBase所有测试"
        ),

        # 4. 运行所有单元测试
        (
            "pytest test/data/models/test_base_model_pytest.py test/data/models/test_clickbase_model_pytest.py -m unit -v",
            "单元测试标记"
        ),

        # 5. 列出所有测试
        (
            "pytest test/data/models/test_base_model_pytest.py --collect-only",
            "列出测试(仅收集)"
        ),

        # 6. 带覆盖率运行
        (
            "pytest test/data/models/test_base_model_pytest.py --cov=src/ginkgo/data/models/model_base --cov-report=term-missing",
            "覆盖率报告"
        ),
    ]

    # 运行测试
    results = []
    for cmd, desc in tests:
        success = run_command(cmd, desc)
        results.append((desc, success))

    # 显示总结
    print("\n" + "="*60)
    print("测试运行总结")
    print("="*60)

    for desc, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status}: {desc}")

    print("\n提示:")
    print("  - 运行所有单元测试: pytest test/data/models/ -m unit")
    print("  - 运行所有测试: pytest test/data/models/")
    print("  - 使用脚本: ./test/data/run_refactored_tests.sh")
    print("  - 查看指南: cat test/data/TEST_REFACTORING_GUIDE.md")


if __name__ == "__main__":
    main()
