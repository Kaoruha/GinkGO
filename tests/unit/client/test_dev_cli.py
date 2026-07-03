# #6020 — dev test/lint 引用错误目录 test/ 应为 tests/
"""
验证 ginkgo dev test / dev lint 命令指向真实存在的 tests/ 目录，
而非不存在的 test/（项目测试目录统一为 tests/，见 CLAUDE.md）。
"""
import pytest
from unittest.mock import patch, MagicMock


class TestDevTestCommandTargetsTestsDir:
    """dev test 应把 tests/ 作为 pytest 目标"""

    @patch("subprocess.run")
    @patch("ginkgo.libs.GCONF")
    def test_dev_test_cmd_targets_tests_dir(self, mock_gconf, mock_run):
        mock_gconf.DEBUGMODE = True
        mock_gconf.WORKING_PATH = "/tmp"

        from ginkgo.client.dev_cli import dev_test
        dev_test()

        assert mock_run.called, "dev_test 未调用 subprocess.run"
        cmd = mock_run.call_args[0][0]
        assert "tests/" in cmd, f"#6020: dev test 未指向 tests/, cmd={cmd}"
        assert "test/" not in cmd, f"#6020: dev test 仍指向 test/, cmd={cmd}"

    @patch("subprocess.run")
    @patch("ginkgo.libs.GCONF")
    def test_dev_test_verbose_pattern_still_targets_tests_dir(self, mock_gconf, mock_run):
        """组合参数时 tests/ 仍应在 cmd 末尾"""
        mock_gconf.DEBUGMODE = True
        mock_gconf.WORKING_PATH = "/tmp"

        from ginkgo.client.dev_cli import dev_test
        dev_test(verbose=True, pattern="smoke")

        cmd = mock_run.call_args[0][0]
        assert "tests/" in cmd, f"cmd={cmd}"
        assert "test/" not in cmd, f"cmd={cmd}"


class TestDevLintCommandTargetsTestsDir:
    """dev lint / lint --fix 应把 tests/ 纳入 black/isort/flake8 范围"""

    @patch("subprocess.run")
    def test_dev_lint_fix_targets_tests_dir(self, mock_run):
        from ginkgo.client.dev_cli import dev_lint
        dev_lint(fix=True)

        # 收集所有 black/isort/flake8 调用的参数（排除 --version 探测）
        all_args = [c[0][0] for c in mock_run.call_args_list]
        tool_calls = [
            a for a in all_args
            if a and a[0] in ("black", "isort", "flake8")
            and not (len(a) == 2 and a[1] == "--version")
        ]
        assert tool_calls, f"未找到 lint 工具调用: {all_args}"
        for call in tool_calls:
            assert "tests/" in call, f"#6020: {call[0]} 未含 tests/: {call}"
            assert "test/" not in call, f"#6020: {call[0]} 仍含 test/: {call}"


class TestDevProfileUsesSysExecutable:
    """#4768 — dev profile 应调用当前解释器 (sys.executable) 而非硬编码 'python'"""

    @patch("subprocess.run")
    def test_dev_profile_cmd_uses_sys_executable(self, mock_run):
        import sys
        from ginkgo.client.dev_cli import dev_profile

        dev_profile(script="foo.py", output="profile.stats")

        assert mock_run.called, "dev_profile 未调用 subprocess.run"
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == sys.executable, (
            f"#4768: cmd 首元素应为 sys.executable ({sys.executable}), got {cmd[0]!r}"
        )
        assert "-m" in cmd and "cProfile" in cmd, f"cProfile 调用丢失: {cmd}"

    @patch("subprocess.run")
    def test_dev_profile_interpreter_missing_outputs_friendly_error(self, mock_run):
        """#4768: 解释器/脚本缺失时应友好退出 (typer.Exit)，非裸 FileNotFoundError traceback"""
        import typer
        mock_run.side_effect = FileNotFoundError("python not found")
        from ginkgo.client.dev_cli import dev_profile

        with pytest.raises(typer.Exit) as exc_info:
            dev_profile(script="foo.py", output="profile.stats")
        assert exc_info.value.exit_code != 0, "失败时应以非零码退出"

    @patch("subprocess.run")
    def test_dev_profile_nonzero_exit_outputs_friendly_error(self, mock_run):
        """#4768: cProfile 非零退出应友好提示并透传退出码，非裸 CalledProcessError"""
        import typer
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(returncode=2, cmd=[])
        from ginkgo.client.dev_cli import dev_profile

        with pytest.raises(typer.Exit) as exc_info:
            dev_profile(script="foo.py", output="profile.stats")
        assert exc_info.value.exit_code == 2


class TestDevJupyterMissingInstall:
    """dev jupyter 在 jupyter 未安装时应友好提示并正常退出（#5091）"""

    @patch("subprocess.run")
    @patch("os.path.exists", return_value=False)
    @patch("shutil.which", return_value=None)
    @patch("ginkgo.libs.GCONF")
    def test_missing_jupyter_no_traceback(
        self, mock_gconf, mock_which, mock_exists, mock_run, capsys):
        """#5091: which 找不到 + venv 路径也不存在 → 不调 subprocess.run、不抛异常"""
        mock_gconf.PYTHONPATH = "/home/x/.venv/bin/python"
        from ginkgo.client.dev_cli import dev_jupyter
        # 不应抛 FileNotFoundError
        dev_jupyter()
        # jupyter 缺失时不应尝试启动子进程
        assert not mock_run.called, "#5091: jupyter 缺失时不应调 subprocess.run"
        # 应输出安装提示（含 jupyter 关键词）
        captured = capsys.readouterr()
        assert "jupyter" in (captured.out + captured.err).lower(), \
            "#5091: 缺失时应提示安装 jupyter"


class TestDevJupyterLaunch:
    """dev jupyter 在 jupyter 可用时应正常启动（#5091 回归守护）"""

    @patch("subprocess.run")
    @patch("os.path.exists", return_value=True)  # venv 也有，但应被 which 优先覆盖
    @patch("shutil.which", return_value="/usr/bin/jupyter")
    @patch("ginkgo.libs.GCONF")
    def test_which_finds_jupyter_launches_lab(
        self, mock_gconf, mock_which, mock_exists, mock_run):
        """#5091: shutil.which 找到 jupyter 时启动 lab，且优先用 which 结果而非 venv 推断"""
        mock_gconf.PYTHONPATH = "/home/x/.venv/bin/python"
        from ginkgo.client.dev_cli import dev_jupyter
        dev_jupyter()

        assert mock_run.called, "找到 jupyter 时应启动 lab"
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/bin/jupyter", \
            f"#5091: 应优先用 shutil.which 结果而非 venv 推断, cmd={cmd}"
        assert "lab" in cmd, f"应启动 lab 子命令, cmd={cmd}"
