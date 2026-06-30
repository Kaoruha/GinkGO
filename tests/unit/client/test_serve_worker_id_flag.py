"""
#6283: serve 子命令的 --id 参数风格统一（方案 B，breaking）

根因（实测纠正，见 PR #6325 review；issue 原始描述的 "click 拆解 -i -d" 不成立）：
- worker-paper 仅声明 --id（无 -id 别名）→ -id 被 click 当未知短选项堆叠报
  No such option，是 issue 观察到的报错唯一来源。
- execution/tasktimer/worker-data/backtest/notify 声明 --id + -id 别名 → 在
  typer 0.20 / click 8.3 下 -id 是合法完整选项（param.opts 含 '-id'），可用。
- help 示例还混用 --node-id（与参数名 --id 不符）。
表象"风格不统一"的根因是别名声明不一致 + help 示例笔误，非"click 不支持多字符单横线"。

方案 B（review 接受的 breaking 路径）：
全删 -id 别名（含 execution/tasktimer 同问题），统一 --id；help 示例同步 --id。
BREAKING：CLAUDE.md「Key Commands」与部署脚本中 `serve worker-backtest -id test2`
需迁移为 `--id test2`，-id 不再被任何 serve 子命令接受。

方案 A（per-alias deprecation）排除：click 8.3 原生 deprecated 是整个 Option 级，
per-alias（只 -id warning 而 --id 不 warning）需侵入 _OptionParser._process_opts
内部 API，成本不成比例；自用项目 breaking 可控。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
import typer

from ginkgo.client import serve_cli

# 所有声明 node_id 的 serve 子命令（execution/tasktimer 超 issue 原始 worker-*
# scope，但属同一兼容性问题，方案 B 一并统一）。
SERVE_ID_COMMANDS = [
    "execution",
    "tasktimer",
    "worker-data",
    "worker-backtest",
    "worker-notify",
    "worker-paper",
]


def _get_serve_command(name: str):
    """从 serve_cli.app 解析出 click Command 对象（程序化访问选项/help 声明）。"""
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
class TestServeIdFlagUnified:
    """#6283: 所有 serve 子命令的 node_id 选项统一 --id，移除 -id 别名。"""

    @pytest.mark.parametrize("cmd_name", SERVE_ID_COMMANDS)
    def test_id_option_only_long_form(self, cmd_name):
        """每个 serve 子命令：node_id 仅保留 --id，不含 -id 别名（#6283 统一）。"""
        aliases = _id_option_aliases(cmd_name)
        assert "--id" in aliases, f"{cmd_name} 应保留 --id: {aliases}"
        assert "-id" not in aliases, f"{cmd_name} 残留 -id 别名（应迁移到 --id）: {aliases}"

    @pytest.mark.parametrize("cmd_name", SERVE_ID_COMMANDS)
    def test_help_example_uses_double_dash_id(self, cmd_name):
        """help 示例统一用 --id，不残留 --node-id 笔误（#6283 第二层不一致修复）。"""
        cmd = _get_serve_command(cmd_name)
        help_text = cmd.help or ""
        # --node-id 从未是真实参数名（参数名是 --id），help 示例出现即是笔误。
        assert "--node-id" not in help_text, f"{cmd_name} help 残留 --node-id 笔误: {help_text}"

    def test_short_id_alias_rejected_after_unification(self):
        """BREAKING 回归：统一后 -id 对所有子命令是未知选项（No such option）。
        用户需迁移到 --id（CLAUDE.md/部署脚本中的 -id 用法不再可用）。
        关键：-id 不被静默接受为合法选项（exit != 0）。"""
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(serve_cli.app, ["worker-backtest", "-id", "t1"])
        assert result.exit_code != 0, "-id 不应被接受（方案 B 统一为 --id，见迁移指引）"
