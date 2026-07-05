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
import re

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from typer.testing import CliRunner

from ginkgo.client import portfolio_cli
from ginkgo.data.services.base_service import ServiceResult


def _strip_ansi(text: str) -> str:
    """去除 ANSI 转义码，便于断言"""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


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
    return pd.DataFrame(
        {
            "uuid": ["portfolio-uuid-001", "portfolio-uuid-002"],
            "name": ["TestPortfolio", "LivePortfolio"],
            "initial_capital": [1000000.0, 2000000.0],
            "current_capital": [950000.0, 2100000.0],
            "cash": [500000.0, 1000000.0],
            "is_live": [False, True],
            "status": ["Ready", "Running"],
            "desc": ["Test desc", "Live desc"],
        }
    )


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
    p.mode = 0  # BACKTEST 枚举值（整数）
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
        assert "--page" in result.output
        assert "--page-size" in result.output
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
        mock_service.get_portfolios_df.return_value = ServiceResult.success(data=mock_portfolio_list_df)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list"])
        assert result.exit_code == 0
        assert "TestPortfolio" in result.output
        assert "LivePortfolio" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_passes_page_and_page_size(self, mock_container, cli_runner, mock_portfolio_list_df):
        """#5009: portfolio list supports --page/--page-size while preserving --limit alias."""
        mock_service = MagicMock()
        mock_service.get_portfolios_df.return_value = ServiceResult.success(data=mock_portfolio_list_df)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list", "--page", "1", "--page-size", "5"])

        assert result.exit_code == 0, result.output
        mock_service.get_portfolios_df.assert_called_once_with(page=1, page_size=5)

    @patch("ginkgo.data.containers.container")
    def test_list_shows_pagination_hint_when_full_page(
        self, mock_container, cli_runner, mock_portfolio_list_df
    ):
        """#5009 review-1a: 满页时显示分页提示（对齐 record signal）。"""
        mock_service = MagicMock()
        mock_service.get_portfolios_df.return_value = ServiceResult.success(data=mock_portfolio_list_df)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list", "--page-size", "2"])

        assert result.exit_code == 0, result.output
        assert "Showing page" in result.output
        assert "Use --page-size 0" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_empty_portfolios(self, mock_container, cli_runner):
        """没有 portfolio 时显示提示"""
        mock_service = MagicMock()
        mock_service.get_portfolios_df.return_value = ServiceResult.success(data=pd.DataFrame())
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list"])
        assert result.exit_code == 0
        assert "No portfolios found" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_raw_output(self, mock_container, cli_runner, mock_portfolio_list_df):
        """--raw 模式输出 JSON 格式数据"""
        mock_service = MagicMock()
        mock_service.get_portfolios_df.return_value = ServiceResult.success(data=mock_portfolio_list_df)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["list", "--raw"])
        assert result.exit_code == 0
        assert "TestPortfolio" in result.output
        assert "portfolio-uuid-001" in result.output

    @patch("ginkgo.data.containers.container")
    def test_list_service_error(self, mock_container, cli_runner):
        """服务返回错误时显示错误信息"""
        mock_service = MagicMock()
        mock_service.get_portfolios_df.return_value = ServiceResult.error(error="Database connection failed")
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
        mock_service.add.return_value = ServiceResult.success(
            data={"uuid": "new-portfolio-uuid", "name": "MyPortfolio"}
        )
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "MyPortfolio", "--capital", "500000"])
        assert result.exit_code == 0
        output = _strip_ansi(result.output)
        assert "created successfully" in output
        assert "MyPortfolio" in output
        assert "500,000" in output

    @patch("ginkgo.data.containers.container")
    def test_create_passes_initial_capital_to_service(self, mock_container, cli_runner):
        """#5331 create 命令必须将 initial_capital 传给 service.add()"""
        mock_service = MagicMock()
        mock_service.add.return_value = ServiceResult.success(data={"uuid": "new-uuid", "name": "CapTest"})
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "CapTest", "--capital", "2000000"])
        assert result.exit_code == 0
        # 验证 service.add 被调用时传入了 initial_capital
        call_kwargs = mock_service.add.call_args
        assert call_kwargs is not None
        # 传入的 capital 值应为 2000000
        passed_capital = call_kwargs.kwargs.get("initial_capital") or call_kwargs[1].get("initial_capital")
        assert passed_capital == 2000000.0

    @patch("ginkgo.data.containers.container")
    def test_create_live_portfolio(self, mock_container, cli_runner, mock_portfolio):
        """创建实盘 portfolio"""
        mock_service = MagicMock()
        mock_service.add.return_value = ServiceResult.success(data={"uuid": "live-uuid", "name": "LivePF"})
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "LivePF", "--live"])
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
        mock_service.add.return_value = ServiceResult.error(error="Name already exists")
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "DupPortfolio"])
        assert result.exit_code == 1
        assert "creation failed" in result.output

    @patch("ginkgo.data.containers.container")
    def test_create_service_exception(self, mock_container, cli_runner):
        """服务抛出异常时创建失败"""
        mock_container.portfolio_service.side_effect = Exception("DB down")

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "BadPortfolio"])
        assert result.exit_code == 1
        assert "Error" in result.output

    # #5984: --capital 必须 > 0，拒绝负数和零。

    @patch("ginkgo.data.containers.container")
    def test_create_rejects_negative_capital(self, mock_container, cli_runner):
        """#5984 --capital 为负数时拒绝创建"""
        mock_service = MagicMock()
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "EdgeNeg", "--capital", "-1"])
        assert result.exit_code == 1
        assert "capital" in _strip_ansi(result.output).lower()
        # 负资本绝不应触达 service
        mock_service.add.assert_not_called()

    @patch("ginkgo.data.containers.container")
    def test_create_rejects_zero_capital(self, mock_container, cli_runner):
        """#5984 --capital 为零时拒绝创建（边界）"""
        mock_service = MagicMock()
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "EdgeZero", "--capital", "0"])
        assert result.exit_code == 1
        assert "capital" in _strip_ansi(result.output).lower()
        mock_service.add.assert_not_called()

    @patch("ginkgo.data.containers.container")
    def test_create_accepts_positive_capital(self, mock_container, cli_runner):
        """#5984 正资本仍正常创建（回归守护）"""
        mock_service = MagicMock()
        mock_service.add.return_value = ServiceResult.success(data={"uuid": "ok-uuid", "name": "Ok"})
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["create", "--name", "Ok", "--capital", "0.01"])
        assert result.exit_code == 0
        assert "created successfully" in _strip_ansi(result.output)


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

    @patch("ginkgo.data.containers.container")
    def test_get_mode_shows_readable_text_backtest(self, mock_container, cli_runner, mock_portfolio):
        """#5326 Mode 字段显示 BACKTEST 而非数字 0"""
        mock_portfolio.mode = 0
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=mock_portfolio)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["get", "portfolio-uuid-001"])
        assert result.exit_code == 0
        assert "BACKTEST" in result.output
        # 不应出现裸数字 0 作为 Mode
        lines = result.output.split("\n")
        mode_line = next((l for l in lines if "Mode" in l), None)
        assert mode_line is not None
        # Mode 行不应以数字结尾（排除表格边框中的数字）
        assert "BACKTEST" in mode_line

    @patch("ginkgo.data.containers.container")
    def test_get_mode_shows_readable_text_paper(self, mock_container, cli_runner, mock_portfolio):
        """#5326 Mode 字段显示 PAPER 而非数字 1"""
        mock_portfolio.mode = 1
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=mock_portfolio)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["get", "portfolio-uuid-001"])
        assert result.exit_code == 0
        assert "PAPER" in result.output


