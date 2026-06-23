"""
#5517: data migrate 路径便携性 + --path 覆盖

默认 migrations_dir 不再硬编码 /home/kaoru/Ginkgo/migrations/mysql，
而是相对 data_cli.__file__ 上溯到源码树根解析；新增 --path 覆盖参数。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import data_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


def _expected_default_migrations_dir():
    """相对 data_cli.__file__ 上溯 4 级到源码树根，拼 migrations/mysql。"""
    src_ginkgo_client = os.path.dirname(os.path.abspath(data_cli.__file__))
    src_ginkgo = os.path.dirname(src_ginkgo_client)
    src_dir = os.path.dirname(src_ginkgo)
    source_root = os.path.dirname(src_dir)
    return os.path.join(source_root, "migrations", "mysql")


@pytest.mark.unit
@pytest.mark.cli
class TestMigratePath:
    """#5517: data migrate 路径便携性"""

    def test_migrate_help_exposes_path_option(self, cli_runner):
        """--path 选项暴露在 migrate help（#5517 覆盖参数）。"""
        result = cli_runner.invoke(data_cli.app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "--path" in result.output

    @patch("subprocess.run")
    def test_migrate_path_override_sets_cwd(self, mock_run, cli_runner, tmp_path):
        """--path 覆盖时，alembic 在用户指定目录执行（cwd = 该目录绝对路径）。"""
        mock_run.return_value = MagicMock(returncode=0)
        result = cli_runner.invoke(data_cli.app, ["migrate", "--action", "upgrade", "--path", str(tmp_path)])
        assert result.exit_code == 0
        # 所有 subprocess.run 调用的 cwd 都应是 --path 指定的绝对路径
        for call in mock_run.call_args_list:
            assert call.kwargs["cwd"] == str(tmp_path)

    @patch("subprocess.run")
    def test_migrate_default_cwd_tracks_source_tree(self, mock_run, cli_runner):
        """默认（无 --path）时 migrations_dir 相对 data_cli.__file__ 解析，便携。

        #5517：不再硬编码 /home/kaoru/Ginkgo/migrations/mysql。换机/换安装目录后，
        默认路径应跟随源码树真实位置，alembic.ini 仍可触达。
        """
        mock_run.return_value = MagicMock(returncode=0)
        result = cli_runner.invoke(data_cli.app, ["migrate", "--action", "upgrade"])
        assert result.exit_code == 0
        for call in mock_run.call_args_list:
            cwd = call.kwargs["cwd"]
            # 便携性锚点 1：等于 __file__ 上溯到源码树根 + migrations/mysql
            assert cwd == _expected_default_migrations_dir()
            # 便携性锚点 2：解析出的目录真实存在（alembic.ini 可触达）
            assert os.path.exists(os.path.join(cwd, "alembic.ini"))
        # 便携性锚点 3：源码不再把硬编码绝对路径赋给 migrations_dir
        # （注释里解释旧值是允许的；禁止的是重新把它写进赋值）
        src = open(data_cli.__file__, encoding="utf-8").read()
        assert 'migrations_dir = "/home/kaoru' not in src
