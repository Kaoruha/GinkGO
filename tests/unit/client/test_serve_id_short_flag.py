"""#4826: serve 子命令 --id 加 -i 短选项别名（与 --id 等价）。

背景：
- #6283 删了 -id 别名统一 --id（解决 help 误导显示为 -id），但 --id 仍无短选项，
  研究员按 help 提示输入 -i <val> 报 "No such option: -i"。
- #4826 为 6 个 serve 子命令的 node_id 显式加 -i 短选项，使 -i <val> 与
  --id <val> 解析等价。

不破坏 #6283（见 test_serve_worker_id_flag.py）：
- --id 仍是规范长选项（保留）
- -id 别名仍不存在（#6283 breaking 语义不变）
- serve_scheduler 的 interval -i 是另一个命令的不同参数，跨命令不冲突。

测试技法：用 cmd.make_context(..., standalone_mode=False) 解析参数但不调用
命令体（避免真实启动 worker 长进程），从 ctx.params 验证解析结果。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
import typer

from ginkgo.client import serve_cli

# 所有声明 node_id 的 serve 子命令（与 #6283 test_serve_worker_id_flag.py 对齐）。
SERVE_ID_COMMANDS = [
    "execution",
    "tasktimer",
    "worker-data",
    "worker-backtest",
    "worker-notify",
    "worker-paper",
]


def _get_serve_command(name: str):
    """从 serve_cli.app 解析出 click Command 对象（程序化访问选项/解析）。"""
    cmd_group = typer.main.get_command(serve_cli.app)
    return cmd_group.commands[name]


def _node_id_aliases(cmd_name: str):
    """返回该命令 node_id 选项的全部别名（opts + secondary_opts）。"""
    cmd = _get_serve_command(cmd_name)
    node_id_params = [p for p in cmd.params if p.name == "node_id"]
    assert node_id_params, f"{cmd_name} 应有 node_id 参数"
    return list(node_id_params[0].opts) + list(node_id_params[0].secondary_opts)


@pytest.mark.unit
@pytest.mark.cli
class TestServeIdShortFlag:
    """#4826: serve 子命令 node_id 加 -i 短选项别名，与 --id 等价。"""

    @pytest.mark.parametrize("cmd_name", SERVE_ID_COMMANDS)
    def test_id_option_has_short_alias(self, cmd_name):
        """node_id 选项含 -i 短选项别名（#4826 验收 2 前置）。"""
        aliases = _node_id_aliases(cmd_name)
        assert "-i" in aliases, f"{cmd_name} node_id 缺 -i 短选项: {aliases}"

    @pytest.mark.parametrize("cmd_name", SERVE_ID_COMMANDS)
    def test_id_option_keeps_long_form_and_no_id_alias(self, cmd_name):
        """#6283 兼容回归：--id 长选项保留，-id 别名仍不存在（breaking 语义不变）。"""
        aliases = _node_id_aliases(cmd_name)
        assert "--id" in aliases, f"{cmd_name} 应保留 --id: {aliases}"
        assert "-id" not in aliases, f"{cmd_name} 残留 -id 别名（#6283 已删）: {aliases}"

    @pytest.mark.parametrize("cmd_name", SERVE_ID_COMMANDS)
    def test_short_i_equivalent_to_long_id(self, cmd_name):
        """-i <val> 与 --id <val> 解析等价（#4826 验收 2，CliRunner 等价断言）。

        用 make_context 解析但不调用命令体（仅 parse_args，不 invoke，避免启动 worker 长进程）。
        """
        cmd = _get_serve_command(cmd_name)
        ctx_short = cmd.make_context(cmd_name, ["-i", "t1"])
        ctx_long = cmd.make_context(cmd_name, ["--id", "t1"])
        assert ctx_short.params["node_id"] == "t1", f"{cmd_name} -i 未绑定到 node_id"
        assert ctx_long.params["node_id"] == "t1", f"{cmd_name} --id 未绑定到 node_id"
        assert ctx_short.params["node_id"] == ctx_long.params["node_id"]

    @pytest.mark.parametrize("cmd_name", SERVE_ID_COMMANDS)
    def test_long_id_default_unchanged(self, cmd_name):
        """既有 --id 长选项默认值回归不变（#4826 验收 3）。"""
        cmd = _get_serve_command(cmd_name)
        ctx = cmd.make_context(cmd_name, [])
        assert ctx.params["node_id"] is None, f"{cmd_name} node_id 默认值应为 None"
