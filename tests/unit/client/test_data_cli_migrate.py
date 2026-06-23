"""
#5941 data migrate alembic 调用可移植性测试
裸 `alembic` 二进制在 venv/uv 下 PATH 不可见 → FileNotFoundError。
应使用 [sys.executable, "-m", "alembic"] 绑定当前解释器。
"""
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import sys
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import data_cli
from ginkgo.client.data_cli import app


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestDataMigrateAlembicPortable:
    """#5941: migrate 用 sys.executable -m alembic，不依赖 PATH 中的裸 alembic"""

    def test_current_action_uses_sys_executable_m_alembic(self, cli_runner):
        """--action current 应经 sys.executable -m alembic 调用，非裸 alembic"""
        with patch("subprocess.run") as mock_run:
            result = cli_runner.invoke(app, ["migrate", "--database", "mysql", "--action", "current"])

        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0] if args else kwargs.get("args")
        # 前缀须为 [sys.executable, "-m", "alembic"]，非裸 "alembic"
        assert cmd[0] == sys.executable, f"应用 sys.executable, 实际 cmd[0]={cmd[0]!r}"
        assert cmd[1:3] == ["-m", "alembic"], f"应用 -m alembic, 实际={cmd[1:3]!r}"
        assert "current" in cmd

    @pytest.mark.parametrize(
        "action,expected_sub",
        [
            ("heads", ["heads"]),
            ("history", ["history"]),
            ("current", ["current"]),
        ],
    )
    def test_status_actions_use_portable_prefix(self, cli_runner, action, expected_sub):
        """heads/history/current 均走便携前缀"""
        with patch("subprocess.run") as mock_run:
            result = cli_runner.invoke(app, ["migrate", "--database", "mysql", "--action", action])
        assert result.exit_code == 0, result.output
        cmd = mock_run.call_args.args[0]
        assert cmd[:3] == [sys.executable, "-m", "alembic"]
        assert cmd[3:] == expected_sub

    def test_upgrade_head_uses_portable_prefix(self, cli_runner):
        """--action upgrade（无 revision）走便携前缀 + upgrade head"""
        with patch("subprocess.run") as mock_run:
            result = cli_runner.invoke(app, ["migrate", "--database", "mysql", "--action", "upgrade"])
        assert result.exit_code == 0, result.output
        cmd = mock_run.call_args.args[0]
        assert cmd[:3] == [sys.executable, "-m", "alembic"]
        assert cmd[3:] == ["upgrade", "head"]
