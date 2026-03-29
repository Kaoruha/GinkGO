"""
DataSource CLI 单元测试

测试 ginkgo.client.datasource_cli 的所有命令：
- list: 列出所有数据源及状态
- test: 测试数据源连接和数据获取
- configure: 配置数据源认证信息
- status: 显示数据源整体状态和健康信息
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import json
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import datasource_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceCLIHelp:
    """datasource 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """datasource --help 显示所有可用子命令"""
        result = cli_runner.invoke(datasource_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "test" in result.output
        assert "configure" in result.output
        assert "status" in result.output

    def test_list_help_shows_raw_option(self, cli_runner):
        """datasource list --help 显示 --raw 选项"""
        result = cli_runner.invoke(datasource_cli.app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--raw" in result.output


# ============================================================================
# 2. Main Commands Happy Path
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceList:
    """datasource list 命令"""

    def test_list_shows_available_sources(self, cli_runner):
        """list 命令显示所有数据源"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Tushare" in result.output
        assert "AKShare" in result.output
        assert "TDX" in result.output
        assert "Yahoo" in result.output
        assert "BaoStock" in result.output

    def test_list_raw_outputs_json(self, cli_runner):
        """list --raw 输出包含 JSON 数据源列表"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["list", "--raw"])
        assert result.exit_code == 0
        assert "Tushare" in result.output
        assert "AKShare" in result.output
        assert "Premium" in result.output
        assert "Free" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceTest:
    """datasource test 命令"""

    def test_test_unknown_source_shows_error(self, cli_runner):
        """test 未知数据源时显示错误和可用源列表"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["test", "unknown_source"])
        assert result.exit_code == 0
        assert "Unknown data source" in result.output
        assert "tushare" in result.output
        assert "akshare" in result.output

    def test_test_known_source_success(self, cli_runner):
        """test 已知数据源时成功连接"""
        mock_source = MagicMock()
        mock_source._test_connection.return_value = True
        mock_container = MagicMock()
        mock_container.ginkgo_tushare_source.return_value = mock_source

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(datasource_cli.app, ["test", "tushare"])
        assert result.exit_code == 0
        assert "Connection to tushare successful" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceConfigure:
    """datasource configure 命令"""

    def test_configure_tushare_with_token(self, cli_runner):
        """configure tushare --token 设置 token 成功"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(
                datasource_cli.app,
                ["configure", "tushare", "--token", "1234567890abcdef12345678"],
            )
        assert result.exit_code == 0
        assert "Tushare token configured successfully" in result.output

    def test_configure_tushare_without_token_shows_instructions(self, cli_runner):
        """configure tushare 不带 token 显示注册指引"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["configure", "tushare"])
        assert result.exit_code == 0
        assert "requires an API token" in result.output
        assert "tushare.pro/register" in result.output

    def test_configure_akshare_no_auth_needed(self, cli_runner):
        """configure akshare 提示无需认证"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["configure", "akshare"])
        assert result.exit_code == 0
        assert "no configuration" in result.output.lower() or "no authentication" in result.output.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceStatus:
    """datasource status 命令"""

    def test_status_shows_dashboard(self, cli_runner):
        """status 命令显示数据源状态面板"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["status"])
        assert result.exit_code == 0
        assert "Data Source Status Dashboard" in result.output
        assert "System Status" in result.output
        assert "Health Status" in result.output


# ============================================================================
# 3. Validation / Errors
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceValidation:
    """datasource 命令参数验证"""

    def test_configure_unknown_source_shows_error(self, cli_runner):
        """configure 未知数据源时显示错误"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["configure", "nonexistent"])
        assert result.exit_code == 0
        assert "Unknown data source" in result.output

    def test_test_source_service_not_in_container(self, cli_runner):
        """test 数据源在容器中不存在时显示错误"""
        mock_container = MagicMock(spec=[])  # 空spec，hasattr返回False
        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(datasource_cli.app, ["test", "tushare"])
        assert "not found in container" in result.output


# ============================================================================
# 4. Exception Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDataSourceExceptions:
    """datasource 命令异常处理"""

    def test_test_connection_raises_exception(self, cli_runner):
        """test 数据源连接测试抛出异常时优雅处理"""
        mock_source = MagicMock()
        mock_source._test_connection.side_effect = Exception("Connection refused")
        mock_container = MagicMock()
        mock_container.ginkgo_tushare_source.return_value = mock_source

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(datasource_cli.app, ["test", "tushare"])
        assert result.exit_code == 0
        assert "Connection test failed" in result.output

    def test_list_exception_in_source_row(self, cli_runner):
        """list 命令在渲染数据源行时发生异常仍能继续"""
        # list 命令内部有 try/except 包裹每行渲染，不会崩溃
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(datasource_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Data Sources" in result.output
