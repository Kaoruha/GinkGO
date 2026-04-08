"""
性能: 222MB RSS, 2.06s, 40 tests [PASS]
Data CLI 单元测试

测试 ginkgo.client.data_cli 的所有命令：
- get: 从数据库获取数据 (stockinfo/bars/tick/adjustfactor/sources)
- status: 显示数据同步状态
- sync: 从外部数据源同步数据 (stockinfo/day/tick/adjustfactor)
- migrate: 数据库迁移管理
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import json
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from typer.testing import CliRunner

from ginkgo.client import data_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_stockinfo_df():
    """标准 stockinfo 测试数据"""
    return pd.DataFrame({
        "code": ["000001.SZ", "000002.SZ", "600000.SH"],
        "code_name": ["平安银行", "万科A", "浦发银行"],
        "industry": ["银行", "房地产", "银行"],
        "market": ["SZ", "SZ", "SH"],
        "list_date": ["1991-04-03", "1991-01-29", "1999-11-10"],
    })


# ============================================================================
# 1. Help 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDataCLIHelp:
    """data 命令帮助信息"""

    def test_root_help_shows_commands(self, cli_runner):
        """data --help 显示所有可用子命令"""
        result = cli_runner.invoke(data_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "get" in result.output
        assert "sync" in result.output
        assert "status" in result.output
        assert "migrate" in result.output

    def test_get_help_shows_options(self, cli_runner):
        """data get --help 显示 get 命令的参数和选项"""
        result = cli_runner.invoke(data_cli.app, ["get", "--help"])
        assert result.exit_code == 0
        assert "--code" in result.output
        assert "--start" in result.output
        assert "--end" in result.output
        assert "--page-size" in result.output
        assert "--filter" in result.output
        assert "--raw" in result.output

    def test_sync_help_shows_options(self, cli_runner):
        """data sync --help 显示 sync 命令的参数"""
        result = cli_runner.invoke(data_cli.app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--daemon" in result.output
        assert "--full" in result.output
        assert "--force" in result.output

    def test_migrate_help_shows_options(self, cli_runner):
        """data migrate --help 显示 migrate 命令的参数"""
        result = cli_runner.invoke(data_cli.app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "--database" in result.output
        assert "--autogenerate" in result.output
        assert "--action" in result.output


# ============================================================================
# 2. get stockinfo 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGetStockinfo:
    """data get stockinfo 命令"""

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_success(self, mock_container, cli_runner, mock_stockinfo_df):
        """成功获取所有 stockinfo 数据"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=mock_stockinfo_df)
        mock_container.stockinfo_service.return_value = mock_service
        mock_data = MagicMock()
        mock_data.to_dataframe.return_value = mock_stockinfo_df
        mock_service.get.return_value.data = mock_data

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo"])
        assert result.exit_code == 0

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_with_filter(self, mock_container, cli_runner, mock_stockinfo_df):
        """使用 --filter 模糊过滤"""
        filtered_df = mock_stockinfo_df[mock_stockinfo_df["industry"] == "银行"]
        mock_service = MagicMock()
        mock_data = MagicMock()
        mock_data.to_dataframe.return_value = mock_stockinfo_df
        mock_service.get.return_value = ServiceResult.success(data=mock_data)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--filter", "银行"])
        assert result.exit_code == 0
        assert "Filter matched" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_with_market_filter(self, mock_container, cli_runner, mock_stockinfo_df):
        """使用 --market 过滤"""
        mock_service = MagicMock()
        mock_data = MagicMock()
        mock_data.to_dataframe.return_value = mock_stockinfo_df
        mock_service.get.return_value = ServiceResult.success(data=mock_data)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--market", "SZ"])
        assert result.exit_code == 0

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_raw_mode(self, mock_container, cli_runner, mock_stockinfo_df):
        """--raw 模式输出 JSON"""
        mock_service = MagicMock()
        mock_data = MagicMock()
        mock_data.to_dataframe.return_value = mock_stockinfo_df
        mock_service.get.return_value = ServiceResult.success(data=mock_data)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--raw"])
        assert result.exit_code == 0
        # 验证输出包含 JSON 格式的数据
        assert "000001.SZ" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_service_error(self, mock_container, cli_runner):
        """服务返回错误时显示错误信息"""
        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.error(error="Database connection failed")
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo"])
        assert result.exit_code == 0  # 不抛异常，只打印错误
        assert "Database connection failed" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_service_raises_exception(self, mock_container, cli_runner):
        """服务抛出异常时正确处理"""
        mock_container.stockinfo_service.side_effect = RuntimeError("Service unavailable")

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo"])
        assert result.exit_code == 1
        assert "Service unavailable" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_filter_no_match(self, mock_container, cli_runner, mock_stockinfo_df):
        """filter 无匹配结果"""
        mock_service = MagicMock()
        mock_data = MagicMock()
        mock_data.to_dataframe.return_value = mock_stockinfo_df
        mock_service.get.return_value = ServiceResult.success(data=mock_data)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--filter", "NONEXISTENT"])
        assert result.exit_code == 0
        assert "No matching records" in result.output


