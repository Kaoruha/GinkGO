# coding:utf-8
"""#6006: 删除/危险操作确认标志统一为 --yes/-y（旧 --confirm 保留别名）。

各 CLI 模块独立开发致确认标志碎片化（--confirm/--yes/缺 -y）。typer Option
多 flag 名可实现统一主名 + 旧名别名共存。
"""
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.mark.unit
@pytest.mark.cli
class TestUnifiedConfirmFlagRegistered:
    """#6006 AC1: 所有删除/危险操作命令注册 --yes/-y。

    用 --help（纯解析期，不需 mock service）断言别名已注册进 typer。
    """

    # (模块, app 属性, 命令路径)
    UNIFIED = [
        ("ginkgo.client.backtest_cli", "app", ["delete"]),
        ("ginkgo.client.group_cli", "app", ["delete"]),
        ("ginkgo.client.templates_cli", "app", ["delete"]),
        ("ginkgo.client.user_cli", "app", ["delete"]),
        ("ginkgo.client.component_cli_db", "app", ["delete"]),
        ("ginkgo.client.kafka_cli", "app", ["purge"]),
    ]

    @pytest.mark.parametrize("module_name, app_attr, cmd", UNIFIED)
    def test_yes_and_short_y_in_help(self, cli_runner, module_name, app_attr, cmd):
        """--yes 主名与 -y 短别名均注册（出现在 --help）。"""
        import importlib

        mod = importlib.import_module(module_name)
        app = getattr(mod, app_attr)
        result = cli_runner.invoke(app, cmd + ["--help"])
        assert result.exit_code == 0, f"{module_name} {cmd} --help failed: {result.output}"
        assert "--yes" in result.output, f"{module_name} {cmd}: --yes 未注册"
        assert "-y" in result.output, f"{module_name} {cmd}: -y 未注册"

    def test_user_contact_delete_yes_in_help(self, cli_runner):
        """user_cli 子 app contact 的 delete 也统一（#6006 覆盖 contact 子命令）。"""
        from ginkgo.client import user_cli

        contact_app = getattr(user_cli, "contact_app", None)
        if contact_app is None:
            pytest.skip("user_cli.contact_app 未挂载")
        result = cli_runner.invoke(contact_app, ["delete", "--help"])
        assert result.exit_code == 0, f"contact delete --help: {result.output}"
        assert "--yes" in result.output
        assert "-y" in result.output
