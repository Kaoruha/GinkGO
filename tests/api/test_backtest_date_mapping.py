# #5577 #5443 — engine_config 日期映射到 task 级别字段
"""
验证 API 创建回测时 engine_config.start_date/end_date 映射到
backtest_start_date/backtest_end_date 任务字段。
"""
import pytest
from unittest.mock import patch, MagicMock


class TestBuildBacktestConfigIncludesDates:
    """build_backtest_config 应正确包含日期"""

    def test_config_contains_start_and_end_dates(self):
        from api.backtest import build_backtest_config, BacktestTaskCreate, EngineConfig

        data = BacktestTaskCreate(
            name="test",
            portfolio_uuids=["p-uuid-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )
        config = build_backtest_config(data)
        assert config["start_date"] == "2025-06-01"
        assert config["end_date"] == "2025-12-31"


class TestCreateBacktestTaskPassesDateFields:
    """create_backtest_task 应把 engine_config 日期传给 task_service.create()"""

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_create_passes_backtest_start_date_to_service(
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

        create_backtest_task(data)

        call_kwargs = mock_service.create.call_args.kwargs
        assert "backtest_start_date" in call_kwargs, \
            f"create() 未收到 backtest_start_date, 实际参数: {list(call_kwargs.keys())}"
        assert call_kwargs["backtest_start_date"] == "2025-06-01"

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_create_passes_backtest_end_date_to_service(
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

        create_backtest_task(data)

        call_kwargs = mock_service.create.call_args.kwargs
        assert "backtest_end_date" in call_kwargs, \
            f"create() 未收到 backtest_end_date, 实际参数: {list(call_kwargs.keys())}"
        assert call_kwargs["backtest_end_date"] == "2025-12-31"


class TestCRUDDatetimeConversion:
    """CRUD 层应正确将字符串日期转为 datetime"""

    def test_backtest_task_crud_parses_string_dates(self):
        from ginkgo.data.crud.backtest_task_crud import BacktestTaskCRUD
        from ginkgo.libs import datetime_normalize

        crud = BacktestTaskCRUD()
        # datetime_normalize 应能处理 "YYYY-MM-DD" 格式
        result = datetime_normalize("2025-06-01")
        assert result is not None
        assert result.year == 2025
        assert result.month == 6
        assert result.day == 1
