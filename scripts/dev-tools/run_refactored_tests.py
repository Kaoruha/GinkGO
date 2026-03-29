#!/usr/bin/env python3
"""
运行重构后的pytest测试的脚本。

使用方法：
    python run_refactored_tests.py [选项]

选项：
    --unit           只运行单元测试
    --integration     只运行集成测试
    --database       只运行数据库测试
    --performance     只运行性能测试
    --all            运行所有测试（默认）
    --slow           包含慢速测试
    -v, --verbose    详细输出
    -h, --help       显示帮助
"""

import sys
import os
import subprocess
import argparse


def parse_args():
    """解析命令行参数."""
    parser = argparse.ArgumentParser(
        description='运行重构后的pytest测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    python run_refactored_tests.py --unit
    python run_refactored_tests.py --database --slow
    python run_refactored_tests.py --performance -v
        """
    )

    parser.add_argument(
        '--unit',
        action='store_true',
        help='只运行单元测试'
    )

    parser.add_argument(
        '--integration',
        action='store_true',
        help='只运行集成测试'
    )

    parser.add_argument(
        '--database',
        action='store_true',
        help='只运行数据库测试'
    )

    parser.add_argument(
        '--performance',
        action='store_true',
        help='只运行性能测试'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='运行所有测试'
    )

    parser.add_argument(
        '--slow',
        action='store_true',
        help='包含慢速测试'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '--dir',
        type=str,
        help='指定测试目录'
    )

    return parser.parse_args()


def build_pytest_command(args):
    """构建pytest命令."""
    cmd = ['pytest', '-c', 'pytest.refactored.ini']

    # 添加详细输出
    if args.verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')

    # 添加标记
    markers = []

    if args.unit:
        markers.append('unit')
    elif args.integration:
        markers.append('integration')
    elif args.database:
        markers.append('database')
    elif args.performance:
        markers.append('performance')
    elif not args.all:
        # 默认运行非slow的测试
        markers.append('not slow')

    # 排除slow测试（除非明确包含）
    if not args.slow and not args.all:
        if markers:
            markers = [f"{m} and not slow" for m in markers]
        else:
            markers.append('not slow')

    if markers:
        marker_expr = ' or '.join(marketers) if len(markers) > 1 else markers[0]
        cmd.extend(['-m', marker_expr])

    # 添加目录
    if args.dir:
        cmd.append(args.dir)
    elif args.database:
        cmd.append('test/database/')
    elif args.performance:
        cmd.append('test/performance/')
    else:
        cmd.append('test/')

    return cmd


def run_tests(cmd):
    """运行测试."""
    print(f"运行命令: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            check=False,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        return result.returncode
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"运行测试时出错: {e}")
        return 1


def main():
    """主函数."""
    args = parse_args()

    # 检查pytest是否安装
    try:
        import pytest
        print(f"使用 pytest 版本: {pytest.__version__}\n")
    except ImportError:
        print("错误: pytest 未安装")
        print("请运行: pip install pytest")
        return 1

    # 构建并运行测试命令
    cmd = build_pytest_command(args)
    return run_tests(cmd)


if __name__ == '__main__':
    sys.exit(main())
