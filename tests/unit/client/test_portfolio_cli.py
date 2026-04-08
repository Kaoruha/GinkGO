"""
性能: 222MB RSS, 2.03s, 27 tests [PASS]
Portfolio CLI 单元测试

测试 ginkgo.client.portfolio_cli 的所有命令：
- list: 列出所有投资组合
- create: 创建新投资组合
- get: 查看投资组合详情
- status: 查看投资组合状态
- delete: 删除投资组合
- bind-component: 绑定组件到投资组合
- unbind-component: 解绑组件
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from typer.testing import CliRunner

from ginkgo.client import portfolio_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


class FakeModelList:
    """模拟 ModelList，提供 to_dataframe() 方法（源码依赖此接口）"""

    def __init__(self, df: pd.DataFrame):
        self._df = df

    def to_dataframe(self) -> pd.DataFrame:
        return self._df


@pytest.fixture
def mock_portfolio_list_df():
    """标准 portfolio 测试 DataFrame"""
    return pd.DataFrame({
        "uuid": ["portfolio-uuid-001", "portfolio-uuid-002"],
        "name": ["TestPortfolio", "LivePortfolio"],
        "initial_capital": [1000000.0, 2000000.0],
        "current_capital": [950000.0, 2100000.0],
        "cash": [500000.0, 1000000.0],
        "is_live": [False, True],
        "status": ["Ready", "Running"],
        "desc": ["Test desc", "Live desc"],
    })


@pytest.fixture
def mock_portfolio():
    """单个 mock portfolio 实体"""
    p = MagicMock()
    p.uuid = "portfolio-uuid-001"
    p.name = "TestPortfolio"
    p.initial_capital = 1000000.0
    p.current_capital = 950000.0
    p.cash = 500000.0
    p.is_live = False
    p.desc = "Test description"
    return p


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioHelp:
    """portfolio 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """portfolio --help 显示所有可用子命令"""
        result = cli_runner.invoke(portfolio_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "create" in result.output
        assert "get" in result.output
        assert "status" in result.output
        assert "delete" in result.output
        assert "bind-component" in result.output
        assert "unbind-component" in result.output

    def test_list_help_shows_options(self, cli_runner):
        """portfolio list --help 显示 list 命令选项"""
        result = cli_runner.invoke(portfolio_cli.app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--status" in result.output
        assert "--limit" in result.output
        assert "--raw" in result.output


# ============================================================================
# 2. List 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioList:
    """portfolio list 命令"""

    @patch("ginkgo.data.containers.container")
    def test_list_all_portfolios(self, mock_container, cli_runner, mock_portfolio_list_df):
        """成功列出所有 portfolio"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(
            data=FakeModelList(mock_portfolio_list_df)
        )
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list"])
        assert result.exit_code == 0
        assert "TestPortfolio" in result.output
        assert "LivePortfolio" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_empty_portfolios(self, mock_container, cli_runner):
        """没有 portfolio 时显示提示"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(
            data=FakeModelList(pd.DataFrame())
        )
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list"])
        assert result.exit_code == 0
        assert "No portfolios found" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_raw_output(self, mock_container, cli_runner, mock_portfolio_list_df):
        """--raw 模式输出 JSON 格式数据"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(
            data=FakeModelList(mock_portfolio_list_df)
        )
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list", "--raw"])
        assert result.exit_code == 0
        assert "TestPortfolio" in result.output
        assert "portfolio-uuid-001" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_service_error(self, mock_container, cli_runner):
        """服务返回错误时显示错误信息"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.error(error="Database connection failed")
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Failed to get portfolios" in result.output
        assert "Database connection failed" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_service_exception(self, mock_container, cli_runner):
        """服务抛出异常时显示错误信息"""
        mock_container.portfolio_service.side_effect = Exception("Unexpected error")

        result = cli_runner.invoke(portfolio_cli.app, ["list"])
        assert result.exit_code == 0
        assert "Error" in result.output


# ============================================================================
# 3. Create 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioCreate:
    """portfolio create 命令"""

    @patch("ginkgo.data.containers.container")
    def test_create_success(self, mock_container, cli_runner, mock_portfolio):
        """成功创建 portfolio"""
        mock_service = MagicMock()
        mock_service.create.return_value = ServiceResult.success(data=mock_portfolio)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "create", "--name", "MyPortfolio", "--capital", "500000"
        ])
        assert result.exit_code == 0
        assert "created successfully" in result.output
        assert "MyPortfolio" in result.output
        assert "500,000" in result.output

    @patch("ginkgo.data.containers.container")
    def test_create_live_portfolio(self, mock_container, cli_runner, mock_portfolio):
        """创建实盘 portfolio"""
        mock_service = MagicMock()
        mock_service.create.return_value = ServiceResult.success(data=mock_portfolio)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "create", "--name", "LivePF", "--live"
        ])
        assert result.exit_code == 0
        assert "Live" in result.output

    @patch("ginkgo.data.containers.container")
    def test_create_missing_name(self, mock_container, cli_runner):
        """缺少 --name 参数时失败"""
        result = cli_runner.invoke(portfolio_cli.app, ["create"])
        assert result.exit_code != 0

    @patch("ginkgo.data.containers.container")
    def test_create_service_error(self, mock_container, cli_runner):
        """服务返回错误时创建失败"""
        mock_service = MagicMock()
        mock_service.create.return_value = ServiceResult.error(error="Name already exists")
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "create", "--name", "DupPortfolio"
        ])
        assert result.exit_code == 1
        assert "creation failed" in result.output

    @patch("ginkgo.data.containers.container")
    def test_create_service_exception(self, mock_container, cli_runner):
        """服务抛出异常时创建失败"""
        mock_container.portfolio_service.side_effect = Exception("DB down")

        result = cli_runner.invoke(portfolio_cli.app, [
            "create", "--name", "BadPortfolio"
        ])
        assert result.exit_code == 1
        assert "Error" in result.output


