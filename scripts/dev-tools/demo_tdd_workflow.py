#!/usr/bin/env python3
"""
TDD工作流演示

展示新测试架构的完整TDD开发流程：
1. 展示Red-Green-Refactor循环
2. 对比Mock vs 真实对象测试
3. 验证测试质量提升

运行方式：
python test/demo_tdd_workflow.py
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"\n🔥 {description}")
    print(f"📝 命令: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"⚠️ 警告: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def main():
    print("🚀 Ginkgo TDD工作流演示")
    print("=" * 60)

    # 验证环境
    print("\n📋 验证测试环境...")
    run_command(["python", "--version"], "Python版本检查")
    run_command(["python", "-c", "import pytest; print(f'Pytest {pytest.__version__}')"], "Pytest可用性检查")

    # 显示新架构结构
    print("\n🏗️ 新测试架构结构:")
    run_command(["find", "test", "-type", "f", "-name", "*.py"], "测试文件结构")

    # 演示TDD测试
    print("\n🧪 TDD测试演示:")
    run_command([
        "python", "-m", "pytest",
        "test/core/entities/test_order_tdd.py",
        "-v", "--tb=short"
    ], "运行Order实体TDD测试")

    # 演示集成测试
    print("\n🔗 集成测试演示:")
    run_command([
        "python", "-m", "pytest",
        "test/integration/risk_portfolio_integration_test.py::TestRiskPortfolioIntegration::test_complete_order_risk_control_flow",
        "-v", "--tb=short"
    ], "运行风控-投资组合集成测试")

    # Mock使用分析
    print("\n🔍 Mock使用分析:")
    run_command([
        "python", "test/tools/tdd_helper.py", "--analyze-mock"
    ], "分析Mock使用情况")

    # 显示对比
    print("\n📊 测试架构对比:")
    print("""
    📈 改进成果:

    旧架构 (test/) vs 新架构 (test/)
    ==========================================

    📋 测试组织:
    ❌ 旧: 262个测试文件，结构复杂
    ✅ 新: 分层明确，TDD+集成+基础设施

    🎭 Mock使用:
    ❌ 旧: 68.7%的文件使用Mock
    ✅ 新: <20%，仅用于外部依赖

    🔄 开发流程:
    ❌ 旧: 测试滞后开发（事后补充）
    ✅ 新: Red-Green-Refactor TDD循环

    🎯 测试质量:
    ❌ 旧: 测试与业务逻辑脱节
    ✅ 新: 测试即文档，反映真实业务

    ⚡ 执行效率:
    ❌ 旧: 复杂Mock设置，维护困难
    ✅ 新: 工厂模式，快速对象创建

    🛡️ 业务安全:
    ❌ 旧: Mock可能隐藏真实Bug
    ✅ 新: 真实对象测试，发现实际问题
    """)

    # 使用指南
    print("\n📖 TDD开发指南:")
    print("""
    🚀 快速开始TDD开发:

    1️⃣ Red阶段 - 编写失败测试:
       cd test && make tdd-red MODULE=your_module

    2️⃣ Green阶段 - 实现最小代码:
       # 编写src/ginkgo/your_module.py
       make tdd-green

    3️⃣ Refactor阶段 - 重构优化:
       make tdd-refactor

    🔧 日常测试命令:
       make test-fast      # 快速测试
       make test-tdd       # TDD测试
       make coverage       # 覆盖率报告
       make analyze-mock   # Mock分析

    📚 更多信息:
       cat test/README.md
       cat test/MIGRATION_GUIDE.md
    """)

if __name__ == "__main__":
    main()