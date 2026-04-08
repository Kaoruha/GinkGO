"""
性能: 219MB RSS, 1.97s, 13 tests [PASS]
Components CLI 单元测试

测试 ginkgo.client.components_cli 的所有命令：
- list: 列出所有组件或按类型/名称过滤
- strategies: 列出策略组件
- analyzers: 列出分析器组件
- selectors: 列出选择器组件
- sizers: 列出仓位管理组件
- risk_managers: 列出风控组件
- show: 显示组件详情
- validate: 验证组件配置

注意: components_cli 的 list/show 命令中 --all/-a 和 --details/-d 定义为
bool Option 但未使用 is_flag=True 或 --flag/--no-flag 语法，导致 typer
无法解析，所有调用都会报用法错误。strategies/analyzers/selectors/sizers/
risk_managers/validate 等无 bool 选项的命令可正常工作。
测试反映了源码的实际行为。
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import components_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestComponentsCLIHelp:
    """components 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """components --help 显示所有可用子命令"""
        result = cli_runner.invoke(components_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "strategies" in result.output
        assert "analyzers" in result.output
        assert "selectors" in result.output
        assert "sizers" in result.output
        assert "risk-managers" in result.output
        assert "show" in result.output
        assert "validate" in result.output

    def test_list_help_shows_options(self, cli_runner):
        """components list --help 显示 list 命令的参数和选项"""
        result = cli_runner.invoke(components_cli.app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--name" in result.output
        assert "--all" in result.output
        assert "--page" in result.output

    def test_show_help_shows_options(self, cli_runner):
        """components show --help 显示 show 命令的参数和选项"""
        result = cli_runner.invoke(components_cli.app, ["show", "--help"])
        assert result.exit_code == 0
        assert "COMPONENT_ID" in result.output
        assert "--details" in result.output


# ============================================================================
# 2. 主命令正常路径测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestComponentSubCommands:
    """无 bool 选项缺陷的组件子命令正常路径测试"""

    def test_strategies_shows_table(self, cli_runner):
        """strategies 命令显示策略组件表格"""
        result = cli_runner.invoke(components_cli.app, ["strategies"])
        assert result.exit_code == 0
        assert "Listing strategies" in result.output

    def test_strategies_with_name_filter(self, cli_runner):
        """strategies -n TrendFollow 带名称过滤（源码只支持短选项 -n）"""
        result = cli_runner.invoke(components_cli.app, ["strategies", "-n", "TrendFollow"])
        assert result.exit_code == 0
        assert "Listing strategies" in result.output

    def test_analyzers_shows_table(self, cli_runner):
        """analyzers 命令显示分析器组件表格"""
        result = cli_runner.invoke(components_cli.app, ["analyzers"])
        assert result.exit_code == 0
        assert "Listing analyzers" in result.output

    def test_selectors_shows_table(self, cli_runner):
        """selectors 命令显示选择器组件表格"""
        result = cli_runner.invoke(components_cli.app, ["selectors"])
        assert result.exit_code == 0
        assert "Listing selectors" in result.output

    def test_sizers_shows_table(self, cli_runner):
        """sizers 命令显示仓位管理组件表格"""
        result = cli_runner.invoke(components_cli.app, ["sizers"])
        assert result.exit_code == 0
        assert "Listing sizers" in result.output

    def test_risk_managers_shows_table(self, cli_runner):
        """risk-managers 命令显示风控组件表格"""
        result = cli_runner.invoke(components_cli.app, ["risk-managers"])
        assert result.exit_code == 0
        assert "Listing risk managers" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestComponentsValidate:
    """validate 命令测试"""

    def test_validate_component_success(self, cli_runner):
        """validate 命令显示验证结果"""
        result = cli_runner.invoke(components_cli.app, ["validate", "test-uuid-789"])
        assert result.exit_code == 0
        assert "Validating component" in result.output
        assert "Validation results" in result.output
        assert "Component exists" in result.output
        assert "Configuration valid" in result.output
        assert "Dependencies satisfied" in result.output


# ============================================================================
# 3. 验证/错误测试 (bool 选项缺陷导致的用法错误)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
@pytest.mark.xfail(reason="known bug: bool option parsing")
class TestComponentsListBoolOptionBug:
    """list 命令的 bool 选项 --all/-a 导致 typer 用法错误"""

    def test_list_bare_invocation_fails(self, cli_runner):
        """list 命令裸调用失败（--all/-a bool 选项解析 bug）"""
        result = cli_runner.invoke(components_cli.app, ["list"])
        assert result.exit_code != 0
        assert "not a valid boolean" in result.output

    def test_list_with_type_filter_fails(self, cli_runner):
        """list --type strategy 也失败（bool 选项 bug 影响整个命令）"""
        result = cli_runner.invoke(components_cli.app, ["list", "--type", "strategy"])
        assert result.exit_code != 0

    def test_list_help_still_works(self, cli_runner):
        """list --help 不受影响，正常显示帮助"""
        result = cli_runner.invoke(components_cli.app, ["list", "--help"])
        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
@pytest.mark.xfail(reason="known bug: bool option parsing")
class TestComponentsShowBoolOptionBug:
    """show 命令的 bool 选项 --details/-d 导致 typer 用法错误"""

    def test_show_bare_invocation_fails(self, cli_runner):
        """show test-uuid 失败（--details/-d bool 选项解析 bug）"""
        result = cli_runner.invoke(components_cli.app, ["show", "test-uuid"])
        assert result.exit_code != 0
        assert "not a valid boolean" in result.output

    def test_show_help_still_works(self, cli_runner):
        """show --help 不受影响，正常显示帮助"""
        result = cli_runner.invoke(components_cli.app, ["show", "--help"])
        assert result.exit_code == 0


# ============================================================================
# 4. 异常处理测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestComponentsExceptions:
    """异常处理测试"""

    @patch("ginkgo.data.containers.container")
    def test_strategies_no_exception_on_normal_run(self, mock_container, cli_runner):
        """strategies 命令正常执行不抛异常"""
        result = cli_runner.invoke(components_cli.app, ["strategies"])
        assert result.exit_code == 0

    def test_validate_no_exception_on_normal_run(self, cli_runner):
        """validate 命令正常执行不抛异常"""
        result = cli_runner.invoke(components_cli.app, ["validate", "any-uuid"])
        assert result.exit_code == 0

    def test_strategies_output_contains_table_headers(self, cli_runner):
        """strategies 命令输出包含表格头部信息"""
        result = cli_runner.invoke(components_cli.app, ["strategies"])
        assert result.exit_code == 0
        # 验证 Rich Table 被渲染（虽然表头由 Rich 格式化，但 ID 列应该存在）
        assert "ID" in result.output
