# #6018 — dev shell 硬编码 src 路径
"""
验证 ginkgo dev shell 启动脚本的 sys.path 指向 GCONF.WORKING_PATH 动态构建
的 src 目录，而非硬编码的旧路径 /home/kaoru/Applications/Ginkgo/src。
"""
import os
import pytest
from unittest.mock import patch


class TestDevShellStartupScriptUsesDynamicSrc:
    """dev_shell 构造的 startup_script 应动态注入 src 路径"""

    @patch("os.unlink")
    @patch("subprocess.run")
    @patch("ginkgo.libs.GCONF")
    def test_startup_script_contains_working_path_src(
        self, mock_gconf, mock_run, mock_unlink, tmp_path
    ):
        mock_gconf.WORKING_PATH = str(tmp_path)
        mock_gconf.PYTHONPATH = "/usr/bin/python3"

        from ginkgo.client.dev_cli import dev_shell
        dev_shell()

        # subprocess.run([python, "-i", startup_file]) — 第三个参数是临时脚本路径
        assert mock_run.called, "dev_shell 未调用 subprocess.run"
        startup_file = mock_run.call_args[0][0][2]
        content = open(startup_file).read()  # os.unlink 被 mock，文件保留

        expected_src = f"{tmp_path}/src"
        assert expected_src in content, (
            f"#6018: startup_script 未含动态 src 路径 {expected_src}"
        )

    @patch("os.unlink")
    @patch("subprocess.run")
    @patch("ginkgo.libs.GCONF")
    def test_startup_script_does_not_contain_hardcoded_old_path(
        self, mock_gconf, mock_run, mock_unlink, tmp_path
    ):
        mock_gconf.WORKING_PATH = str(tmp_path)
        mock_gconf.PYTHONPATH = "/usr/bin/python3"

        from ginkgo.client.dev_cli import dev_shell
        dev_shell()

        startup_file = mock_run.call_args[0][0][2]
        content = open(startup_file).read()

        assert "/home/kaoru/Applications/Ginkgo/src" not in content, (
            f"#6018: startup_script 仍含硬编码旧路径"
        )
