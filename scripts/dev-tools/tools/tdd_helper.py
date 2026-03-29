#!/usr/bin/env python3
"""
TDD开发助手工具

提供TDD开发过程中的自动化支持：
1. Red-Green-Refactor流程管理
2. 测试覆盖率监控
3. Mock使用分析
4. TDD度量收集

使用方法：
python test/tools/tdd_helper.py --mode red --module order
python test/tools/tdd_helper.py --mode green --run-tests
python test/tools/tdd_helper.py --coverage-report
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import json
import time
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TDDHelper:
    """TDD开发助手"""

    def __init__(self):
        self.test_dir = PROJECT_ROOT / "test"
        self.src_dir = PROJECT_ROOT / "src"
        self.metrics_file = self.test_dir / "tdd_metrics.json"

    def run_red_phase(self, module: str, no_suggestions: bool = False) -> bool:
        """Red阶段：编写失败测试"""
        print(f"🔴 Red阶段：为模块 {module} 编写失败测试")

        # 检查是否存在测试文件 - 支持新的模块化结构
        module_parts = module.split('_')

        if len(module_parts) >= 3:
            # 模块化路径: trading_entities_position
            main_module, sub_module, class_name = module_parts[:3]
            test_patterns = [
                f"test/{main_module}/{sub_module}/test_{class_name}.py",
                f"test/data/models/test_{class_name}_model.py",
                f"test/data/crud/test_{class_name}_crud.py",
                f"test/integration/test_{class_name}_*.py"
            ]
        else:
            # 传统模式兼容
            test_patterns = [
                f"test/**/test_{module}.py",
                f"test/**/test_{module}_*.py",
                f"test/integration/**/test_{module}_*.py"
            ]

        found_tests = []
        for pattern in test_patterns:
            found_tests.extend(list(PROJECT_ROOT.glob(pattern)))

        if not found_tests:
            print(f"❌ 未找到模块 {module} 的TDD测试文件")
        else:
            print(f"✅ 找到 {len(found_tests)} 个测试文件:")
            for test_file in found_tests:
                print(f"   - {test_file.relative_to(PROJECT_ROOT)}")

        # 根据参数决定是否提供创建建议
        if not no_suggestions:
            self._suggest_test_creation(module, found_tests)
        else:
            print("🔧 已跳过文件创建建议")

        if found_tests:
            # 运行测试验证它们失败
            return self._run_tests_expect_failure(found_tests)
        else:
            return True

    def run_green_phase(self, run_tests: bool = True) -> bool:
        """Green阶段：实现最小可用代码"""
        print("🟢 Green阶段：运行测试验证实现")

        if run_tests:
            success = self._run_all_tdd_tests()
            # Green阶段：即使测试失败也返回成功，因为这是开发过程的一部分
            print("💡 提示：如果测试失败，请继续实现代码直到测试通过")
            return True

        print("提示：实现最小可用代码，然后运行 --mode green --run-tests")
        return True

    def run_refactor_phase(self) -> bool:
        """Refactor阶段：重构代码保持测试通过"""
        print("🔄 Refactor阶段：重构并验证测试仍然通过")

        # 运行完整测试套件
        success = self._run_all_tdd_tests()

        if success:
            # 运行代码质量检查
            self._run_code_quality_checks()

        return success

    def generate_coverage_report(self) -> bool:
        """生成测试覆盖率报告"""
        print("📊 生成测试覆盖率报告")

        try:
            # 运行覆盖率测试
            cmd = [
                "python", "-m", "pytest",
                "test/",
                "--cov=src/ginkgo",
                "--cov-report=html:test/htmlcov",
                "--cov-report=term-missing",
                "-q"
            ]

            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ 覆盖率报告已生成: test/htmlcov/index.html")
                self._analyze_coverage_report(result.stdout)
                return True
            else:
                print(f"❌ 生成覆盖率报告失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 覆盖率分析错误: {e}")
            return False

    def analyze_mock_usage(self) -> Dict:
        """分析Mock使用情况"""
        print("🔍 分析Mock使用情况")

        mock_analysis = {
            "total_test_files": 0,
            "files_with_mock": 0,
            "mock_usage_ratio": 0.0,
            "mock_patterns": {},
            "recommendations": []
        }

        # 扫描测试文件
        test_files = list(self.test_dir.glob("**/*.py"))
        mock_usage = {}

        for test_file in test_files:
            if test_file.name.startswith("test_"):
                mock_analysis["total_test_files"] += 1

                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 检测Mock使用模式
                    mock_patterns = [
                        "from unittest.mock import",
                        "@patch(",
                        "@mock.patch",
                        "Mock(",
                        "MagicMock(",
                        ".return_value =",
                        "mock_"
                    ]

                    file_mock_count = 0
                    for pattern in mock_patterns:
                        file_mock_count += content.count(pattern)

                    if file_mock_count > 0:
                        mock_analysis["files_with_mock"] += 1
                        mock_usage[str(test_file.relative_to(self.test_dir))] = file_mock_count

                except Exception as e:
                    print(f"警告：无法读取文件 {test_file}: {e}")

        # 计算统计信息
        if mock_analysis["total_test_files"] > 0:
            mock_analysis["mock_usage_ratio"] = mock_analysis["files_with_mock"] / mock_analysis["total_test_files"]

        mock_analysis["mock_patterns"] = mock_usage

        # 生成建议
        if mock_analysis["mock_usage_ratio"] > 0.5:
            mock_analysis["recommendations"].append("Mock使用率过高，考虑使用更多集成测试")

        if mock_analysis["mock_usage_ratio"] > 0.7:
            mock_analysis["recommendations"].append("严重依赖Mock，建议重构为测试真实对象交互")

        # 显示结果
        print(f"📈 Mock使用分析结果:")
        print(f"   总测试文件: {mock_analysis['total_test_files']}")
        print(f"   使用Mock文件: {mock_analysis['files_with_mock']}")
        print(f"   Mock使用率: {mock_analysis['mock_usage_ratio']:.1%}")

        if mock_analysis["recommendations"]:
            print("💡 建议:")
            for rec in mock_analysis["recommendations"]:
                print(f"   - {rec}")

        return mock_analysis

    def collect_tdd_metrics(self) -> Dict:
        """收集TDD度量数据"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "test_counts": self._count_tests(),
            "coverage": self._get_coverage_metrics(),
            "mock_usage": self.analyze_mock_usage(),
            "test_execution_time": self._measure_test_execution_time(),
            "red_green_refactor_cycles": self._count_tdd_cycles()
        }

        # 保存度量数据
        try:
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(metrics, f, indent=2, ensure_ascii=False)

            print(f"📊 TDD度量数据已保存: {self.metrics_file}")

        except Exception as e:
            print(f"❌ 保存度量数据失败: {e}")

        return metrics

    def _run_tests_expect_failure(self, test_files: List[Path]) -> bool:
        """运行测试期望失败（Red阶段验证）"""
        print("验证测试失败...")

        failed_count = 0
        for test_file in test_files:
            cmd = ["python", "-m", "pytest", str(test_file), "-v", "--tb=short"]
            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)

            if result.returncode != 0:
                failed_count += 1
                print(f"✅ {test_file.name} - 测试按预期失败")
            else:
                print(f"⚠️ {test_file.name} - 测试意外通过")

        if failed_count == len(test_files):
            print("🔴 Red阶段验证成功：所有测试都失败了")
        else:
            print("⚠️ Red阶段提醒：某些测试意外通过，请检查测试内容")
            print("💡 提示：Red阶段期望测试失败，如果通过请确认测试逻辑是否正确")

        # Red阶段总是返回成功，让开发流程继续
        return True

    def _run_all_tdd_tests(self) -> bool:
        """运行所有TDD测试"""
        cmd = [
            "python", "-m", "pytest",
            "test/",
            "-m", "tdd",
            "-v",
            "--tb=short"
        ]

        print("运行TDD测试...")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)

        if result.returncode == 0:
            print("✅ 所有TDD测试通过")
            return True
        else:
            print("❌ TDD测试失败")
            return False

    def _run_code_quality_checks(self):
        """运行代码质量检查"""
        print("🔍 运行代码质量检查...")

        # 检查是否有代码格式化工具
        quality_tools = [
            ("flake8", ["flake8", "src/"]),
            ("black", ["black", "--check", "src/"]),
            ("isort", ["isort", "--check-only", "src/"])
        ]

        for tool_name, cmd in quality_tools:
            try:
                result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {tool_name} 检查通过")
                else:
                    print(f"⚠️ {tool_name} 发现问题")
            except FileNotFoundError:
                print(f"ℹ️ {tool_name} 未安装，跳过检查")

    def _suggest_test_creation(self, module: str, existing_files: list = None):
        """建议创建测试文件 - 基于Ginkgo模块结构"""
        existing_files = existing_files or []
        existing_paths = {str(f.relative_to(PROJECT_ROOT)) for f in existing_files}

        # 解析模块路径，支持如: trading_entities_position, data_models_position
        module_parts = module.split('_')

        if len(module_parts) >= 2:
            # 模块化路径: trading_entities_position -> trading/entities/test_position.py
            main_module = module_parts[0]  # trading
            sub_module = module_parts[1]   # entities
            class_name = module_parts[2] if len(module_parts) > 2 else "component"  # position

            suggestions = [
                f"test/{main_module}/{sub_module}/test_{class_name}.py - {class_name}核心功能测试",
            ]

            # 根据模块类型添加额外建议
            if main_module == "trading" and sub_module == "entities":
                suggestions.extend([
                    f"test/data/models/test_{class_name}_model.py - {class_name}数据模型测试",
                    f"test/data/crud/test_{class_name}_crud.py - {class_name}数据操作测试",
                    f"test/integration/test_{class_name}_integration.py - {class_name}集成测试"
                ])
            elif main_module == "trading" and "risk" in sub_module:
                suggestions.append(f"test/integration/test_{class_name}_risk_integration.py - 风控集成测试")
            elif main_module == "libs":
                # libs模块测试建议
                if sub_module == "core":
                    suggestions.extend([
                        f"test/integration/test_{class_name}_libs_integration.py - {class_name}核心库集成测试"
                    ])
                elif sub_module == "containers":
                    suggestions.extend([
                        f"test/integration/test_{class_name}_container_integration.py - {class_name}容器集成测试"
                    ])
            elif main_module == "features":
                # features模块测试建议
                if sub_module == "engines":
                    suggestions.extend([
                        f"test/integration/test_{class_name}_feature_integration.py - {class_name}特征引擎集成测试"
                    ])
                elif sub_module == "services":
                    suggestions.extend([
                        f"test/integration/test_{class_name}_service_integration.py - {class_name}特征服务集成测试"
                    ])
            elif main_module == "data":
                # data模块测试建议
                if sub_module == "drivers":
                    suggestions.extend([
                        f"test/integration/test_{class_name}_driver_integration.py - {class_name}数据驱动集成测试"
                    ])
                elif sub_module == "streaming":
                    suggestions.extend([
                        f"test/integration/test_{class_name}_streaming_integration.py - {class_name}流式数据集成测试"
                    ])
            elif main_module == "quant_ml":
                # 量化ML模块测试建议
                suggestions.extend([
                    f"test/integration/test_{class_name}_ml_integration.py - {class_name}机器学习集成测试"
                ])
            elif main_module == "client":
                # CLI客户端测试建议
                suggestions.extend([
                    f"test/integration/test_{class_name}_cli_integration.py - {class_name}CLI集成测试"
                ])

        else:
            # 传统模式兼容
            suggestions = [
                f"test/trading/entities/test_{module}.py - {module}实体测试",
                f"test/data/models/test_{module}_model.py - {module}模型测试",
                f"test/integration/test_{module}_integration.py - {module}集成测试"
            ]

        # 过滤出不存在的文件
        new_suggestions = []
        for suggestion in suggestions:
            file_path = suggestion.split(' - ')[0]
            if file_path not in existing_paths:
                new_suggestions.append(suggestion)

        if new_suggestions:
            print("💡 建议创建以下测试文件:")
            for i, suggestion in enumerate(new_suggestions, 1):
                print(f"   {i}. {suggestion}")

            # 交互式创建选项
            print("\n选择要创建的文件 (输入数字，多个用逗号分隔，或按回车跳过):")
            try:
                user_input = input(">>> ").strip()
                if user_input:
                    self._create_selected_files(user_input, new_suggestions)
            except (KeyboardInterrupt, EOFError):
                print("\n跳过文件创建")
        else:
            print("✅ 所有推荐的测试文件都已存在")

    def _create_selected_files(self, user_input: str, suggestions: list):
        """根据用户选择创建测试文件"""
        try:
            # 解析用户输入
            selections = [int(x.strip()) for x in user_input.split(',')]

            for selection in selections:
                if 1 <= selection <= len(suggestions):
                    suggestion = suggestions[selection - 1]
                    # 提取文件路径 (去掉描述部分)
                    file_path = suggestion.split(' - ')[0].replace('test/', '')
                    self._create_test_file(file_path, suggestion)
                else:
                    print(f"❌ 无效选择: {selection}")

        except ValueError:
            print("❌ 输入格式错误，请输入数字")

    def _create_test_file(self, file_path: str, description: str):
        """创建单个测试文件"""
        full_path = self.test_dir / file_path

        # 创建目录
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件
        if not full_path.exists():
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(self._get_test_template(file_path))
            print(f"✅ 已创建: {file_path}")
        else:
            print(f"ℹ️ 文件已存在: {file_path}")

    def _get_test_template(self, file_path: str) -> str:
        """获取测试文件模板"""
        class_name = file_path.split('/')[-1].replace('test_', '').replace('.py', '')

        template = f'''"""
{class_name}测试

TDD驱动开发测试文件
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))


class Test{class_name.title()}TDD:
    """{class_name}类TDD测试套件"""

    def test_{class_name.lower()}_placeholder(self):
        """
        占位测试 - 请根据需求编写具体测试
        """
        # TODO: 编写具体测试用例
        assert True  # 临时占位
'''
        return template

    def _count_tests(self) -> Dict:
        """统计测试数量"""
        counts = {"total": 0, "tdd": 0, "integration": 0, "unit": 0}

        test_files = list(self.test_dir.glob("**/*.py"))
        for test_file in test_files:
            if test_file.name.startswith("test_"):
                counts["total"] += 1

                # 统计测试类型
                if "_tdd.py" in test_file.name:
                    counts["tdd"] += 1
                elif "integration" in str(test_file):
                    counts["integration"] += 1
                else:
                    counts["unit"] += 1

        return counts

    def _get_coverage_metrics(self) -> Dict:
        """获取覆盖率度量"""
        # 这里可以解析coverage.py的输出
        return {"coverage_percentage": 0, "uncovered_lines": 0}

    def _measure_test_execution_time(self) -> float:
        """测量测试执行时间"""
        start_time = time.time()

        cmd = ["python", "-m", "pytest", "test/", "-q", "--tb=no"]
        subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True)

        return time.time() - start_time

    def _count_tdd_cycles(self) -> int:
        """统计TDD循环次数（从git提交历史分析）"""
        try:
            cmd = ["git", "log", "--oneline", "--grep=TDD", "--grep=Red", "--grep=Green", "--grep=Refactor"]
            result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
            return len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        except:
            return 0

    def _analyze_coverage_report(self, coverage_output: str):
        """分析覆盖率报告"""
        lines = coverage_output.split('\n')
        for line in lines:
            if "TOTAL" in line:
                print(f"📊 {line}")
                break


