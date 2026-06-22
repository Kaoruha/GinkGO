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

    def test_get_help_marks_unimplemented_as_planned(self, cli_runner):
        """data get help 区分"可用"与 [planned] 未实现的 data_type（#4900/#5242）。

        adjustfactor/sources 已实现（PR #6234：接 service / 列数据源），列入可用；
        calendar 仍未实现（dispatch 友好提示 planned 而非 Unknown data type，#5919），help 标 [planned]。
        help 必须与实际一致，否则误导用户——#6230 旧的 [planned: calendar/adjustfactor/sources]
        在 #6234 实现两者后已过时。
        """
        result = cli_runner.invoke(data_cli.app, ["get", "--help"])
        assert result.exit_code == 0
        out = result.output
        # 可用类型应列出（adjustfactor/sources 已实现，移入可用括号内）
        assert "(stockinfo/day/tick/adjustfactor/sources)" in out
        # calendar 仍未实现，必须带 [planned] 标注，且 planned 里只剩 calendar
        assert "[planned: calendar]" in out
        # 旧的 planned 多项列表不应再出现（calendar 后不再跟 adjustfactor）
        assert "calendar/adjustfactor" not in out

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
        """使用 --filter 模糊过滤（DF 出口，客户端模糊匹配）"""
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_stockinfo_df)
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
    def test_get_stockinfo_passes_code_to_service(self, mock_container, cli_runner, mock_stockinfo_df):
        """--code 过滤透传到 service.get_stockinfos_df (#5950)"""
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_stockinfo_df)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--code", "000001.SZ"])
        assert result.exit_code == 0
        # 核心：code 必须透传到 DF 出口，而非只靠 --filter 客户端模糊匹配
        mock_service.get_stockinfos_df.assert_called_once()
        _, kwargs = mock_service.get_stockinfos_df.call_args
        assert kwargs.get("code") == "000001.SZ"

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_raw_mode(self, mock_container, cli_runner, mock_stockinfo_df):
        """--raw 模式输出 JSON（DF 出口）"""
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_stockinfo_df)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--raw"])
        assert result.exit_code == 0
        # 验证输出包含 JSON 格式的数据
        assert "000001.SZ" in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_service_error(self, mock_container, cli_runner):
        """服务返回错误时显示错误信息（DF 出口 else 分支）"""
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.error(error="Database connection failed")
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

    def test_get_calendar_shows_planned_not_unknown(self, cli_runner):
        """#5919: calendar 在 help 标 [planned]，dispatch 应提示 planned/未实现，
        不应报通用 'Unknown data type'（help 已声明该类型，只是未实现）。
        区别于 test_get_unknown_data_type（nonexistent 真未知 → Unknown）。"""
        result = cli_runner.invoke(data_cli.app, ["get", "calendar"])
        out = result.output.lower()
        assert "planned" in out or "not yet implemented" in out
        assert "unknown data type" not in out

    def test_get_sources_lists_configured_sources(self, cli_runner):
        """sources 数据类型列出已配置的数据源（不再显示 not yet implemented 桩）"""
        result = cli_runner.invoke(data_cli.app, ["get", "sources"])
        assert result.exit_code == 0
        assert "not yet implemented" not in result.output
        # 容器注入了 tushare/tdx（containers.py），应被列出
        assert "tushare" in result.output.lower()


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
        """同步 stockinfo 成功：调用 service.sync() 并打印 success/total（非桩）"""
        mock_service = MagicMock()
        mock_service.sync.return_value = ServiceResult.success(
            data=MagicMock(),
            message="Stock info sync completed: 5529 records processed",
        )
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["sync", "stockinfo"])
        assert result.exit_code == 0
        assert "Syncing stock information" in result.output
        # 核心行为：必须真正调用 service.sync()，而不是桩
        mock_service.sync.assert_called_once()
        assert "not yet implemented" not in result.output
        # 输出含 success/total，与 day/adjustfactor 同款
        assert "5529" in result.output

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
        from ginkgo.libs.data.results.data_sync_result import DataSyncResult
        from datetime import datetime

        mock_bar_service = MagicMock()
        sync_data = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2025, 1, 1), datetime(2025, 6, 1)),
            records_processed=10,
            records_added=10,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.5,
            is_idempotent=True,
            sync_strategy="smart",
        )
        mock_bar_service.sync_smart.return_value = ServiceResult.success(
            data=sync_data,
            message="Successfully synced 10 bar records for 000001.SZ",
        )
        mock_hub.data.bar_service.return_value = mock_bar_service

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--code", "000001.SZ"])
        assert result.exit_code == 0
        import re
        output_clean = re.sub(r'\x1b\[[0-9;]*m', '', result.output)
        assert "000001.SZ" in output_clean

    @patch("ginkgo.service_hub")
    def test_sync_day_records_added_zero_counts_skipped(self, mock_hub, cli_runner):
        """records_added=0（源无数据）计入 skipped_count，汇总行含 Skipped"""
        from ginkgo.libs.data.results.data_sync_result import DataSyncResult
        from datetime import datetime
        import re

        mock_bar_service = MagicMock()
        sync_data = DataSyncResult(
            entity_type="bars",
            entity_identifier="SH999999",
            sync_range=(datetime(2025, 1, 1), datetime(2025, 6, 1)),
            records_processed=0,
            records_added=0,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.5,
            is_idempotent=True,
            sync_strategy="smart",
        )
        mock_bar_service.sync_smart.return_value = ServiceResult.success(
            data=sync_data,
            message="Successfully synced 0 bar records for SH999999",
        )
        mock_hub.data.bar_service.return_value = mock_bar_service

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--code", "SH999999"])
        assert result.exit_code == 0
        output_clean = re.sub(r'\x1b\[[0-9;]*m', '', result.output)
        # 第三态：源无数据，计入 Skipped 而非漏统计
        assert "Skipped: 1" in output_clean
        assert "Success: 0" in output_clean

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

    @patch("ginkgo.service_hub")
    def test_sync_day_no_data_available(self, mock_hub, cli_runner):
        """sync 返回成功但 records_added=0 时不应显示误导性的 sync completed"""
        from ginkgo.libs.data.results.data_sync_result import DataSyncResult
        from datetime import datetime

        mock_bar_service = MagicMock()
        sync_data = DataSyncResult(
            entity_type="bars",
            entity_identifier="SH600000",
            sync_range=(datetime(2025, 1, 1), datetime(2025, 6, 1)),
            records_processed=0,
            records_added=0,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.5,
            is_idempotent=True,
            sync_strategy="range",
            warnings=["No new data available from source"],
        )
        mock_bar_service.sync_smart.return_value = ServiceResult.success(
            data=sync_data,
            message="No new data available from source",
        )
        mock_hub.data.bar_service.return_value = mock_bar_service

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--code", "SH600000"])
        assert result.exit_code == 0
        # 不应显示 ✅ 误导性的 per-code 成功消息（汇总行中的 "Day sync completed" 是允许的）
        assert "✅ SH600000 sync completed" not in result.output
        # 应显示无数据的提示
        assert "no data" in result.output.lower() or "warning" in result.output.lower()

    @patch("ginkgo.service_hub")
    def test_sync_day_with_records_shows_success(self, mock_hub, cli_runner):
        """sync 返回 records_added>0 时显示成功消息含记录数"""
        from ginkgo.libs.data.results.data_sync_result import DataSyncResult
        from datetime import datetime

        mock_bar_service = MagicMock()
        sync_data = DataSyncResult(
            entity_type="bars",
            entity_identifier="600000.SH",
            sync_range=(datetime(2025, 1, 1), datetime(2025, 6, 1)),
            records_processed=120,
            records_added=120,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=1.2,
            is_idempotent=True,
            sync_strategy="range",
        )
        mock_bar_service.sync_smart.return_value = ServiceResult.success(
            data=sync_data,
            message="Successfully synced 120 bar records for 600000.SH",
        )
        mock_hub.data.bar_service.return_value = mock_bar_service

        result = cli_runner.invoke(data_cli.app, ["sync", "day", "--code", "600000.SH"])
        assert result.exit_code == 0
        import re
        output_clean = re.sub(r'\x1b\[[0-9;]*m', '', result.output)
        assert "600000.SH" in output_clean
        assert "120" in output_clean or "sync completed" in output_clean

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


@pytest.mark.unit
@pytest.mark.cli
class TestDataGetStatusStub:
    """#5992 data get status 返回友好 stub，而非 'Unknown data type: status'"""

    def test_get_status_returns_friendly_not_unknown(self, cli_runner):
        """data get status → exit 0，不含 'Unknown data type'，友好提示 status"""
        result = cli_runner.invoke(data_cli.app, ["get", "status"])
        assert result.exit_code == 0
        assert "Unknown data type" not in result.output
        out_lower = result.output.lower()
        assert "status" in out_lower
