"""
CLI E2E 测试

通过 subprocess 调用 main.py，验证真实命令行行为。
这些测试验证 CLI 入口点、帮助文本和基本错误处理。
不依赖数据库。

注意：运行时需加 --noconftest 跳过 Playwright conftest。
"""
import subprocess
import sys
import os

import pytest

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_path = PROJECT_ROOT
if _path not in sys.path:
    sys.path.insert(0, _path)


def _run_cli(args, timeout=15):
    """运行 ginkgo CLI 命令并返回 CompletedProcess"""
    return subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "main.py")] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestEntryPoint:
    """CLI 入口点测试"""

    @pytest.mark.e2e
    def test_help_shows_usage(self):
        """--help 显示使用说明"""
        result = _run_cli(["--help"])
        assert result.returncode == 0
        assert "Ginkgo" in result.stdout

    @pytest.mark.e2e
    def test_no_args_shows_help(self):
        """无参数显示帮助（Typer 返回 2 表示缺少子命令，但会显示用法）"""
        result = _run_cli([])
        assert "Ginkgo" in result.stdout


class TestCoreCommands:
    """核心命令 E2E 测试"""

    @pytest.mark.e2e
    def test_status_command(self):
        """status 命令可执行"""
        result = _run_cli(["status"])
        assert "status" in result.stdout.lower()

    @pytest.mark.e2e
    def test_debug_on_command(self):
        """debug on 命令可执行"""
        result = _run_cli(["debug", "on"])
        assert "debug" in result.stdout.lower()

    @pytest.mark.e2e
    def test_debug_off_command(self):
        """debug off 命令可执行"""
        result = _run_cli(["debug", "off"])
        assert "debug" in result.stdout.lower()


class TestSubCommandHelp:
    """子命令帮助测试"""

    @pytest.mark.e2e
    @pytest.mark.parametrize("command", [
        "data", "engine", "portfolio", "config", "serve",
        "kafka", "worker", "user", "group", "logging",
        "eval", "component", "mapping", "result",
    ])
    def test_subcommand_help(self, command):
        f"{command} --help 显示帮助"""
        result = _run_cli([command, "--help"])
        assert result.returncode == 0
        assert command in result.stdout.lower() or "Usage" in result.stdout


class TestErrorHandling:
    """错误处理 E2E 测试"""

    @pytest.mark.e2e
    def test_unknown_command(self):
        """未知命令返回错误"""
        result = _run_cli(["nonexistent_command_xyz"])
        assert result.returncode != 0

    @pytest.mark.e2e
    def test_missing_required_arg(self):
        """缺少必需参数返回错误"""
        result = _run_cli(["get"])
        assert result.returncode != 0
