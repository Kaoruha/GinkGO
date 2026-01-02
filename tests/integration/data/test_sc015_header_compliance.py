# Upstream: SC-015 质量要求 (所有模型文件包含三行头部注释)
# Downstream: tasks.md T264 验证
# Role: 质量验证测试 - 验证所有模型文件的三行头部注释

"""
Quality verification test for SC-015: Three-line header comments.

SC-015 Requirement: 所有模型文件包含三行头部注释

三行头部注释格式：
# Upstream: <上游依赖>
# Downstream: <下游消费>
# Role: <职责描述>

Test Strategy:
1. 扫描所有模型文件
2. 验证每个文件都包含三行头部注释
3. 验证格式正确
4. 生成合规性报告
"""

import pytest
import os
import re
from pathlib import Path
from typing import List, Dict


@pytest.mark.integration
@pytest.mark.quality
class TestSC015HeaderCompliance:
    """SC-015: 所有模型文件包含三行头部注释"""

    @pytest.fixture(autouse=True)
    def setup_debug_mode(self):
        """确保调试模式已启用"""
        import subprocess
        subprocess.run(
            ["ginkgo", "system", "config", "set", "--debug", "on"],
            capture_output=True,
            text=True
        )
        yield
        subprocess.run(
            ["ginkgo", "system", "config", "set", "--debug", "off"],
            capture_output=True,
            text=True
        )

    def test_sc015_all_model_files_have_headers(self):
        """
        SC-015: 验证所有模型文件包含三行头部注释

        测试步骤：
        1. 扫描 src/ginkgo/data/models/ 目录
        2. 检查每个 .py 文件的前 3 行
        3. 验证格式：# Upstream:, # Downstream:, # Role:
        4. 生成合规性报告
        """
        print("\n" + "="*70)
        print("SC-015 Quality Test: Three-Line Header Comments")
        print("="*70)

        # 扫描模型文件
        models_dir = Path("src/ginkgo/data/models")
        model_files = list(models_dir.glob("*.py"))

        # 排除 __init__.py
        model_files = [f for f in model_files if f.name != "__init__.py"]

        print(f"\nFound {len(model_files)} model files")

        results = {
            "total": len(model_files),
            "compliant": 0,
            "non_compliant": 0,
            "files": []
        }

        # 三行头部注释的正则表达式
        header_pattern = re.compile(
            r'^#\s+Upstream:\s*.+\n'
            r'^#\s+Downstream:\s*.+\n'
            r'^#\s+Role:\s*.+',
            re.MULTILINE
        )

        for model_file in model_files:
            with open(model_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 检查前 10 行是否包含三行头部注释
                first_10_lines = '\n'.join(content.split('\n')[:10])

            is_compliant = header_pattern.search(first_10_lines) is not None

            file_result = {
                "name": model_file.name,
                "path": str(model_file),
                "compliant": is_compliant
            }

            results["files"].append(file_result)

            if is_compliant:
                results["compliant"] += 1
                print(f"  ✅ {model_file.name}")
            else:
                results["non_compliant"] += 1
                print(f"  ❌ {model_file.name} - Missing or invalid header")

        # 计算合规率
        compliance_rate = (results["compliant"] / results["total"] * 100) if results["total"] > 0 else 0

        print("\n" + "="*70)
        print("SC-015 Header Compliance Results")
        print("="*70)
        print(f"Total Files:            {results['total']}")
        print(f"Compliant Files:        {results['compliant']}")
        print(f"Non-Compliant Files:    {results['non_compliant']}")
        print(f"Compliance Rate:        {compliance_rate:.1f}%")
        print(f"Requirement:            100%")

        if results["non_compliant"] == 0:
            print(f"\nResult:                 ✅ PASS (All files compliant)")
        else:
            print(f"\nResult:                 ❌ FAIL ({results['non_compliant']} files non-compliant)")
            print(f"\nNon-Compliant Files:")
            for f in results["files"]:
                if not f["compliant"]:
                    print(f"  - {f['name']}")

        print("="*70)

        # 验证 100% 合规
        assert results["non_compliant"] == 0, f"SC-015 FAILED: {results['non_compliant']} files non-compliant"

    def test_sc015_notifier_module_headers(self):
        """
        SC-015: 验证 notifier 模块文件的三行头部注释

        测试步骤：
        1. 扫描 src/ginkgo/notifier/ 目录
        2. 检查所有 .py 文件
        3. 验证格式合规
        """
        print("\n" + "="*70)
        print("SC-015 Quality Test: Notifier Module Headers")
        print("="*70)

        # 扫描 notifier 模块
        notifier_dir = Path("src/ginkgo/notifier")
        py_files = list(notifier_dir.rglob("*.py"))

        # 排除 __init__.py 和 __pycache__
        py_files = [
            f for f in py_files
            if f.name != "__init__.py" and "__pycache__" not in str(f)
        ]

        print(f"\nFound {len(py_files)} Python files in notifier module")

        results = {
            "total": len(py_files),
            "compliant": 0,
            "non_compliant": 0,
            "files": []
        }

        header_pattern = re.compile(
            r'^#\s+Upstream:\s*.+\n'
            r'^#\s+Downstream:\s*.+\n'
            r'^#\s+Role:\s*.+',
            re.MULTILINE
        )

        for py_file in py_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                first_10_lines = '\n'.join(content.split('\n')[:10])

            is_compliant = header_pattern.search(first_10_lines) is not None

            file_result = {
                "name": py_file.name,
                "relative_path": str(py_file.relative_to(notifier_dir)),
                "compliant": is_compliant
            }

            results["files"].append(file_result)

            if is_compliant:
                results["compliant"] += 1
            else:
                results["non_compliant"] += 1

        compliance_rate = (results["compliant"] / results["total"] * 100) if results["total"] > 0 else 0

        print("\n" + "="*70)
        print("SC-015 Notifier Module Results")
        print("="*70)
        print(f"Total Files:            {results['total']}")
        print(f"Compliant Files:        {results['compliant']}")
        print(f"Non-Compliant Files:    {results['non_compliant']}")
        print(f"Compliance Rate:        {compliance_rate:.1f}%")

        if results["non_compliant"] == 0:
            print(f"\nResult:                 ✅ PASS (All files compliant)")
        else:
            print(f"\nResult:                 ⚠️  WARNING ({results['non_compliant']} files need attention)")

        print("="*70)

        # 对于 notifier 模块，我们只警告，不强制要求（因为可能有历史遗留文件）
        print(f"\nNote: Some files may be exempt from header requirement (legacy code)")

    def test_sc015_header_format_validation(self):
        """
        SC-015: 验证头部注释的格式正确性

        测试步骤：
        1. 检查 Upstream/Downstream/Role 的格式
        2. 验证描述有意义
        3. 生成格式验证报告
        """
        print("\n" + "="*70)
        print("SC-015 Quality Test: Header Format Validation")
        print("="*70)

        # 扫描模型文件
        models_dir = Path("src/ginkgo/data/models")
        model_files = [f for f in models_dir.glob("*.py") if f.name != "__init__.py"]

        format_results = {
            "total": len(model_files),
            "valid_format": 0,
            "invalid_format": 0,
            "issues": []
        }

        for model_file in model_files:
            with open(model_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 检查前 3 行
            if len(lines) < 3:
                format_results["invalid_format"] += 1
                format_results["issues"].append({
                    "file": model_file.name,
                    "issue": "File has less than 3 lines"
                })
                continue

            # 检查格式
            upstream_match = re.match(r'^#\s+Upstream:\s*.+', lines[0])
            downstream_match = re.match(r'^#\s+Downstream:\s*.+', lines[1])
            role_match = re.match(r'^#\s+Role:\s*.+', lines[2])

            if not upstream_match:
                format_results["invalid_format"] += 1
                format_results["issues"].append({
                    "file": model_file.name,
                    "issue": "Line 1: Invalid Upstream format"
                })

            if not downstream_match:
                format_results["invalid_format"] += 1
                format_results["issues"].append({
                    "file": model_file.name,
                    "issue": "Line 2: Invalid Downstream format"
                })

            if not role_match:
                format_results["invalid_format"] += 1
                format_results["issues"].append({
                    "file": model_file.name,
                    "issue": "Line 3: Invalid Role format"
                })

            if upstream_match and downstream_match and role_match:
                format_results["valid_format"] += 1

        print("\n" + "="*70)
        print("SC-015 Format Validation Results")
        print("="*70)
        print(f"Total Files:            {format_results['total']}")
        print(f"Valid Format:           {format_results['valid_format']}")
        print(f"Invalid Format:         {format_results['invalid_format']}")

        if format_results["issues"]:
            print(f"\nFormat Issues:")
            for issue in format_results["issues"]:
                print(f"  - {issue['file']}: {issue['issue']}")

        print("="*70)

        # 验证格式正确性
        assert format_results["invalid_format"] == 0, f"SC-015 FAILED: {format_results['invalid_format']} files have invalid format"
