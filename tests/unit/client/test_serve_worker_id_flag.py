"""
#6283: serve worker-* 的 --id 参数风格统一，移除 click 死别名 -id

根因：typer.Option(None, "--id", "-id") 中的 "-id" 是多字符单横线别名，
click 把 "-id" 当作短选项堆叠 "-i -d" 解析 → 报 "No such option: -i"。
该别名自始无效，却仍残留在 worker-data/backtest/notify 的选项声明里
（worker-paper 已清理），构成"风格不统一"的误导假象。

本测试通过 click Option 的 secondary_opts（别名声明）程序化验证：
node_id 选项不得残留 -id 死别名，仅保留标准 --id 长选项。
（程序化检查而非 help 文本断言，不受 rich 表格渲染格式影响。）
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
import typer

from ginkgo.client import serve_cli


def _get_serve_command(name: str):
    """从 serve_cli.app 解析出 click Command 对象（程序化访问选项声明）。"""
    cmd_group = typer.main.get_command(serve_cli.app)
    return cmd_group.commands[name]


def _id_option_aliases(cmd_name: str):
    """返回该命令 node_id 选项的全部别名（opts + secondary_opts）。"""
    cmd = _get_serve_command(cmd_name)
    node_id_params = [p for p in cmd.params if p.name == "node_id"]
    assert node_id_params, f"{cmd_name} 应有 node_id 参数"
    param = node_id_params[0]
    return list(param.opts) + list(param.secondary_opts)


@pytest.mark.unit
@pytest.mark.cli
class TestWorkerIdFlagStyle:
    """#6283: serve worker-* 的 node_id 选项统一 --id，移除 -id 死别名。"""

    def test_worker_backtest_id_option_drops_deprecated_short_alias(self):
        """worker-backtest: node_id 不得残留 -id 死别名（click 拆 -i -d 报错）。"""
        aliases = _id_option_aliases("worker-backtest")
        assert "--id" in aliases, f"worker-backtest 应保留 --id: {aliases}"
        assert "-id" not in aliases, f"worker-backtest 残留死别名 -id: {aliases}"

    def test_worker_data_id_option_drops_deprecated_short_alias(self):
        """worker-data: node_id 不得残留 -id 死别名（#6283 统一 --id）。"""
        aliases = _id_option_aliases("worker-data")
        assert "--id" in aliases
        assert "-id" not in aliases, f"worker-data 残留死别名 -id: {aliases}"

    def test_worker_notify_id_option_drops_deprecated_short_alias(self):
        """worker-notify: node_id 不得残留 -id 死别名（#6283 统一 --id）。"""
        aliases = _id_option_aliases("worker-notify")
        assert "--id" in aliases
        assert "-id" not in aliases, f"worker-notify 残留死别名 -id: {aliases}"

    def test_worker_paper_id_option_never_had_short_alias(self):
        """worker-paper: 本就纯 --id（回归锁，防止重新引入 -id 死别名）。"""
        aliases = _id_option_aliases("worker-paper")
        assert "--id" in aliases
        assert "-id" not in aliases, f"worker-paper 引入了死别名 -id: {aliases}"

    def test_deprecated_short_id_flag_fails_cleanly(self, runner=None):
        """-id 整体作为未知选项报错，而非被误解析为可用别名（#6283 验收2）。"""
        from typer.testing import CliRunner
        runner = runner or CliRunner()
        # worker-backtest -id t1：修复前报 "No such option: -i"（拆解），
        # 移除别名后报 "No such option: -id"（整体未知，更清晰）。
        # 两种都 exit_code != 0；关键是不被当作合法别名静默接受。
        result = runner.invoke(serve_cli.app, ["worker-backtest", "-id", "t1"])
        assert result.exit_code != 0, "-id 不应被静默接受为合法选项"
