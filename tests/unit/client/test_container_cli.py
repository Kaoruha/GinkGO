"""
Container CLI 单元测试

测试 ginkgo.client.container_cli 的所有命令：
- status: 显示 DI 容器状态和健康信息
- services: 列出所有注册的服务
- dependencies: 显示服务依赖图
- health: 执行容器健康检查
- reset: 重置 DI 容器
- test: 运行容器架构测试
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from ginkgo.client import container_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestContainerCLIHelp:
    """container 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """container --help 显示所有可用子命令"""
        result = cli_runner.invoke(container_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "status" in result.output
        assert "services" in result.output
        assert "dependencies" in result.output
        assert "health" in result.output
        assert "reset" in result.output
        assert "test" in result.output

    def test_test_help_shows_options(self, cli_runner):
        """container test --help 显示测试选项"""
        result = cli_runner.invoke(container_cli.app, ["test", "--help"])
        assert result.exit_code == 0
        assert "--unit" in result.output
        assert "--integration" in result.output
        assert "--all" in result.output


# ============================================================================
# 2. Main Commands Happy Path
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestContainerStatus:
    """container status 命令"""

    def test_status_shows_dashboard(self, cli_runner):
        """status 命令显示 DI 容器状态面板"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(container_cli.app, ["status"])
        assert result.exit_code == 0
        assert "DI Container Status Dashboard" in result.output
        assert "Container Status" in result.output
        assert "Service Health" in result.output
        assert "Performance" in result.output

    def test_services_shows_registered_list(self, cli_runner):
        """services 命令列出已注册服务"""
        with patch("ginkgo.data.containers.container"):
            result = cli_runner.invoke(container_cli.app, ["services"])
        assert result.exit_code == 0
        assert "Registered Services" in result.output
        assert "stockinfo_service" in result.output
        assert "bar_service" in result.output
        assert "Total services registered" in result.output


# ============================================================================
# 3. Dependencies and Health
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestContainerDependencies:
    """container dependencies 命令"""

    def test_dependencies_shows_tree(self, cli_runner):
        """dependencies 命令显示服务依赖树"""
        result = cli_runner.invoke(container_cli.app, ["dependencies"])
        assert result.exit_code == 0
        assert "Dependency Graph" in result.output
        assert "Data Services" in result.output
        assert "Management Services" in result.output
        assert "Infrastructure Services" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestContainerHealth:
    """container health 命令"""

    def test_health_all_healthy(self, cli_runner):
        """health 检查所有服务健康时显示成功"""
        mock_container = MagicMock()
        mock_container.stockinfo_service.return_value = MagicMock()
        mock_container.bar_service.return_value = MagicMock()
        mock_container.tick_service.return_value = MagicMock()
        mock_container.adjustfactor_service.return_value = MagicMock()
        mock_container.cruds.bar.return_value = MagicMock()
        mock_container.cruds.stock_info.return_value = MagicMock()
        mock_container.cruds.adjustfactor.return_value = MagicMock()

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(container_cli.app, ["health"])
        assert result.exit_code == 0
        assert "Healthy Services" in result.output
        assert "health checks passed" in result.output.lower()


# ============================================================================
# 4. Reset Command
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestContainerReset:
    """container reset 命令"""

    def test_reset_cancelled_by_user(self, cli_runner):
        """reset 用户取消操作时不执行重置"""
        with patch("rich.prompt.Confirm") as mock_confirm, \
             patch("ginkgo.data.containers.container"):
            mock_confirm.ask.return_value = False
            result = cli_runner.invoke(container_cli.app, ["reset"])
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()


# ============================================================================
# 5. Exception Handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestContainerExceptions:
    """container 命令异常处理"""

    def test_health_crud_factory_not_found(self, cli_runner):
        """health 检查时 CRUD factory 不存在时显示错误"""
        mock_container = MagicMock()
        mock_container.stockinfo_service.return_value = MagicMock()
        mock_container.bar_service.return_value = MagicMock()
        mock_container.tick_service.return_value = MagicMock()
        mock_container.adjustfactor_service.return_value = MagicMock()
        # 没有 cruds 属性
        del mock_container.cruds

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(container_cli.app, ["health"])
        assert result.exit_code == 0
        assert "Errors" in result.output
        assert "CRUD factory not found" in result.output

    def test_test_command_delegates_to_subprocess(self, cli_runner):
        """test 命令委托给子进程执行"""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = cli_runner.invoke(container_cli.app, ["test", "--unit"])
        assert result.exit_code == 0
        assert "completed successfully" in result.output
