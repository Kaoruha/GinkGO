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
    return pd.DataFrame({
        "uuid": ["pos1"],
        "portfolio_id": ["p1"],
        "engine_id": ["e1"],
        "task_id": ["t1"],
        "code": ["000001.SZ"],
        "quantity": [100],
        "average_price": [10.5],
        "market_value": [1050.0],
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
    """record position 的 engine/task 过滤透传（#4743）"""

    @patch("ginkgo.data.containers.Container")
    def test_position_passes_engine_and_task(self, mock_container, cli_runner, mock_positions_df):
        """-e/-t 透传到 service.get_positions_df"""
        mock_service = MagicMock()
        mock_service.get_positions_df.return_value = ServiceResult.success(data=mock_positions_df)
        mock_container.position_service.return_value = mock_service

        result = cli_runner.invoke(record_cli.app, [
            "position", "--portfolio", "p1", "--engine", "e1", "--task", "t1",
        ])
        assert result.exit_code == 0
        _, kwargs = mock_service.get_positions_df.call_args
        assert kwargs.get("portfolio_id") == "p1"
        assert kwargs.get("engine_id") == "e1"
        assert kwargs.get("task_id") == "t1"
