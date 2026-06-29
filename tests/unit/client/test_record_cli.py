"""
record CLI 单元测试。

覆盖 record signal/order/position 命令：
- #4743: order/position 的 engine/task 过滤透传（与 signal 对称）
- #5949: signal 的 portfolio/engine/task 可选过滤 + 拆分强制阶段

Run: pytest tests/unit/client/test_record_cli.py -v -o "addopts="
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from typer.testing import CliRunner

from ginkgo.client import record_cli
from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_orders_df():
    return pd.DataFrame({
        "uuid": ["o1"],
        "portfolio_id": ["p1"],
        "engine_id": ["e1"],
        "task_id": ["t1"],
        "code": ["000001.SZ"],
        "direction": ["LONG"],
        "order_type": ["MARKET"],
        "quantity": [100],
        "limit_price": [10.5],
        "timestamp": ["2026-01-01"],
        "status": ["FILLED"],
    })


@pytest.fixture
def mock_positions_df():
    # #5341: record position 读流水表 MPositionRecord，字段是 volume/cost/price/fee
    # （非 MPosition 当前态的 quantity/average_price/market_value）
    return pd.DataFrame({
        "uuid": ["pos1"],
        "portfolio_id": ["p1"],
        "engine_id": ["e1"],
        "task_id": ["t1"],
        "code": ["000001.SZ"],
        "volume": [100],
        "cost": [10.5],
        "price": [10.8],
        "fee": [5.0],
        "timestamp": ["2026-01-01"],
    })


# ============================================================================
# #4743: order / position 加 -e/-t 过滤（与 signal 对称）
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestRecordOrderFilters:
    """record order 的 engine/task 过滤透传（#4743）"""

    @patch("ginkgo.data.containers.Container")
    def test_order_passes_engine_and_task(self, mock_container, cli_runner, mock_orders_df):
        """-e/-t 透传到 service.get_orders_df"""
        mock_service = MagicMock()
        mock_service.get_orders_df.return_value = ServiceResult.success(data=mock_orders_df)
        mock_container.order_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, [
            "order", "--portfolio", "p1", "--engine", "e1", "--task", "t1",
        ])
        assert result.exit_code == 0
        _, kwargs = mock_service.get_orders_df.call_args
        assert kwargs.get("portfolio_id") == "p1"
        assert kwargs.get("engine_id") == "e1"
        assert kwargs.get("task_id") == "t1"

    @patch("ginkgo.data.containers.Container")
    def test_order_without_filters_still_works(self, mock_container, cli_runner, mock_orders_df):
        """无过滤参数时正常返回全部（不传 None 进 service）"""
        mock_service = MagicMock()
        mock_service.get_orders_df.return_value = ServiceResult.success(data=mock_orders_df)
        mock_container.order_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, ["order"])
        assert result.exit_code == 0
        mock_service.get_orders_df.assert_called_once()


@pytest.mark.unit
@pytest.mark.cli
class TestRecordPositionFilters:
    """record position 的 engine/task 过滤透传（#4743）+ 读流水表（#5341）

    #5341 根因：回测持仓写 MPositionRecord（流水），record position 原读
    PositionService（MPosition 当前态）永远空。改读 ResultService.get_positions_df
    （查 PositionRecordCRUD）。
    """

    @patch("ginkgo.data.containers.Container")
    def test_position_passes_engine_and_task(self, mock_container, cli_runner, mock_positions_df):
        """-e/-t 透传到 result_service.get_positions_df"""
        mock_service = MagicMock()
        mock_service.get_positions_df.return_value = ServiceResult.success(data=mock_positions_df)
        mock_container.result_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, [
            "position", "--portfolio", "p1", "--engine", "e1", "--task", "t1",
        ])
        assert result.exit_code == 0
        _, kwargs = mock_service.get_positions_df.call_args
        assert kwargs.get("portfolio_id") == "p1"
        assert kwargs.get("engine_id") == "e1"
        assert kwargs.get("task_id") == "t1"

    @patch("ginkgo.data.containers.Container")
    def test_position_reads_result_service_not_position_service(
        self, mock_container, cli_runner, mock_positions_df
    ):
        """#5341 核心：必须读 result_service（流水表），不得读 position_service（当前态）"""
        mock_result_svc = MagicMock()
        mock_result_svc.get_positions_df.return_value = ServiceResult.success(data=mock_positions_df)
        mock_container.result_service.return_value = mock_result_svc
        mock_position_svc = MagicMock()
        mock_container.position_service.return_value = mock_position_svc

        result = cli_runner.invoke(record_cli.app, [
            "position", "--portfolio", "p1", "--engine", "e1", "--task", "t1",
        ])
        assert result.exit_code == 0
        mock_result_svc.get_positions_df.assert_called_once()
        # 关键：position_service（当前态表）绝不能被调用——那是 #5341 的 bug 源头
        mock_position_svc.get_positions_df.assert_not_called()


# ============================================================================
# #5949: signal 可选过滤（-p/-e/-t）+ 拆分强制阶段
# ============================================================================


def _signals_df():
    return pd.DataFrame({
        "uuid": ["s1"],
        "engine_id": ["e1"],
        "portfolio_id": ["p1"],
        "task_id": ["t1"],
        "code": ["000001.SZ"],
        "direction": ["LONG"],
        "timestamp": ["2026-01-01"],
        "reason": ["test"],
    })


@pytest.mark.unit
@pytest.mark.cli
class TestRecordSignalFilters:
    """record signal 的可选过滤 + 拆分强制阶段（#5949）

    原实现强制三阶段（无 engine→列 engines；有 engine 无 portfolio→列 portfolios；
    都有→查 signals）。统一后 -p/-e/-t 全可选，与 order/position 一致。
    """

    @patch("ginkgo.data.containers.Container")
    def test_signal_passes_all_filters(self, mock_container, cli_runner):
        """-p/-e/-t 全透传到 service.get_signals_df"""
        mock_service = MagicMock()
        mock_service.get_signals_df.return_value = ServiceResult.success(data=_signals_df())
        mock_container.signal_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, [
            "signal", "--portfolio", "p1", "--engine", "e1", "--task", "t1",
        ])
        assert result.exit_code == 0
        _, kwargs = mock_service.get_signals_df.call_args
        assert kwargs.get("portfolio_id") == "p1"
        assert kwargs.get("engine_id") == "e1"
        assert kwargs.get("task_id") == "t1"

    @patch("ginkgo.data.containers.Container")
    def test_signal_portfolio_only_queries_directly(self, mock_container, cli_runner):
        """单 -p 直接查该 portfolio 全部 signal，不再强制先选 engine"""
        mock_service = MagicMock()
        mock_service.get_signals_df.return_value = ServiceResult.success(data=_signals_df())
        mock_container.signal_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, ["signal", "--portfolio", "p1"])
        assert result.exit_code == 0
        # 核心：直接走 signal 查询，不触发 engine 选择阶段
        mock_container.signal_service.assert_called_once()
        _, kwargs = mock_service.get_signals_df.call_args
        assert kwargs.get("portfolio_id") == "p1"

    @patch("ginkgo.data.containers.Container")
    def test_signal_no_filters_returns_all(self, mock_container, cli_runner):
        """无任何过滤参数时查全部 signal（不再强制选 engine）"""
        mock_service = MagicMock()
        mock_service.get_signals_df.return_value = ServiceResult.success(data=_signals_df())
        mock_container.signal_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, ["signal"])
        assert result.exit_code == 0
        mock_service.get_signals_df.assert_called_once()