# ============================================================================
# 4. Get 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioGet:
    """portfolio get 命令"""

    @patch("ginkgo.data.containers.container")
    def test_get_by_uuid(self, mock_container, cli_runner, mock_portfolio):
        """通过 UUID 查看 portfolio 详情"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=mock_portfolio)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["get", "portfolio-uuid-001"])
        assert result.exit_code == 0
        assert "portfolio-uuid-001" in result.output
        assert "TestPortfolio" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_by_name_fallback(self, mock_container, cli_runner, mock_portfolio):
        """UUID 查找失败时回退到按名称查找"""
        mock_service = MagicMock()
        # 第一次按 UUID 查找返回空列表，第二次按 name 查找成功
        mock_service.get.side_effect = [
            ServiceResult.success(data=[]),
            ServiceResult.success(data=mock_portfolio),
        ]
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["get", "TestPortfolio"])
        assert result.exit_code == 0
        assert "TestPortfolio" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_not_found(self, mock_container, cli_runner):
        """portfolio 不存在时返回错误"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.error(error="Not found")
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["get", "nonexistent-uuid"])
        assert result.exit_code == 1
        assert "Failed to get portfolio" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_with_details_empty_components(self, mock_container, cli_runner, mock_portfolio):
        """--details 显示组件绑定（无组件时提示）"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=mock_portfolio)

        mock_mapping_crud = MagicMock()
        mock_mapping_crud.find.return_value = []
        mock_container.portfolio_service.return_value = mock_service
        mock_container.cruds.portfolio_file_mapping.return_value = mock_mapping_crud

        result = cli_runner.invoke(portfolio_cli.app, ["get", "portfolio-uuid-001", "--details"])
        assert result.exit_code == 0
        assert "No component bindings" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_service_exception(self, mock_container, cli_runner):
        """服务抛出异常时 get 失败"""
        mock_container.portfolio_service.side_effect = Exception("Connection refused")

        result = cli_runner.invoke(portfolio_cli.app, ["get", "some-uuid"])
        assert result.exit_code == 1
        assert "Error" in result.output


# ============================================================================
# 5. Delete 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioDelete:
    """portfolio delete 命令"""

    @patch("ginkgo.data.containers.container")
    def test_delete_with_confirm(self, mock_container, cli_runner):
        """使用 --confirm 成功删除"""
        mock_service = MagicMock()
        mock_service.delete.return_value = ServiceResult.success(data=None)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "delete", "portfolio-uuid-001", "--confirm"
        ])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    def test_delete_missing_confirm(self, cli_runner):
        """缺少 --confirm 时拒绝删除"""
        result = cli_runner.invoke(portfolio_cli.app, [
            "delete", "portfolio-uuid-001"
        ])
        assert result.exit_code == 1
        assert "--confirm" in result.output

    @patch("ginkgo.data.containers.container")
    def test_delete_service_error(self, mock_container, cli_runner):
        """服务返回错误时删除失败"""
        mock_service = MagicMock()
        mock_service.delete.return_value = ServiceResult.error(error="Portfolio not found")
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "delete", "bad-uuid", "--confirm"
        ])
        assert result.exit_code == 1
        assert "Failed to delete portfolio" in result.output


# ============================================================================
# 6. Bind/Unbind 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioBindComponent:
    """portfolio bind-component 命令"""

    @patch("ginkgo.data.containers.container")
    def test_bind_success(self, mock_container, cli_runner, mock_portfolio):
        """成功绑定组件到 portfolio"""
        mock_pf_service = MagicMock()
        # bind 源码检查 len(data) > 0，需要传列表
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file = MagicMock()
        mock_file.uuid = "file-uuid-001"
        mock_file.name = "MyStrategy"

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(data=mock_file)

        mock_mapping = MagicMock()
        mock_mapping.uuid = "mapping-uuid-001"

        mock_mapping_service = MagicMock()
        mock_mapping_service.create_portfolio_file_binding.return_value = ServiceResult.success(data=mock_mapping)
        mock_mapping_service.create_component_parameters.return_value = ServiceResult.success(data=None)

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service
        mock_container.mapping_service.return_value = mock_mapping_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "bind-component", "TestPortfolio", "MyStrategy", "--type", "strategy"
        ])
        assert result.exit_code == 0
        assert "binding created successfully" in result.output

    @patch("ginkgo.data.containers.container")
    def test_bind_with_params(self, mock_container, cli_runner, mock_portfolio):
        """绑定组件并设置参数"""
        mock_pf_service = MagicMock()
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file = MagicMock()
        mock_file.uuid = "file-uuid-002"
        mock_file.name = "RiskMgr"

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(data=mock_file)

        mock_mapping = MagicMock()
        mock_mapping.uuid = "mapping-uuid-002"

        mock_mapping_service = MagicMock()
        mock_mapping_service.create_portfolio_file_binding.return_value = ServiceResult.success(data=mock_mapping)
        mock_mapping_service.create_component_parameters.return_value = ServiceResult.success(data=None)

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service
        mock_container.mapping_service.return_value = mock_mapping_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "bind-component", "TestPortfolio", "RiskMgr",
            "--type", "risk", "--param", "0:0.1", "--param", "1:100"
        ])
        assert result.exit_code == 0
        assert "binding created successfully" in result.output
        assert "2 parameter(s) set" in result.output

    def test_bind_missing_type(self, cli_runner):
        """缺少 --type 参数时失败"""
        result = cli_runner.invoke(portfolio_cli.app, [
            "bind-component", "portfolio-id", "file-id"
        ])
        assert result.exit_code != 0

    @patch("ginkgo.data.containers.container")
    def test_bind_invalid_type(self, mock_container, cli_runner, mock_portfolio):
        """无效的组件类型时失败"""
        mock_pf_service = MagicMock()
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(
            data=MagicMock(uuid="f-1", name="Comp")
        )

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "bind-component", "TestPortfolio", "Comp", "--type", "invalid_type"
        ])
        assert result.exit_code == 1
        assert "Invalid component type" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioUnbindComponent:
    """portfolio unbind-component 命令"""

    @patch("ginkgo.data.containers.container")
    def test_unbind_success(self, mock_container, cli_runner, mock_portfolio):
        """成功解绑组件"""
        mock_pf_service = MagicMock()
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file = MagicMock()
        mock_file.uuid = "file-uuid-001"
        mock_file.name = "MyStrategy"

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(data=mock_file)

        mock_mapping_service = MagicMock()
        mock_mapping_service.delete_portfolio_file_binding.return_value = ServiceResult.success(data=None)

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service
        mock_container.mapping_service.return_value = mock_mapping_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "unbind-component", "TestPortfolio", "MyStrategy", "--confirm"
        ])
        assert result.exit_code == 0
        assert "binding deleted successfully" in result.output

    def test_unbind_missing_confirm(self, cli_runner):
        """缺少 --confirm 时拒绝解绑"""
        result = cli_runner.invoke(portfolio_cli.app, [
            "unbind-component", "portfolio-id", "file-id"
        ])
        assert result.exit_code == 1
        assert "--confirm" in result.output

    @patch("ginkgo.data.containers.container")
    def test_unbind_service_error(self, mock_container, cli_runner, mock_portfolio):
        """服务返回错误时解绑失败"""
        mock_pf_service = MagicMock()
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file = MagicMock()
        mock_file.uuid = "file-uuid-003"

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(data=mock_file)

        mock_mapping_service = MagicMock()
        mock_mapping_service.delete_portfolio_file_binding.return_value = ServiceResult.error(
            error="Binding not found"
        )

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service
        mock_container.mapping_service.return_value = mock_mapping_service

        result = cli_runner.invoke(portfolio_cli.app, [
            "unbind-component", "TestPortfolio", "SomeFile", "--confirm"
        ])
        assert result.exit_code == 1
        assert "Failed to delete binding" in result.output