def main():
    parser = argparse.ArgumentParser(description="TDD开发助手工具")
    parser.add_argument("--mode", choices=["red", "green", "refactor"], help="TDD阶段")
    parser.add_argument("--module", help="模块名称（用于Red阶段）")
    parser.add_argument("--no-suggestions", action="store_true", help="跳过文件创建建议")
    parser.add_argument("--run-tests", action="store_true", help="运行测试")
    parser.add_argument("--coverage-report", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--analyze-mock", action="store_true", help="分析Mock使用")
    parser.add_argument("--collect-metrics", action="store_true", help="收集TDD度量")

    args = parser.parse_args()

    helper = TDDHelper()

    if args.mode == "red":
        if not args.module:
            print("❌ Red阶段需要指定--module参数")
            sys.exit(1)
        success = helper.run_red_phase(args.module, args.no_suggestions)
        sys.exit(0 if success else 1)

    elif args.mode == "green":
        success = helper.run_green_phase(args.run_tests)
        sys.exit(0 if success else 1)

    elif args.mode == "refactor":
        success = helper.run_refactor_phase()
        sys.exit(0 if success else 1)

    elif args.coverage_report:
        success = helper.generate_coverage_report()
        sys.exit(0 if success else 1)

    elif args.analyze_mock:
        helper.analyze_mock_usage()
        sys.exit(0)

    elif args.collect_metrics:
        helper.collect_tdd_metrics()
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()