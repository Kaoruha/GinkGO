# #5581 — BacktestTaskCreate 顶层 start_date/end_date 可选字段
"""
验证 BacktestTaskCreate schema 接受可选顶层 start_date/end_date，
并在创建任务时顶层优先、engine_config 回退。

与 test_backtest_date_mapping.py (#5577 engine_config→task 映射) 互补：
#5577 保证 engine_config 日期能落到 task 字段；#5581 在此之上加顶层显式入口。
"""
import pytest
from unittest.mock import patch, MagicMock


class TestBacktestTaskCreateToplevelDates:
    """#5581: schema 接受可选顶层 start_date/end_date 字段"""

    def test_schema_accepts_toplevel_start_and_end_dates(self):
        """顶层 start_date/end_date 应被接受为可选字段。

        RED: 当前 BacktestTaskCreate 无 start_date/end_date 字段 →
        pydantic ignore extra，data.start_date 抛 AttributeError。
        """
        from api.backtest import BacktestTaskCreate, EngineConfig

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        assert data.start_date == "2024-01-01"
        assert data.end_date == "2024-12-31"

    def test_toplevel_dates_default_to_none_when_omitted(self):
        """未传顶层日期时为 None（向后兼容，不破坏现有 engine_config 路径）。"""
        from api.backtest import BacktestTaskCreate, EngineConfig

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
        )
        assert data.start_date is None
        assert data.end_date is None


class TestCreateBacktestTaskToplevelDatePriority:
    """#5581: 顶层日期优先于 engine_config，未传时回退 engine_config。"""

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_toplevel_start_date_overrides_engine_config(self, mock_get_service, mock_portfolio):
        """顶层 start_date 提供时，backtest_start_date 用顶层值而非 engine_config。"""
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
                start_date="2025-06-01",  # engine_config 值
                end_date="2025-12-31",
            ),
            start_date="2024-01-01",  # 顶层值（应优先）
            end_date="2024-12-31",
        )

        create_backtest_task(data)

        call_kwargs = mock_service.create.call_args.kwargs
        assert call_kwargs["backtest_start_date"] == "2024-01-01", \
            "顶层 start_date 应优先于 engine_config"
        assert call_kwargs["backtest_end_date"] == "2024-12-31"

    @patch("api.backtest.get_portfolio_info")
    @patch("api.backtest.get_backtest_task_service")
    def test_falls_back_to_engine_config_when_no_toplevel(self, mock_get_service, mock_portfolio):
        """顶层日期未传时，回退到 engine_config（保留 #5577 行为）。"""
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
            # 不传顶层 start_date/end_date
        )

        create_backtest_task(data)

        call_kwargs = mock_service.create.call_args.kwargs
        assert call_kwargs["backtest_start_date"] == "2025-06-01"
        assert call_kwargs["backtest_end_date"] == "2025-12-31"


class TestBuildBacktestConfigEffectiveDates:
    """#5581: config_snapshot 应反映有效日期（顶层优先），保证回放一致。"""

    def test_config_uses_toplevel_dates_when_provided(self):
        """顶层日期提供时，config.start_date/end_date 也用顶层值。"""
        from api.backtest import build_backtest_config, BacktestTaskCreate, EngineConfig

        data = BacktestTaskCreate(
            name="test_bt",
            portfolio_uuids=["p-1"],
            engine_config=EngineConfig(
                start_date="2025-06-01",
                end_date="2025-12-31",
            ),
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        config = build_backtest_config(data)
        assert config["start_date"] == "2024-01-01", \
            "config_snapshot 应反映顶层日期（回测引擎据此跑数据，须与 task 字段一致）"
        assert config["end_date"] == "2024-12-31"

