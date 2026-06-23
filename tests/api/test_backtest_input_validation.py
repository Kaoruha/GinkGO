# #5462 — backtest 创建应在建任务前校验 portfolio 存在 + 日期顺序
"""
验证 create_backtest_task 的输入校验：
1. 无效 portfolio UUID → 抛 NotFoundError，不建任务（而非吞错回填 "Unknown Portfolio"）
2. start_date > end_date → 抛 ValidationError，不建任务
3. 正常输入仍建任务（回归保护）
"""
import pytest
from unittest.mock import patch, MagicMock

from core.exceptions import NotFoundError, ValidationError


class TestCreateBacktestTaskRejectsInvalidPortfolio:
    """无效 portfolio UUID 应在建任务前抛 NotFoundError，不调用 service.create"""

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_invalid_portfolio_raises_not_found_and_no_task_created(
        self, mock_get_service, mock_portfolio
    ):
        from api.backtest import create_backtest_task, BacktestTaskCreate, EngineConfig

        mock_portfolio.side_effect = NotFoundError("Portfolio", "nonexistent-uuid")
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["nonexistent-uuid"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )

        with pytest.raises(NotFoundError):
            create_backtest_task(data)

        # 关键：不应创建任务
        mock_service.create.assert_not_called()


class TestCreateBacktestTaskRejectsReversedDates:
    """start_date > end_date 应在建任务前抛 ValidationError，不调用 service.create"""

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_reversed_dates_raises_validation_error_and_no_task_created(
        self, mock_get_service, mock_portfolio
    ):
        from api.backtest import create_backtest_task, BacktestTaskCreate, EngineConfig

        # 即使 portfolio 存在，日期倒序也应在建任务前被拒
        mock_portfolio.return_value = {"uuid": "p-1", "name": "Portfolio1"}
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-12-31",
                end_date="2025-06-01",
            ),
        )

        with pytest.raises(ValidationError):
            create_backtest_task(data)

        mock_service.create.assert_not_called()


class TestCreateBacktestTaskAcceptsValidInput:
    """正常输入仍应建任务（回归保护）"""

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_valid_input_creates_task(
        self, mock_get_service, mock_portfolio
    ):
        from api.backtest import create_backtest_task, BacktestTaskCreate, EngineConfig

        mock_portfolio.return_value = {"uuid": "p-1", "name": "Portfolio1"}
        mock_task = MagicMock()
        mock_task.uuid = "task-uuid"
        mock_task.created_at = "2025-01-01T00:00:00Z"
        mock_result = MagicMock()
        mock_result.is_success.return_value = True
        mock_result.data = mock_task
        mock_service = MagicMock()
        mock_service.create.return_value = mock_result
        mock_get_service.return_value = mock_service

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )

        result = create_backtest_task(data)

        mock_service.create.assert_called_once()
        assert result["uuid"] == "task-uuid"
