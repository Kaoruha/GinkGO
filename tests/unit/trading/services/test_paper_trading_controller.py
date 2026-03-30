# tests/unit/trading/services/test_paper_trading_controller.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestPaperTradingController:
    def test_run_daily_cycle_skips_non_trading_day(self):
        """非交易日不应推进引擎"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = []

        mock_engine = MagicMock()

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 29).date()
            result = controller.run_daily_cycle()

        assert result.skipped is True
        mock_engine.advance_time_to.assert_not_called()

    def test_run_daily_cycle_fetches_data_then_advances(self):
        """交易日应先拉取数据再推进引擎"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [MagicMock(is_open=True)]

        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        mock_sync_result.data.batch_details = {"successful_codes": 2, "failed_codes": 0, "failures": []}
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ", "600036.SH"]
        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}
        mock_engine.advance_time_to.return_value = True

        mock_next_day = MagicMock()
        mock_next_day.date.return_value = datetime(2026, 3, 31).date()
        mock_trade_day_crud.get_next_trading_day.return_value = mock_next_day

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
            bar_service=mock_bar_service,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 30).date()
            result = controller.run_daily_cycle()

        assert result.skipped is False
        assert result.advanced is True
        assert result.fetched_count == 2
        mock_bar_service.sync_range_batch.assert_called_once()
        mock_engine.advance_time_to.assert_called_once()

    def test_run_daily_cycle_skips_when_no_codes(self):
        """无关注股票时应跳过"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [MagicMock(is_open=True)]

        mock_engine = MagicMock()
        mock_engine.portfolios = {}

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 30).date()
            result = controller.run_daily_cycle()

        assert result.skipped is True
        assert "No interested codes" in result.error
        mock_engine.advance_time_to.assert_not_called()

    def test_run_daily_cycle_skips_when_sync_fails(self):
        """交易日但 sync 返回 0 成功时应跳过（拉取失败）"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [MagicMock(is_open=True)]

        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        mock_sync_result.data.batch_details = {"successful_codes": 0, "failed_codes": 1, "failures": [{"code": "000001.SZ", "error": "no data"}]}
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
            bar_service=mock_bar_service,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 30).date()
            result = controller.run_daily_cycle()

        assert result.skipped is True
        assert "No data fetched" in result.error
        mock_engine.advance_time_to.assert_not_called()

    def test_run_daily_cycle_uses_next_trading_day(self):
        """推进目标应为下一个交易日，而非 today+1"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [MagicMock(is_open=True)]
        # 周五(3/27)的下一交易日是周一(3/30)
        mock_next_day = MagicMock()
        mock_next_day.date.return_value = datetime(2026, 3, 30).date()
        mock_trade_day_crud.get_next_trading_day.return_value = mock_next_day

        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        mock_sync_result.data.batch_details = {"successful_codes": 1, "failed_codes": 0, "failures": []}
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}
        mock_engine.advance_time_to.return_value = True

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
            bar_service=mock_bar_service,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            # 模拟周五
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 27).date()
            # 保持 datetime.combine 和 datetime.min 正常工作
            mock_dt.combine = datetime.combine
            mock_dt.min = datetime.min
            result = controller.run_daily_cycle()

        # 应推进到周一而非周六
        call_args = mock_engine.advance_time_to.call_args[0][0]
        assert call_args.date() == datetime(2026, 3, 30).date()

    def test_get_interested_codes_from_selector(self):
        """应从引擎的 selector 获取关注股票列表"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ", "600036.SH"]

        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}

        mock_trade_day_crud = MagicMock()
        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
        )

        codes = controller.get_interested_codes()
        assert set(codes) == {"000001.SZ", "600036.SH"}

    def test_run_daily_cycle_warns_on_partial_sync_failure(self):
        """部分股票同步失败时应告警但仍推进引擎"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [MagicMock(is_open=True)]
        mock_next_day = MagicMock()
        mock_next_day.date.return_value = datetime(2026, 3, 31).date()
        mock_trade_day_crud.get_next_trading_day.return_value = mock_next_day

        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        # 5只中只有3只成功
        mock_sync_result.data.batch_details = {
            "successful_codes": 3,
            "failed_codes": 2,
            "failures": [{"code": "000002.SZ", "error": "timeout"}, {"code": "600036.SH", "error": "no data"}]
        }
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ", "000002.SZ", "600036.SH", "000003.SZ", "000004.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}
        mock_engine.advance_time_to.return_value = True

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
            bar_service=mock_bar_service,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 30).date()
            result = controller.run_daily_cycle()

        # 部分成功不应 skip，仍应推进
        assert result.skipped is False
        assert result.advanced is True
        assert result.fetched_count == 3
        # 应包含失败信息
        assert "000002.SZ" in result.warning or "600036.SH" in result.warning