# ============================================================================
# 5. Delete 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioDelete:
    """portfolio delete 命令"""

    @patch("ginkgo.data.containers.container")
    def test_delete_with_confirm(self, mock_container, cli_runner, mock_portfolio):
        """使用 --confirm + 完整 UUID 成功删除"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=[mock_portfolio])
        mock_service.delete.return_value = ServiceResult.success(data=None)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "portfolio-uuid-001", "--confirm"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output
        mock_service.delete.assert_called_once_with("portfolio-uuid-001")

    def test_delete_missing_confirm(self, cli_runner):
        """缺少 --confirm 时拒绝删除"""
        result = cli_runner.invoke(portfolio_cli.app, ["delete", "portfolio-uuid-001"])
        assert result.exit_code == 1
        assert "--confirm" in result.output

    @patch("ginkgo.data.containers.container")
    def test_delete_by_name_resolves_uuid(self, mock_container, cli_runner):
        """#5995: 按名称删除——精确 UUID 查空后回退 name 查找，解析出 uuid 再删"""
        mock_service = MagicMock()
        named = MagicMock()
        named.uuid = "resolved-uuid-999"
        mock_service.get.side_effect = [
            ServiceResult.success(data=[]),  # get(portfolio_id=name) 空
            ServiceResult.success(data=[named]),  # get(name=name) 命中
        ]
        mock_service.delete.return_value = ServiceResult.success(data=None)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "deploy_test", "--confirm"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output
        mock_service.delete.assert_called_once_with("resolved-uuid-999")

    @patch("ginkgo.data.containers.container")
    def test_delete_by_partial_uuid_fuzzy(self, mock_container, cli_runner):
        """#5995: 按 partial UUID 模糊匹配——精确 UUID/name 均空后 fuzzy 命中唯一"""
        mock_service = MagicMock()
        fuzzy_hit = MagicMock()
        fuzzy_hit.uuid = "deadbeefdeadbeefdeadbeefdeadbeef"
        mock_service.get.return_value = ServiceResult.success(data=[])
        mock_service.fuzzy_search.return_value = ServiceResult.success(data=[fuzzy_hit])
        mock_service.delete.return_value = ServiceResult.success(data=None)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "deadbeef", "--confirm"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output
        mock_service.fuzzy_search.assert_called_once_with("deadbeef")
        mock_service.delete.assert_called_once_with("deadbeefdeadbeefdeadbeefdeadbeef")

    @patch("ginkgo.data.containers.container")
    def test_delete_ambiguous_fuzzy_rejected(self, mock_container, cli_runner):
        """#5995: fuzzy 多匹配时不删除，提示用完整 UUID"""
        mock_service = MagicMock()
        a, b = MagicMock(), MagicMock()
        a.uuid, b.uuid = "uuid-aaa", "uuid-bbb"
        mock_service.get.return_value = ServiceResult.success(data=[])
        mock_service.fuzzy_search.return_value = ServiceResult.success(data=[a, b])
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "uuid", "--confirm"])
        assert result.exit_code == 1
        assert "Multiple" in result.output or "多个" in result.output
        mock_service.delete.assert_not_called()

    @patch("ginkgo.data.containers.container")
    def test_delete_not_found_clear_error(self, mock_container, cli_runner):
        """#5995: 名称/UUID/fuzzy 均未命中时给明确错误，不报裸异常"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=[])
        mock_service.fuzzy_search.return_value = ServiceResult.success(data=[])
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "nonexistent", "--confirm"])
        assert result.exit_code == 1
        assert "投资组合不存在" in result.output
        mock_service.delete.assert_not_called()

    @patch("ginkgo.data.containers.container")
    def test_delete_service_error(self, mock_container, cli_runner, mock_portfolio):
        """解析成功但 service.delete 返回错误时删除失败"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=[mock_portfolio])
        mock_service.delete.return_value = ServiceResult.error(error="Portfolio not found")
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "portfolio-uuid-001", "--confirm"])
        assert result.exit_code == 1
        assert "Failed to delete portfolio" in result.output

    @patch("ginkgo.data.containers.container")
    def test_delete_with_yes_short_flag(self, mock_container, cli_runner):
        """使用 -y 短标志成功删除（#6006: 统一确认标志跨命令一致）"""
        mock_service = MagicMock()
        mock_service.delete.return_value = ServiceResult.success(data=None)
        mock_container.portfolio_service.return_value = mock_service

        result = cli_runner.invoke(portfolio_cli.app, ["delete", "portfolio-uuid-001", "-y"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output
        mock_service.delete.assert_called_once_with("portfolio-uuid-001")


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

        result = cli_runner.invoke(
            portfolio_cli.app, ["bind-component", "TestPortfolio", "MyStrategy", "--type", "strategy"]
        )
        assert result.exit_code == 0
        assert "binding created successfully" in result.output

    @patch("ginkgo.data.containers.container")
    def test_bind_with_params(self, mock_container, cli_runner, mock_portfolio):
        """绑定组件并设置参数（index 格式向后兼容）"""
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

        result = cli_runner.invoke(
            portfolio_cli.app,
            ["bind-component", "TestPortfolio", "RiskMgr", "--type", "risk", "--param", "0:0.1", "--param", "1:100"],
        )
        assert result.exit_code == 0
        output = _strip_ansi(result.output)
        assert "binding created successfully" in output
        assert "2 parameter(s) set" in output

    def test_bind_missing_type(self, cli_runner):
        """缺少 --type 参数时失败"""
        result = cli_runner.invoke(portfolio_cli.app, ["bind-component", "portfolio-id", "file-id"])
        assert result.exit_code != 0

    @patch("ginkgo.data.containers.container")
    def test_bind_invalid_type(self, mock_container, cli_runner, mock_portfolio):
        """无效的组件类型时失败"""
        mock_pf_service = MagicMock()
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(data=MagicMock(uuid="f-1", name="Comp"))

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service

        result = cli_runner.invoke(
            portfolio_cli.app, ["bind-component", "TestPortfolio", "Comp", "--type", "invalid_type"]
        )
        assert result.exit_code == 1
        assert "Invalid component type" in result.output

    @patch("ginkgo.data.containers.container")
    def test_bind_rejects_keyword_param(self, mock_container, cli_runner, mock_portfolio):
        """ADR-020: 关键字格式 --param short_period:20 已废弃，应报错退出。

        纯位置装配后 CLI 只接受整数 index:value；关键字路径（依赖提取器/
        打分启发式）已移除。回归保护：防止重新引入 name-skip + resolve_param_kwargs
        打分链（#5955→#6032→#6159→#6481）。
        """
        mock_pf_service = MagicMock()
        mock_pf_service.get.return_value = ServiceResult.success(data=[mock_portfolio])

        mock_file = MagicMock()
        mock_file.uuid = "file-uuid-kw"
        mock_file.name = "moving_average_crossover"

        mock_file_service = MagicMock()
        mock_file_service.get_by_uuid.return_value = ServiceResult.success(data=mock_file)

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service

        result = cli_runner.invoke(
            portfolio_cli.app,
            [
                "bind-component",
                "TestPortfolio",
                "moving_average_crossover",
                "--type",
                "strategy",
                "--param",
                "short_period:20",
            ],
        )
        assert result.exit_code != 0
        assert "仅支持整数 index" in result.output


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

        result = cli_runner.invoke(portfolio_cli.app, ["unbind-component", "TestPortfolio", "MyStrategy", "--confirm"])
        assert result.exit_code == 0
        assert "binding deleted successfully" in result.output

    @patch("ginkgo.data.containers.container")
    def test_unbind_with_yes_short_flag(self, mock_container, cli_runner, mock_portfolio):
        """使用 -y 短标志成功解绑（#6006: 统一确认标志跨命令一致）"""
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

        result = cli_runner.invoke(portfolio_cli.app, ["unbind-component", "TestPortfolio", "MyStrategy", "-y"])
        assert result.exit_code == 0
        assert "binding deleted successfully" in result.output
        mock_mapping_service.delete_portfolio_file_binding.assert_called_once()

    def test_unbind_missing_confirm(self, cli_runner):
        """缺少 --confirm 时拒绝解绑"""
        result = cli_runner.invoke(portfolio_cli.app, ["unbind-component", "portfolio-id", "file-id"])
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
        mock_mapping_service.delete_portfolio_file_binding.return_value = ServiceResult.error(error="Binding not found")

        mock_container.portfolio_service.return_value = mock_pf_service
        mock_container.file_service.return_value = mock_file_service
        mock_container.mapping_service.return_value = mock_mapping_service

        result = cli_runner.invoke(portfolio_cli.app, ["unbind-component", "TestPortfolio", "SomeFile", "--confirm"])
        assert result.exit_code == 1
        assert "Failed to delete binding" in result.output


# ============================================================================
# #4666 Bug 2: _generate_baseline_if_possible pagination handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGenerateBaselinePagination:
    """#4666 Bug 2: task_service.list() returns paginated dict, not plain list.

    BacktestTaskService.list() returns ServiceResult.success({
        "data": [...], "total": N, "page": 0, "page_size": 20
    }).
    The code must extract the inner "data" list, not treat the outer dict as a list.
    """

    def test_extracts_task_id_from_paginated_result(self):
        """_generate_baseline_if_possible must extract task_id from paginated dict.

        BacktestTaskService.list() returns ServiceResult.data = {"data": [...], "total": N}.
        The function must unwrap the inner list, not treat the outer dict as a task.
        """
        from ginkgo.client.portfolio_cli import _generate_baseline_if_possible

        # Mock backtest_task_service returning paginated dict
        mock_task = MagicMock()
        mock_task.task_id = "task-abc-123"
        mock_task.engine_id = "engine-xyz"

        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = ServiceResult.success(
            {
                "data": [mock_task],
                "total": 1,
                "page": 0,
                "page_size": 20,
            }
        )

        # Mock evaluator (prevent real evaluation)
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate_backtest_stability.return_value = {
            "status": "success",
            "monitoring_baseline": {"slice_period_days": 30, "baseline_stats": {"sharpe": {}}},
        }

        # Mock redis service
        mock_redis = MagicMock()

        mock_services = MagicMock()
        mock_services.data.backtest_task_service.return_value = mock_task_svc
        mock_services.data.redis_service.return_value = mock_redis

        with (
            patch("ginkgo.services", mock_services),
            patch(
                "ginkgo.trading.analysis.evaluation.backtest_evaluator.BacktestEvaluator", return_value=mock_evaluator
            ),
        ):
            _generate_baseline_if_possible("paper-id", "source-id")

        # The evaluator must have been called with the correct engine_id
        mock_evaluator.evaluate_backtest_stability.assert_called_once_with(
            portfolio_id="source-id",
            engine_id="engine-xyz",
        )

    def test_handles_empty_paginated_result(self):
        """When paginated result has empty data list, function must not crash."""
        from ginkgo.client.portfolio_cli import _generate_baseline_if_possible

        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = ServiceResult.success(
            {
                "data": [],
                "total": 0,
                "page": 0,
                "page_size": 20,
            }
        )

        mock_services = MagicMock()
        mock_services.data.backtest_task_service.return_value = mock_task_svc

        with patch("ginkgo.services", mock_services):
            # Should not crash — just return silently
            _generate_baseline_if_possible("paper-id", "source-id")
