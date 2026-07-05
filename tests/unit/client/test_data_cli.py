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
    return pd.DataFrame(
        {
            "code": ["000001.SZ", "000002.SZ", "600000.SH"],
            "code_name": ["平安银行", "万科A", "浦发银行"],
            "industry": ["银行", "房地产", "银行"],
            "market": ["SZ", "SZ", "SH"],
            "list_date": ["1991-04-03", "1991-01-29", "1999-11-10"],
        }
    )


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
    def test_get_stockinfo_format_json(self, mock_container, cli_runner, mock_stockinfo_df):
        """--format json：stdout 输出 format_result 契约（ADR-021 第 5/9 维 list 结构）。

        list 结构：``{"success": true, "data": [...], "count": N, "metadata": {}}``。
        显式 ``--format json`` 才走 JSON；auto/default 保持 text 兼容旧脚本。
        """
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_stockinfo_df)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--format", "json"])
        assert result.exit_code == 0
        # 从 output 提取 format_result 的 JSON 行（stdout 可能混 [GCONF] 等日志噪音）
        json_line = next(
            (l for l in result.output.splitlines() if l.strip().startswith('{"success"')),
            None,
        )
        assert json_line is not None, f"未找到 format_result JSON，实际 output:\n{result.output}"
        payload = json.loads(json_line)
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert payload["count"] == 3  # mock_stockinfo_df 3 条
        assert payload["metadata"]["total"] == 3
        codes = [r["code"] for r in payload["data"]]
        assert "000001.SZ" in codes

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_limit_head(self, mock_container, cli_runner):
        """--limit N：stockinfo 分支取前 N 条（head，按 code 排序），ADR-021 第 2 维 order。

        stockinfo = 全量列表（非时序），head 取 code 字典序前 N。任务3：非交互模式
        截断改用 ``--limit``，``--page-size`` 收窄为 TTY 翻页（此处 CliRunner 非 TTY）。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ", "000002.SZ", "000003.SZ", "600000.SH", "600001.SH"],
                "code_name": ["平安银行", "万科A", "A 股票", "浦发银行", "B 股票"],
                "industry": ["银行", "房地产", "科技", "银行", "科技"],
                "market": ["SZ", "SZ", "SZ", "SH", "SH"],
                "list_date": ["1991-04-03", "1991-01-29", "2020-01-01", "1999-11-10", "2021-01-01"],
            }
        )
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--format", "text", "--limit", "2"])
        assert result.exit_code == 0, f"exit≠0, output:\n{result.output}"
        # head sort by code：000001 < 000002 < 000003 < 600000 < 600001，head 2 = 前两条
        assert "000001" in result.output
        assert "000002" in result.output
        assert "000003" not in result.output
        assert "600000" not in result.output

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

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_pagesize_nontty_skips_interactive(self, mock_container, cli_runner, mock_stockinfo_df):
        """非 TTY + --page-size 不进交互分页（#5280：CI/脚本/管道不阻塞）

        CliRunner 注入的 stdin 非 TTY，模拟自动化场景。修复前守卫仅判
        page_size>0 即进交互分支 Prompt.ask，非交互环境阻塞/污染输出。
        """
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_stockinfo_df)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--page-size", "5"])
        assert result.exit_code == 0
        # 不进入交互分支（无 Prompt 标记）
        assert "Interactive mode enabled" not in result.output
        assert "n/p/q" not in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_stockinfo_pagesize_nontty_keeps_text_output(self, mock_container, cli_runner, mock_stockinfo_df):
        """非 TTY + --page-size N：ADR-021 任务3，page-size 仅 TTY 交互翻页生效。

        auto/default 保持 text 输出兼容旧脚本，page-size 不再承担非 TTY 截断语义。
        #5280 的"非 TTY 不阻塞"核心保证仍成立（exit_code==0 不 hang），但输出形式
        仍是 text；截断改由 --limit 承担（见 test_get_stockinfo_limit_head）。
        """
        mock_service = MagicMock()
        mock_service.get_stockinfos_df.return_value = ServiceResult.success(data=mock_stockinfo_df)
        mock_container.stockinfo_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--page-size", "2"])
        assert result.exit_code == 0  # #5280：非 TTY 不阻塞、不 hang
        assert "Interactive mode enabled" not in result.output
        assert '{"success"' not in result.output
        assert "000001" in result.output


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

    @patch("ginkgo.data.containers.container")
    def test_get_day_format_json(self, mock_container, cli_runner):
        """--format json：day 分支走 format_result list 契约（ADR-021 第 5/9 维）。

        list 结构：``{"success": true, "data": [...], "count": N, "metadata": {}}``。
        无 --limit 时全量 records 进 data。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ", "000001.SZ"],
                "timestamp": ["2026-07-01", "2026-07-02"],
                "open": [10.0, 10.5],
                "high": [10.8, 10.9],
                "low": [9.9, 10.3],
                "close": [10.5, 10.7],
                "volume": [100000, 120000],
                "amount": [1050000.0, 1284000.0],
            }
        )
        mock_service.get_bars_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.bar_service.return_value = mock_service

        result = cli_runner.invoke(data_cli.app, ["get", "day", "--code", "000001.SZ", "--format", "json"])
        assert result.exit_code == 0
        json_line = next(
            (l for l in result.output.splitlines() if l.strip().startswith('{"success"')),
            None,
        )
        assert json_line is not None, f"未找到 format_result JSON:\n{result.output}"
        payload = json.loads(json_line)
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert payload["count"] == 2
        assert payload["metadata"]["total"] == 2
        codes = [r["code"] for r in payload["data"]]
        assert "000001.SZ" in codes

    @patch("ginkgo.data.containers.container")
    def test_get_day_limit_tail(self, mock_container, cli_runner):
        """--limit N：day 分支取最新 N 条（tail），ADR-021 第 2 维 order。

        day = 时序行情，交易员关心近期 → tail。同时修复 day 分支隐藏 bug：原 text
        模式直接 ``iterrows()`` 全量打印表格，``--page-size`` 只打印 "Showing N of M"
        提示却**不实际截断**；``--limit`` 落地真正的 tail 截断。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ"] * 5,
                "timestamp": [f"2026-07-0{i}" for i in range(1, 6)],
                "open": [10.0] * 5,
                "high": [10.5] * 5,
                "low": [9.5] * 5,
                "close": [10.2] * 5,
                "volume": [100000] * 5,
                "amount": [1020000.0] * 5,
            }
        )
        mock_service.get_bars_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.bar_service.return_value = mock_service

        result = cli_runner.invoke(
            data_cli.app, ["get", "day", "--code", "000001.SZ", "--format", "text", "--limit", "2"]
        )
        assert result.exit_code == 0, f"exit≠0, output:\n{result.output}"
        # tail：只含最新 2 条 (07-04, 07-05)，不含前 3 条
        assert "2026-07-04" in result.output
        assert "2026-07-05" in result.output
        assert "2026-07-01" not in result.output
        assert "2026-07-03" not in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_tick_limit_tail(self, mock_container, cli_runner):
        """--limit N：tick 分支取最新 N 条（tail），ADR-021 第 2 维 order。

        tick = 分笔时序，最新成交更受关注 → tail。``--limit`` 取代旧 ``--page-size``
        双关用法（任务3：page-size 收窄为交互翻页语义）。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ"] * 5,
                "timestamp": [f"2026-07-01 09:3{i}:00" for i in range(5)],
                "price": [10.0 + i * 0.01 for i in range(5)],
                "volume": [100 + i * 10 for i in range(5)],
                "amount": [1000.0 + i * 100 for i in range(5)],
                "direction": [1] * 5,
            }
        )
        mock_service.get_ticks_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.tick_service.return_value = mock_service

        result = cli_runner.invoke(
            data_cli.app, ["get", "tick", "--code", "000001.SZ", "--format", "text", "--limit", "2"]
        )
        assert result.exit_code == 0, f"exit≠0, output:\n{result.output}"
        # tail：只含最新 2 条 (09:33, 09:34)
        assert "09:33" in result.output
        assert "09:34" in result.output
        assert "09:30" not in result.output
        assert "09:31" not in result.output

    @patch("ginkgo.data.containers.container")
    def test_get_tick_format_json(self, mock_container, cli_runner):
        """--format json：tick 分支走 format_result list 契约（ADR-021 第 5/9 维）。

        --limit 对 json 同样生效，避免机器输出无限膨胀。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ", "000001.SZ"],
                "timestamp": ["2026-07-01 09:30:00", "2026-07-01 09:31:00"],
                "price": [10.0, 10.05],
                "volume": [100, 200],
                "amount": [1000.0, 2010.0],
                "direction": [1, 1],
            }
        )
        mock_service.get_ticks_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.tick_service.return_value = mock_service

        result = cli_runner.invoke(
            data_cli.app, ["get", "tick", "--code", "000001.SZ", "--format", "json", "--limit", "1"]
        )
        assert result.exit_code == 0
        json_line = next(
            (l for l in result.output.splitlines() if l.strip().startswith('{"success"')),
            None,
        )
        assert json_line is not None, f"未找到 format_result JSON:\n{result.output}"
        payload = json.loads(json_line)
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert payload["count"] == 1
        assert payload["metadata"]["total"] == 2
        assert payload["metadata"]["limit"] == 1
        prices = [r["price"] for r in payload["data"]]
        assert prices == [10.05]

    @patch("ginkgo.data.containers.container")
    def test_get_tick_format_json_default_limit(self, mock_container, cli_runner):
        """#6579 review finding 2：tick ``--format json`` 无 ``--limit`` 时须有默认上限。

        tick 默认 7 天窗单股可达 10-50 万行，json 无上限会爆 stdout。取 1000 作默认
        （与文本路径 50 解耦——机读场景需更多样本）。``metadata.limit`` 报实际阈值
        （用户值或默认 1000），让下游知边界而非 ``None``（无限制假象）。
        """
        import pandas as pd

        mock_service = MagicMock()
        # 1500 行 > 默认上限 1000，验证截断生效
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ"] * 1500,
                "timestamp": [f"2026-07-01 09:{i // 60:02d}:{i % 60:02d}:00" for i in range(1500)],
                "price": [10.0 + i * 0.001 for i in range(1500)],
                "volume": [100 + i for i in range(1500)],
                "amount": [1000.0 + i for i in range(1500)],
                "direction": [1] * 1500,
            }
        )
        mock_service.get_ticks_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.tick_service.return_value = mock_service

        result = cli_runner.invoke(
            data_cli.app, ["get", "tick", "--code", "000001.SZ", "--format", "json"]
        )
        assert result.exit_code == 0, f"exit≠0, output:\n{result.output}"
        json_line = next(
            (l for l in result.output.splitlines() if l.strip().startswith('{"success"')),
            None,
        )
        assert json_line is not None, f"未找到 format_result JSON:\n{result.output}"
        payload = json.loads(json_line)
        # 默认上限 1000 生效：count 截断、total 仍是全量 1500、metadata.limit 报阈值
        assert payload["count"] == 1000, f"expected default limit 1000, got count={payload['count']}"
        assert payload["metadata"]["total"] == 1500
        assert payload["metadata"]["limit"] == 1000

    @patch("ginkgo.data.containers.container")
    def test_get_adjustfactor_format_json(self, mock_container, cli_runner):
        """--format json：adjustfactor 分支走 format_result list 契约（ADR-021 第 5/9 维）。

        --format json 优先于 --raw（format 是显式格式选择，raw 是旧 alias，
        task #16 会把 --raw 别名到 --format json）。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ", "000001.SZ"],
                "timestamp": ["2026-07-01", "2026-07-02"],
                "foreadjustfactor": [1.0, 1.001],
                "backadjustfactor": [1.0, 0.999],
                "adjustfactor": [1.0, 1.0005],
            }
        )
        mock_service.get_adjustfactors_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.adjustfactor_service.return_value = mock_service

        result = cli_runner.invoke(
            data_cli.app,
            ["get", "adjustfactor", "--code", "000001.SZ", "--format", "json"],
        )
        assert result.exit_code == 0
        json_line = next(
            (l for l in result.output.splitlines() if l.strip().startswith('{"success"')),
            None,
        )
        assert json_line is not None, f"未找到 format_result JSON:\n{result.output}"
        payload = json.loads(json_line)
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert payload["count"] == 2
        # 因子列正确序列化（非空、是数值）
        factors = [r["foreadjustfactor"] for r in payload["data"]]
        assert 1.0 in factors

    @patch("ginkgo.data.containers.container")
    def test_get_adjustfactor_limit_head(self, mock_container, cli_runner):
        """--limit N：adjustfactor 分支取前 N 条（head），ADR-021 第 2 维 + 任务4 核实结论。

        复权因子是低频事件型数据（一年通常 ≤3 条除权事件），归"全量列表"语义（与
        stockinfo 一致），head 取最早 N 条除权事件。改自原 tail 行为（从 day/tick
        复制的遗留逻辑）；业务理由：复权因子全量条数少，按时间正序阅读除权轨迹更直观。

        #6579 review finding 3：mock df 用**倒序输入**（最新在前），复现 review 实测的
        覆盖盲区——文本路径缺 ``sort_values`` 时 head 取到的是最新 N 条而非承诺的最早 N 条。
        正序 mock 会掩盖此 bug（review 指出原测试 mock 恰好预排序）。
        """
        mock_service = MagicMock()
        mock_df = pd.DataFrame(
            {
                "code": ["000001.SZ"] * 5,
                # 倒序输入（最新在前）：修复前 head(2) 会错误返回 2025-01/2024-10
                "timestamp": ["2025-01-15", "2024-10-15", "2024-07-15", "2024-04-15", "2024-01-15"],
                "foreadjustfactor": [0.85, 0.88, 0.92, 0.95, 1.0],
                "backadjustfactor": [1.15, 1.12, 1.08, 1.05, 1.0],
                "adjustfactor": [1.15, 1.12, 1.08, 1.05, 1.0],
            }
        )
        mock_service.get_adjustfactors_df.return_value = ServiceResult.success(data=mock_df)
        mock_container.adjustfactor_service.return_value = mock_service

        result = cli_runner.invoke(
            data_cli.app, ["get", "adjustfactor", "--code", "000001.SZ", "--format", "text", "--limit", "2"]
        )
        assert result.exit_code == 0, f"exit≠0, output:\n{result.output}"
        # head：最早 2 条除权事件 (2024-01, 2024-04)
        assert "2024-01-15" in result.output
        assert "2024-04-15" in result.output
        assert "2024-10-15" not in result.output
        assert "2025-01-15" not in result.output

    def test_get_invalid_format_exits_with_code_2(self, cli_runner):
        """#6579 review finding 1：无效 --format 须 exit 2（BAD_PARAMS，ADR-021 第 6 维）。

        typer.Exit(2) 不能被 get 末尾的 ``except Exception`` 吞成 ``Exit(1)``
        （typer.Exit MRO = Exit→RuntimeError→Exception，是 Exception 子类）。
        校验在 service 调用前发生，无需 mock container。
        """
        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--format", "xml"])
        assert result.exit_code == 2, (
            f"expected exit 2 (BAD_PARAMS), got {result.exit_code}\noutput:\n{result.output}"
        )
        assert "Invalid --format" in result.output

    def test_get_invalid_limit_exits_with_code_2(self, cli_runner):
        """#6579 review finding 1：--limit < 1 须 exit 2（BAD_PARAMS），不被吞成 Exit(1)。"""
        result = cli_runner.invoke(data_cli.app, ["get", "stockinfo", "--limit", "0"])
        assert result.exit_code == 2, (
            f"expected exit 2 (BAD_PARAMS), got {result.exit_code}\noutput:\n{result.output}"
        )
        assert "--limit must be greater than 0" in result.output

    def test_get_sources_format_json(self, cli_runner):
        """--format json：sources 分支走 format_result list 契约（ADR-021 第 5/9 维）。

        sources 是静态列表（非 service/DF），json 分叉直接构造 records。
        不 mock（同 test_get_sources_lists_configured_sources）：容器注入了 tushare/tdx。
        """
        result = cli_runner.invoke(data_cli.app, ["get", "sources", "--format", "json"])
        assert result.exit_code == 0
        json_line = next(
            (l for l in result.output.splitlines() if l.strip().startswith('{"success"')),
            None,
        )
        assert json_line is not None, f"未找到 format_result JSON:\n{result.output}"
        payload = json.loads(json_line)
        assert payload["success"] is True
        assert isinstance(payload["data"], list)
        assert payload["count"] >= 2  # 至少 tushare + tdx
        names = [r["name"] for r in payload["data"]]
        assert "tushare" in names

    def test_get_sources_limit_ignored(self, cli_runner):
        """--limit 对 sources 不截断（ADR-021 任务2：资源列表本就少）。

        sources 是静态数据源列表（非查询结果），--limit 语义不适用。验证 --limit 1
        仍输出全部已配置数据源（tushare + tdx），不被截断。
        """
        result = cli_runner.invoke(data_cli.app, ["get", "sources", "--format", "text", "--limit", "1"])
        assert result.exit_code == 0, f"exit≠0, output:\n{result.output}"
        out = result.output.lower()
        # containers 注入 tushare + tdx，--limit 1 仍全量显示（不截断）
        assert "tushare" in out
        assert "tdx" in out

    def test_get_sources_format_auto_nontty(self, cli_runner):
        """--format 缺省 → auto/default 保持 text 输出（ADR-021 第 1 维）。

        JSON 必须显式传 ``--format json``，避免旧脚本在非 TTY 下突然收到 JSON。
        """
        result = cli_runner.invoke(data_cli.app, ["get", "sources"])
        assert result.exit_code == 0
        assert '{"success"' not in result.output
        assert "tushare" in result.output.lower()

    def test_get_no_color_wires_to_console(self, cli_runner):
        """--no-color → console.no_color=True（ADR-021 任务1：flag wiring）。

        Rich 非 TTY 本就无前景色输出，硬断言输出 ANSI 不可靠（Rich Table 在
        force_terminal 下只产 bold(1m)/italic(3m)，Segment.remove_color 本就不剥这两种）。
        改测契约：--no-color 真正抵达 console.no_color 属性。配对验证不带 flag 不误置。
        """
        from rich.console import Console

        # 带 --no-color：置位
        forced_on = Console(force_terminal=True, no_color=False)
        with patch("ginkgo.client.data_cli.console", forced_on):
            r = cli_runner.invoke(data_cli.app, ["get", "sources", "--no-color", "--format", "text"])
        assert r.exit_code == 0, f"exit≠0:\n{r.output}"
        assert forced_on.no_color is True, "--no-color 未置 console.no_color=True"

        # 不带 --no-color：保持默认（不误置）
        forced_off = Console(force_terminal=True, no_color=False)
        with patch("ginkgo.client.data_cli.console", forced_off):
            r2 = cli_runner.invoke(data_cli.app, ["get", "sources", "--format", "text"])
        assert r2.exit_code == 0
        assert not forced_off.no_color, "未传 --no-color 却误置 no_color"


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

        output_clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
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
        output_clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
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

        output_clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
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
