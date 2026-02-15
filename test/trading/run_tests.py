#!/usr/bin/env python3
"""
Ginkgo Trading 测试运行脚本

提供便捷的测试运行命令
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """运行命令并显示输出"""
    print(f"\n{'='*60}")
    print(f" {description}")
    print(f"{'='*60}")
    print(f"命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("""
Ginkgo Trading 测试运行脚本

用法:
  python run_tests.py <命令> [选项]

可用命令:
  all          运行所有测试
  unit         运行单元测试
  integration   运行集成测试
  entities     运行entities目录测试
  events       运行events目录测试
  bar          运行Bar测试
  order        运行Order测试
  signal       运行Signal测试
  position     运行Position测试
  tick         运行Tick测试
  coverage     运行测试并生成覆盖率报告
  verbose      详细模式运行所有测试
  report       生成HTML测试报告

示例:
  python run_tests.py all
  python run_tests.py unit
  python run_tests.py coverage
        """)
        return 1

    command = sys.argv[1]
    test_dir = Path(__file__).parent

    # 构建基础 pytest 命令
    pytest_cmd = [
        sys.executable, "-m", "pytest",
        "-v",  # 详细输出
        "--tb=short",  # 简短的traceback
        "--strict-markers",  # 严格标记检查
    ]

    # 根据命令添加参数
    if command == "all":
        target = str(test_dir)
    elif command == "unit":
        pytest_cmd.extend(["-m", "unit"])
        target = str(test_dir)
    elif command == "integration":
        pytest_cmd.extend(["-m", "integration"])
        target = str(test_dir)
    elif command == "entities":
        target = str(test_dir / "entities")
    elif command == "events":
        target = str(test_dir / "events")
    elif command == "bar":
        target = str(test_dir / "entities" / "test_bar_refactored.py")
    elif command == "order":
        target = str(test_dir / "entities" / "test_order_refactored.py")
    elif command == "signal":
        target = str(test_dir / "entities" / "test_signal_refactored.py")
    elif command == "position":
        target = str(test_dir / "entities" / "test_position_refactored.py")
    elif command == "tick":
        target = str(test_dir / "entities" / "test_tick_refactored.py")
    elif command == "coverage":
        pytest_cmd.extend([
            "--cov=ginkgo.trading.entities",
            "--cov=ginkgo.trading.events",
            "--cov-report=html",
            "--cov-report=term"
        ])
        target = str(test_dir)
    elif command == "verbose":
        pytest_cmd.append("-vv")
        target = str(test_dir)
    elif command == "report":
        pytest_cmd.extend(["--html=report.html", "--self-contained-html"])
        target = str(test_dir)
    else:
        print(f"未知命令: {command}")
        return 1

    pytest_cmd.append(target)

    # 运行测试
    descriptions = {
        "all": "运行所有测试",
        "unit": "运行单元测试",
        "integration": "运行集成测试",
        "entities": "运行entities测试",
        "events": "运行events测试",
        "bar": "运行Bar测试",
        "order": "运行Order测试",
        "signal": "运行Signal测试",
        "position": "运行Position测试",
        "tick": "运行Tick测试",
        "coverage": "生成测试覆盖率报告",
        "verbose": "详细模式运行所有测试",
        "report": "生成HTML测试报告"
    }

    return run_command(pytest_cmd, descriptions.get(command, f"运行 {command}"))


if __name__ == "__main__":
    sys.exit(main())
