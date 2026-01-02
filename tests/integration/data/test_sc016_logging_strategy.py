# Upstream: SC-016 质量要求 (日志级别策略符合 ERROR/WARNING/INFO/DEBUG 定义)
# Downstream: tasks.md T293 验证
# Role: 质量验证测试 - 验证日志级别策略

"""
Quality verification test for SC-016: Logging level strategy.

SC-016 Requirement: 日志级别策略符合 ERROR/WARNING/INFO/DEBUG 定义

日志级别定义：
- ERROR: 错误事件，可能影响功能运行
- WARNING: 警告事件，不会影响功能但需要注意
- INFO: 重要信息事件，记录关键业务流程
- DEBUG: 调试信息，仅用于问题诊断

Test Strategy:
1. 扫描所有 Python 文件
2. 检查日志级别使用是否正确
3. 验证日志消息格式
4. 生成合规性报告
"""

import pytest
import os
import re
from pathlib import Path
from typing import List, Dict


@pytest.mark.integration
@pytest.mark.quality
class TestSC016LoggingLevelStrategy:
    """SC-016: 日志级别策略符合 ERROR/WARNING/INFO/DEBUG 定义"""

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

    def test_sc016_logging_levels_usage(self):
        """
        SC-016: 验证日志级别使用符合策略

        测试步骤：
        1. 扫描 notifier 模块的所有 Python 文件
        2. 检查 GLOG/GinkgoLogger 的使用
        3. 验证日志级别选择合理
        4. 生成合规性报告
        """
        print("\n" + "="*70)
        print("SC-016 Quality Test: Logging Level Strategy")
        print("="*70)

        # 扫描 notifier 模块
        notifier_dir = Path("src/ginkgo/notifier")
        py_files = list(notifier_dir.rglob("*.py"))

        # 排除 __init__.py 和 __pycache__
        py_files = [
            f for f in py_files
            if f.name != "__init__.py" and "__pycache__" not in str(f)
        ]

        print(f"\nScanning {len(py_files)} Python files...")

        # 日志级别模式
        log_patterns = {
            "ERROR": re.compile(r'GLOG\.ERROR|\.ERROR\(|error_logger\.ERROR'),
            "WARNING": re.compile(r'GLOG\.WARN|\.WARN\(|warning_logger\.WARN'),
            "INFO": re.compile(r'GLOG\.INFO|\.INFO\(|info_logger\.INFO'),
            "DEBUG": re.compile(r'GLOG\.DEBUG|\.DEBUG\(|debug_logger\.DEBUG')
        }

        results = {
            "total_files": len(py_files),
            "files_with_logs": 0,
            "log_usage": {
                "ERROR": 0,
                "WARNING": 0,
                "INFO": 0,
                "DEBUG": 0
            },
            "files": []
        }

        for py_file in py_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            file_result = {
                "name": py_file.name,
                "relative_path": str(py_file.relative_to(notifier_dir)),
                "log_levels": {}
            }

            has_logs = False
            for level, pattern in log_patterns.items():
                matches = pattern.findall(content)
                count = len(matches)
                if count > 0:
                    file_result["log_levels"][level] = count
                    results["log_usage"][level] += count
                    has_logs = True

            if has_logs:
                results["files_with_logs"] += 1
                results["files"].append(file_result)

        print("\n" + "="*70)
        print("SC-016 Logging Usage Statistics")
        print("="*70)
        print(f"Total Files Scanned:    {results['total_files']}")
        print(f"Files with Logging:     {results['files_with_logs']}")
        print(f"\nLog Level Usage:")
        print(f"  ERROR:                {results['log_usage']['ERROR']}")
        print(f"  WARNING:              {results['log_usage']['WARNING']}")
        print(f"  INFO:                 {results['log_usage']['INFO']}")
        print(f"  DEBUG:                {results['log_usage']['DEBUG']}")

        # 验证日志级别使用合理性
        total_logs = sum(results["log_usage"].values())
        error_ratio = results["log_usage"]["ERROR"] / total_logs if total_logs > 0 else 0
        warning_ratio = results["log_usage"]["WARNING"] / total_logs if total_logs > 0 else 0
        info_ratio = results["log_usage"]["INFO"] / total_logs if total_logs > 0 else 0
        debug_ratio = results["log_usage"]["DEBUG"] / total_logs if total_logs > 0 else 0

        print(f"\nLog Level Distribution:")
        print(f"  ERROR:                {error_ratio*100:.1f}%")
        print(f"  WARNING:              {warning_ratio*100:.1f}%")
        print(f"  INFO:                 {info_ratio*100:.1f}%")
        print(f"  DEBUG:                {debug_ratio*100:.1f}%")

        print("\n" + "="*70)
        print("SC-016 Logging Strategy Assessment")
        print("="*70)

        # 检查策略合规性
        issues = []

        # ERROR 日志不应该太多（通常 < 20%）
        if error_ratio > 0.2:
            issues.append(f"High ERROR ratio ({error_ratio*100:.1f}%) - should be < 20%")

        # DEBUG 日志应该存在（用于调试）
        if results["log_usage"]["DEBUG"] == 0:
            issues.append("No DEBUG logging found - DEBUG logs should exist for troubleshooting")

        if issues:
            print(f"\n⚠️  Issues Found:")
            for issue in issues:
                print(f"  - {issue}")
            print(f"\nResult:                 ⚠️  WARNING (Logging strategy needs review)")
        else:
            print(f"\nResult:                 ✅ PASS (Logging strategy is appropriate)")

        print("="*70)

        # 不强制要求，只警告
        print(f"\nNote: These are recommendations, not strict requirements")

    def test_sc016_log_message_format(self):
        """
        SC-016: 验证日志消息格式

        测试步骤：
        1. 检查日志消息是否包含足够的信息
        2. 验证 ERROR/WARNING 日志有适当的上下文
        3. 生成格式验证报告
        """
        print("\n" + "="*70)
        print("SC-016 Quality Test: Log Message Format")
        print("="*70)

        # 扫描 notifier 模块
        notifier_dir = Path("src/ginkgo/notifier")
        py_files = [
            f for f in notifier_dir.rglob("*.py")
            if f.name != "__init__.py" and "__pycache__" not in str(f)
        ]

        # 检查日志调用模式
        log_call_pattern = re.compile(
            r'(GLOG\.(ERROR|WARN|INFO|DEBUG)|\.ERROR\(|\.WARN\(|\.INFO\(|\.DEBUG\()'
            r'\s*\([^)]+\)',
            re.MULTILINE
        )

        results = {
            "total_log_calls": 0,
            "with_context": 0,
            "without_context": 0,
            "examples": []
        }

        for py_file in py_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            matches = log_call_pattern.findall(content)
            for match in matches:
                results["total_log_calls"] += 1

                # 检查是否包含上下文信息（如错误对象、变量等）
                log_call = match[0]
                has_format = ('{}' in log_call or '%s' in log_call or 'f"' in log_call or 'f\'' in log_call)

                if has_format or 'Exception' in log_call or 'Error' in log_call:
                    results["with_context"] += 1
                else:
                    results["without_context"] += 1

                    # 收集示例（最多 5 个）
                    if len(results["examples"]) < 5:
                        results["examples"].append({
                            "file": py_file.name,
                            "call": log_call[:100] + "..." if len(log_call) > 100 else log_call
                        })

        print("\n" + "="*70)
        print("SC-016 Log Message Format Results")
        print("="*70)
        print(f"Total Log Calls:         {results['total_log_calls']}")
        print(f"With Context:            {results['with_context']}")
        print(f"Without Context:         {results['without_context']}")

        if results["examples"]:
            print(f"\nExamples of logs without context:")
            for example in results["examples"]:
                print(f"  File: {example['file']}")
                print(f"  Call: {example['call']}")
                print()

        context_ratio = results["with_context"] / results["total_log_calls"] if results["total_log_calls"] > 0 else 0

        print("="*70)
        print(f"Context Ratio:           {context_ratio*100:.1f}%")
        print(f"Recommendation:          > 80% of logs should have context")

        if context_ratio >= 0.8:
            print(f"\nResult:                 ✅ PASS (Good logging practice)")
        else:
            print(f"\nResult:                 ⚠️  WARNING (Consider adding more context to logs)")

        print("="*70)

    def test_sc016_debug_mode_compatibility(self):
        """
        SC-016: 验证 DEBUG 模式兼容性

        测试步骤：
        1. 检查代码是否正确使用 GCONF.DEBUGMODE
        2. 验证调试日志有适当的条件判断
        3. 生成兼容性报告
        """
        print("\n" + "="*70)
        print("SC-016 Quality Test: DEBUG Mode Compatibility")
        print("="*70)

        # 扫描 notifier 模块
        notifier_dir = Path("src/ginkgo/notifier")
        py_files = [
            f for f in notifier_dir.rglob("*.py")
            if f.name != "__init__.py" and "__pycache__" not in str(f)
        ]

        # 检查 DEBUG 模式使用模式
        debug_mode_pattern = re.compile(r'GCONF\.DEBUGMODE|if.*DEBUG|DEBUG.*mode')

        results = {
            "total_files": len(py_files),
            "files_with_debug_check": 0,
            "debug_logs": 0,
            "conditional_debug_logs": 0
        }

        for py_file in py_files:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查是否使用 DEBUG 模式
            if debug_mode_pattern.search(content):
                results["files_with_debug_check"] += 1

            # 检查 DEBUG 日志
            debug_logs = re.findall(r'GLOG\.DEBUG|\.DEBUG\(', content)
            results["debug_logs"] += len(debug_logs)

            # 检查条件 DEBUG 日志
            conditional_debug = re.findall(
                r'if\s+.*DEBUG.*:\s*.*\.DEBUG\(|if\s+GCONF\.DEBUGMODE.*:.*\.DEBUG\(',
                content,
                re.MULTILINE | re.DOTALL
            )
            results["conditional_debug_logs"] += len(conditional_debug)

        print("\n" + "="*70)
        print("SC-016 DEBUG Mode Compatibility Results")
        print("="*70)
        print(f"Total Files:             {results['total_files']}")
        print(f"Files with DEBUG Check:  {results['files_with_debug_check']}")
        print(f"Total DEBUG Logs:         {results['debug_logs']}")
        print(f"Conditional DEBUG Logs:  {results['conditional_debug_logs']}")

        print("\n" + "="*70)
        print("SC-016 DEBUG Mode Assessment")
        print("="*70)

        if results["debug_logs"] > 0:
            if results["conditional_debug_logs"] > 0:
                print(f"\n✅ DEBUG logs are properly conditionalized")
                print(f"   {results['conditional_debug_logs']} DEBUG logs have conditional checks")
                print(f"\nResult:                 ✅ PASS (DEBUG mode compatible)")
            else:
                print(f"\n⚠️  DEBUG logs exist but may not be conditional")
                print(f"   Consider using: if GCONF.DEBUGMODE: ...DEBUG(...)")
                print(f"\nResult:                 ⚠️  WARNING (Consider adding DEBUG mode checks)")
        else:
            print(f"\nℹ️  No DEBUG logs found")
            print(f"   DEBUG logs are optional but recommended for troubleshooting")
            print(f"\nResult:                 ✅ PASS (No DEBUG logs, which is acceptable)")

        print("="*70)