# ============================================================================
# 3. get 其他数据类型测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGetOtherTypes:
    """data get 非 stockinfo 数据类型"""

    def test_get_bars_requires_code(self, cli_runner):
        """获取 bars 数据需要 --code 参数"""
        result = cli_runner.invoke(data_cli.app, ["get", "day"])
        assert result.exit_code == 1
        assert "code" in result.output.lower() or "required" in result.output.lower()

    def test_get_bars_with_code(self, cli_runner):
        """获取 bars 数据提供 code 不崩溃"""
        result = cli_runner.invoke(data_cli.app, ["get", "day", "--code", "000001.SZ"])
        # 命令不会崩溃，虽然功能尚未实现
        assert "not yet implemented" in result.output or result.exit_code == 0

    def test_get_tick_requires_code(self, cli_runner):
        """获取 tick 数据需要 --code 参数"""
        result = cli_runner.invoke(data_cli.app, ["get", "tick"])
        assert result.exit_code == 1
        assert "code" in result.output.lower()

    def test_get_adjustfactor_requires_code(self, cli_runner):
        """获取 adjustfactor 数据需要 --code 参数"""
        result = cli_runner.invoke(data_cli.app, ["get", "adjustfactor"])
        assert result.exit_code == 1
        assert "code" in result.output.lower()

    def test_get_unknown_data_type(self, cli_runner):
        """未知数据类型返回 exit_code 1"""
        result = cli_runner.invoke(data_cli.app, ["get", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown" in result.output or "unknown" in result.output

    def test_get_sources_shows_not_implemented(self, cli_runner):
        """sources 数据类型显示尚未实现"""
        result = cli_runner.invoke(data_cli.app, ["get", "sources"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output


# ============================================================================
# 4. status 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestStatus:
    """data status 命令"""

    def test_status_shows_output(self, cli_runner):
        """status 命令正常执行并输出信息"""
        result = cli_runner.invoke(data_cli.app, ["status"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_status_shows_not_implemented(self, cli_runner):
        """status 命令显示尚未实现"""
        result = cli_runner.invoke(data_cli.app, ["status"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output


# ============================================================================
# 5. sync 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestSync:
    """data sync 命令"""

    @patch("ginkgo.data.containers.container")
    def test_sync_stockinfo_success(self, mock_container, cli_runner):
        """同步 stockinfo 成功"""
        mock_service = MagicMock()
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["sync", "stockinfo"])
        assert result.exit_code == 0
        assert "Syncing stock information" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_stockinfo_service_exception(self, mock_container, cli_runner):
        """同步 stockinfo 时服务抛异常"""
        mock_container.stockinfo_service.side_effect = RuntimeError("Connection error")

        result = cli_runner.invoke(data_cli.app, ["sync", "stockinfo"])
        assert result.exit_code == 1
        assert "Connection error" in result.output

    @patch("ginkgo.service_hub")
    def test_sync_day_with_code(self, mock_hub, cli_runner):
        """同步指定股票的日K线"""
        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.is_success.return_value = True
        mock_bar_service.sync_smart.return_value = mock_sync_result
        mock_hub.data.bar_service.return_value = mock_bar_service

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--code", "000001.SZ"])
        assert result.exit_code == 0
        assert "000001.SZ" in result.output

    def test_sync_day_unknown_type_error(self, cli_runner):
        """sync 未知数据类型返回错误"""
        result = cli_runner.invoke(data_cli.app, ["sync", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_stockinfo_success(self, mock_container, cli_runner):
        """daemon 模式同步 stockinfo 成功入队"""
        mock_kafka = MagicMock()
        mock_kafka.send_stockinfo_update_signal.return_value = True
        mock_container.kafka_service.return_value = mock_kafka

        result = cli_runner.invoke(data_cli.app, ["sync", "stockinfo", "--daemon"])
        assert result.exit_code == 0
        assert "queued" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_stockinfo_failure(self, mock_container, cli_runner):
        """daemon 模式同步 stockinfo 入队失败"""
        mock_kafka = MagicMock()
        mock_kafka.send_stockinfo_update_signal.return_value = False
        mock_container.kafka_service.return_value = mock_kafka

        result = cli_runner.invoke(data_cli.app, ["sync", "stockinfo", "--daemon"])
        assert result.exit_code == 1
        assert "Failed" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_day_with_code(self, mock_container, cli_runner):
        """daemon 模式同步日K线（指定代码）"""
        mock_kafka = MagicMock()
        mock_kafka.send_daybar_update_signal.return_value = True
        mock_container.kafka_service.return_value = mock_kafka

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--code", "000001.SZ", "--daemon"])
        assert result.exit_code == 0
        assert "queued" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_day_all_codes(self, mock_container, cli_runner):
        """daemon 模式同步全部日K线"""
        mock_kafka = MagicMock()
        mock_kafka.send_bar_all_signal.return_value = True
        mock_container.kafka_service.return_value = mock_kafka

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--daemon"])
        assert result.exit_code == 0
        assert "queued" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_tick_with_code(self, mock_container, cli_runner):
        """daemon 模式同步 tick（指定代码）"""
        mock_kafka = MagicMock()
        mock_kafka.send_tick_update_signal.return_value = True
        mock_container.kafka_service.return_value = mock_kafka

        result = cli_runner.invoke(data_cli.app, ["sync", "tick", "--code", "000001.SZ", "--daemon"])
        assert result.exit_code == 0
        assert "queued" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_adjustfactor_with_code(self, mock_container, cli_runner):
        """daemon 模式同步 adjustfactor（指定代码）"""
        mock_kafka = MagicMock()
        mock_kafka.send_adjustfactor_update_signal.return_value = True
        mock_container.kafka_service.return_value = mock_kafka

        result = cli_runner.invoke(data_cli.app, ["sync", "adjustfactor", "--code", "000001.SZ", "--daemon"])
        assert result.exit_code == 0
        assert "queued" in result.output

    @patch("ginkgo.data.containers.container")
    def test_sync_daemon_exception(self, mock_container, cli_runner):
        """daemon 模式同步时服务抛异常"""
        mock_container.kafka_service.side_effect = RuntimeError("Kafka unavailable")

        result = cli_runner.invoke(data_cli.app, ["sync", "stockinfo", "--daemon"])
        assert result.exit_code == 1
        assert "Kafka unavailable" in result.output


# ============================================================================
# 6. migrate 测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestMigrate:
    """data migrate 命令"""

    @patch("subprocess.run")
    def test_migrate_default_shows_status(self, mock_run, cli_runner):
        """默认参数显示 MySQL 迁移状态（默认 action=upgrade 会调用 subprocess）"""
        mock_run.return_value = MagicMock(returncode=0)
        result = cli_runner.invoke(data_cli.app, ["migrate"])
        assert result.exit_code == 0
        assert "upgraded" in result.output.lower()

    @patch("subprocess.run")
    def test_migrate_mysql_upgrade(self, mock_run, cli_runner):
        """MySQL upgrade 操作调用 alembic"""
        mock_run.return_value = MagicMock(returncode=0)
        result = cli_runner.invoke(data_cli.app, ["migrate", "--action", "upgrade"])
        assert result.exit_code == 0
        assert "upgraded" in result.output.lower()

    def test_migrate_clickhouse_shows_manual_instructions(self, cli_runner):
        """ClickHouse 迁移显示手动操作说明"""
        result = cli_runner.invoke(data_cli.app, ["migrate", "--database", "clickhouse"])
        assert result.exit_code == 0
        assert "clickhouse" in result.output.lower()
        assert "Manual" in result.output

    def test_migrate_mongodb_shows_manual_instructions(self, cli_runner):
        """MongoDB 迁移显示手动操作说明"""
        result = cli_runner.invoke(data_cli.app, ["migrate", "--database", "mongodb"])
        assert result.exit_code == 0
        assert "mongodb" in result.output.lower()
        assert "Manual" in result.output

    def test_migrate_unknown_database(self, cli_runner):
        """未知数据库类型返回错误"""
        result = cli_runner.invoke(data_cli.app, ["migrate", "--database", "redis"])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    @patch("subprocess.run")
    def test_migrate_mysql_downgrade_requires_revision(self, mock_run, cli_runner):
        """MySQL downgrade 必须指定 --revision"""
        result = cli_runner.invoke(data_cli.app, ["migrate", "--action", "downgrade"])
        assert result.exit_code == 1
        assert "revision" in result.output.lower()


# ============================================================================
# 7. 杂项 / 边界测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestMisc:
    """杂项和边界条件"""

    def test_no_args_shows_help(self, cli_runner):
        """无参数时显示帮助信息（Typer 对缺失参数返回 exit_code 2）"""
        result = cli_runner.invoke(data_cli.app, [])
        assert result.exit_code != 0
        assert "Usage" in result.output or "get" in result.output

    def test_unknown_command(self, cli_runner):
        """未知子命令返回错误"""
        result = cli_runner.invoke(data_cli.app, ["nonexistent"])
        assert result.exit_code != 0

    def test_get_bars_alias(self, cli_runner):
        """'bars' 作为 'day' 的别名"""
        result = cli_runner.invoke(data_cli.app, ["get", "bars"])
        assert result.exit_code == 1
        assert "code" in result.output.lower()

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_empty_dataframe(self, mock_container, cli_runner):
        """stockinfo 服务返回空 DataFrame"""
        empty_df = pd.DataFrame(columns=["code", "code_name", "industry", "market", "list_date"])
        mock_service = MagicMock()
        mock_data = MagicMock()
        mock_data.to_dataframe.return_value = empty_df
        mock_service.get.return_value = ServiceResult.success(data=mock_data)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo"])
        assert result.exit_code == 0
        assert "No stock records" in result.output
