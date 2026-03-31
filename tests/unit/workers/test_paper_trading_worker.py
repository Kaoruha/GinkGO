"""
PaperTradingWorker 单元测试

测试覆盖：
1. 构造和初始化
2. 引擎组装
3. 每日循环逻辑（交易日/非交易日/数据同步）
4. Kafka 命令处理（paper_trading / deploy / unload）
5. interested codes 收集
6. 边界情况和错误处理
"""
import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from datetime import datetime
from unittest.mock import MagicMock, patch, call
import pytest


class TestConstruction:
    """构造和初始化测试"""

    def test_default_state(self):
        """Worker 默认状态：未运行，无引擎，无 portfolios"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        assert worker.worker_id == "test-1"
        assert worker.is_running is False
        assert worker._engine is None
        assert worker._consumer is None

    def test_requires_worker_id(self):
        """必须提供 worker_id"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="w-001")
        assert worker.worker_id == "w-001"


class TestAssembleEngine:
    """引擎组装测试"""

    @patch("ginkgo.trading.services._assembly.component_loader.ComponentLoader")
    @patch("ginkgo.trading.feeders.backtest_feeder.BacktestFeeder")
    @patch("ginkgo.trading.gateway.trade_gateway.TradeGateway")
    @patch("ginkgo.trading.brokers.sim_broker.SimBroker")
    @patch("ginkgo.trading.engines.time_controlled_engine.TimeControlledEventEngine")
    @patch("ginkgo.trading.portfolios.t1backtest.PortfolioT1Backtest")
    def test_creates_engine_with_paper_mode(self, mock_portfolio, mock_engine,
                                            mock_broker, mock_gateway,
                                            mock_feeder, mock_loader):
        """assemble_engine 应创建 PAPER 模式的引擎"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        from ginkgo.enums import EXECUTION_MODE, PORTFOLIO_MODE_TYPES

        # Mock DB 返回一个 PAPER portfolio
        mock_db_portfolio = MagicMock()
        mock_db_portfolio.uuid = "p-001"
        mock_db_portfolio.code = "test-paper"
        mock_db_portfolio.mode = PORTFOLIO_MODE_TYPES.PAPER.value

        mock_container = MagicMock()
        mock_crud = MagicMock()
        mock_crud.find.return_value = [mock_db_portfolio]
        mock_container.cruds.portfolio.return_value = mock_crud

        mock_components = {
            "strategies": [], "risk_managers": [],
            "analyzers": [], "selectors": [], "sizers": [],
        }

        mock_engine_instance = MagicMock()
        mock_engine_instance.portfolios = []
        mock_engine.return_value = mock_engine_instance

        worker = PaperTradingWorker(worker_id="test-1")
        with patch("ginkgo.client.portfolio_cli.collect_portfolio_components",
                   return_value=mock_components):
            worker.assemble_engine(mock_container)

        mock_engine.assert_called_once()
        call_kwargs = mock_engine.call_args
        assert call_kwargs.kwargs.get("mode") == EXECUTION_MODE.PAPER or \
               call_kwargs[1].get("mode") == EXECUTION_MODE.PAPER

    @patch("ginkgo.trading.services._assembly.component_loader.ComponentLoader")
    @patch("ginkgo.trading.feeders.backtest_feeder.BacktestFeeder")
    @patch("ginkgo.trading.gateway.trade_gateway.TradeGateway")
    @patch("ginkgo.trading.brokers.sim_broker.SimBroker")
    @patch("ginkgo.trading.engines.time_controlled_engine.TimeControlledEventEngine")
    @patch("ginkgo.trading.portfolios.t1backtest.PortfolioT1Backtest")
    def test_loads_papers_portfolios_from_db(self, mock_portfolio_cls,
                                              mock_engine_cls,
                                              mock_broker, mock_gateway,
                                              mock_feeder, mock_loader):
        """assemble_engine 应从 DB 加载所有 PAPER 模式的 Portfolio"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        # Mock DB portfolio
        mock_db_portfolio = MagicMock()
        mock_db_portfolio.uuid = "p-001"
        mock_db_portfolio.code = "paper-portfolio"
        mock_db_portfolio.mode = PORTFOLIO_MODE_TYPES.PAPER.value
        mock_db_portfolio.initial_cash = 100000.0

        mock_crud = MagicMock()
        mock_crud.find.return_value = [mock_db_portfolio]

        mock_container = MagicMock()
        mock_container.cruds.portfolio.return_value = mock_crud

        # Mock collect_portfolio_components
        mock_components = {
            "strategies": [],
            "risk_managers": [],
            "analyzers": [],
            "selectors": [],
            "sizers": [],
        }

        mock_portfolio_instance = MagicMock()
        mock_portfolio_instance.uuid = "p-001"
        mock_portfolio_cls.return_value = mock_portfolio_instance

        mock_engine_instance = MagicMock()
        mock_engine_instance.portfolios = []
        mock_engine_cls.return_value = mock_engine_instance

        worker = PaperTradingWorker(worker_id="test-1")
        with patch("ginkgo.client.portfolio_cli.collect_portfolio_components",
                   return_value=mock_components):
            worker.assemble_engine(mock_container)

        # Engine 应已创建
        assert worker._engine is not None
        # Portfolio 应已添加到引擎
        mock_engine_instance.add_portfolio.assert_called_once()


class TestDailyCycle:
    """每日循环逻辑测试"""

    def _make_worker_with_engine(self):
        """辅助方法：创建带 mock 引擎的 worker"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = MagicMock()
        worker._engine.portfolios = []
        worker._engine.is_running = True
        return worker

    def test_skip_on_non_trading_day(self):
        """非交易日应跳过推进"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = self._make_worker_with_engine()
        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = []  # 没有交易日记录

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.cruds.trade_day.return_value = mock_trade_day_crud
            result = worker.run_daily_cycle()

        assert result.skipped is True
        assert result.advanced is False
        worker._engine.advance_time_to.assert_not_called()

    def test_advance_on_trading_day(self):
        """交易日应推进引擎"""
        worker = self._make_worker_with_engine()

        # Mock portfolio with selector._interested
        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio._selectors = [mock_selector]
        worker._engine.portfolios = [mock_portfolio]

        # Mock 交易日检查：返回 is_open=True
        mock_trade_day_record = MagicMock()
        mock_trade_day_record.is_open = True
        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [mock_trade_day_record]

        # Mock get_next_trading_day
        next_day = datetime(2026, 3, 31)
        mock_trade_day_crud.get_next_trading_day.return_value = next_day

        # Mock bar_service.sync_range_batch
        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.data = {"successful_codes": 1, "failed_codes": 0, "failures": []}
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.cruds.trade_day.return_value = mock_trade_day_crud
            mock_services.data.services.bar_service.return_value = mock_bar_service
            result = worker.run_daily_cycle()

        assert result.skipped is False
        assert result.advanced is True
        worker._engine.advance_time_to.assert_called_once_with(next_day)

    def test_sync_calls_bar_service_with_correct_codes(self):
        """sync 应调用 bar_service.sync_range_batch 并传入正确的 codes"""
        worker = self._make_worker_with_engine()

        # Mock portfolio with selector._interested
        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ", "600036.SH"]
        mock_portfolio = MagicMock()
        mock_portfolio._selectors = [mock_selector]
        worker._engine.portfolios = [mock_portfolio]

        # Mock 交易日
        mock_trade_day_record = MagicMock()
        mock_trade_day_record.is_open = True
        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [mock_trade_day_record]
        mock_trade_day_crud.get_next_trading_day.return_value = datetime(2026, 3, 31)

        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.data = {"successful_codes": 2, "failed_codes": 0, "failures": []}
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.cruds.trade_day.return_value = mock_trade_day_crud
            mock_services.data.services.bar_service.return_value = mock_bar_service
            worker.run_daily_cycle()

        # 验证 sync_range_batch 被调用，且 codes 包含两个股票
        mock_bar_service.sync_range_batch.assert_called_once()
        call_args = mock_bar_service.sync_range_batch.call_args
        codes = call_args[0][0] if call_args[0] else call_args[1].get("codes")
        assert "000001.SZ" in codes
        assert "600036.SH" in codes

    def test_empty_portfolios_skips_advance(self):
        """没有 portfolio 时不推进引擎"""
        worker = self._make_worker_with_engine()
        worker._engine.portfolios = []  # 空

        # Mock 交易日
        mock_trade_day_record = MagicMock()
        mock_trade_day_record.is_open = True
        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [mock_trade_day_record]
        mock_trade_day_crud.get_next_trading_day.return_value = datetime(2026, 3, 31)

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.cruds.trade_day.return_value = mock_trade_day_crud
            result = worker.run_daily_cycle()

        assert result.skipped is True
        worker._engine.advance_time_to.assert_not_called()

    def test_sync_failure_still_advances(self):
        """数据同步失败仍应推进引擎"""
        worker = self._make_worker_with_engine()

        # Mock portfolio with selector
        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio._selectors = [mock_selector]
        worker._engine.portfolios = [mock_portfolio]

        # Mock 交易日
        mock_trade_day_record = MagicMock()
        mock_trade_day_record.is_open = True
        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = [mock_trade_day_record]
        mock_trade_day_crud.get_next_trading_day.return_value = datetime(2026, 3, 31)

        # Mock sync 失败
        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.data = {"successful_codes": 0, "failed_codes": 1,
                                  "failures": [{"code": "000001.SZ", "error": "timeout"}]}
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.cruds.trade_day.return_value = mock_trade_day_crud
            mock_services.data.services.bar_service.return_value = mock_bar_service
            result = worker.run_daily_cycle()

        assert result.advanced is True
        worker._engine.advance_time_to.assert_called_once()


class TestCommandHandling:
    """Kafka 命令处理测试"""

    def test_paper_trading_command(self):
        """paper_trading 命令应调用 run_daily_cycle"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = MagicMock()
        worker._engine.portfolios = []

        with patch.object(worker, "run_daily_cycle") as mock_cycle:
            mock_cycle.return_value = MagicMock(skipped=False, advanced=True)
            worker._handle_command("paper_trading", {})

        mock_cycle.assert_called_once()

    def test_deploy_command(self):
        """deploy 命令应调用 _handle_deploy"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")

        with patch.object(worker, "_handle_deploy", return_value=True) as mock_deploy:
            worker._handle_command("deploy", {"portfolio_id": "p-001"})

        mock_deploy.assert_called_once_with({"portfolio_id": "p-001"})

    def test_unload_command(self):
        """unload 命令应调用 _handle_unload"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")

        with patch.object(worker, "_handle_unload", return_value=True) as mock_unload:
            worker._handle_command("unload", {"portfolio_id": "p-001"})

        mock_unload.assert_called_once_with({"portfolio_id": "p-001"})

    def test_unknown_command_returns_false(self):
        """未知命令应返回 False"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        result = worker._handle_command("unknown_cmd", {})
        assert result is False


class TestDeploy:
    """deploy 命令处理测试"""

    @patch("ginkgo.trading.services._assembly.component_loader.ComponentLoader")
    @patch("ginkgo.trading.portfolios.t1backtest.PortfolioT1Backtest")
    def test_deploy_adds_portfolio_to_engine(self, mock_portfolio_cls, mock_loader):
        """deploy 应创建 Portfolio 并添加到引擎"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_engine = MagicMock()
        mock_engine.portfolios = []
        worker._engine = mock_engine

        mock_portfolio_instance = MagicMock()
        mock_portfolio_instance.uuid = "p-new-001"
        mock_portfolio_cls.return_value = mock_portfolio_instance

        mock_components = {
            "strategies": [], "risk_managers": [],
            "analyzers": [], "selectors": [], "sizers": [],
        }

        # Mock services for the _handle_deploy's internal import
        mock_container = MagicMock()
        mock_crud = MagicMock()
        mock_db_portfolio = MagicMock()
        mock_db_portfolio.uuid = "p-new-001"
        mock_db_portfolio.code = "test-portfolio"
        mock_crud.find.return_value = [mock_db_portfolio]
        mock_container.cruds.portfolio.return_value = mock_crud

        with patch("ginkgo.client.portfolio_cli.collect_portfolio_components",
                   return_value=mock_components):
            with patch("ginkgo.services", create=True) as mock_services:
                mock_services.data.container = mock_container
                result = worker._handle_deploy({"portfolio_id": "p-new-001"})

        assert result is True
        mock_engine.add_portfolio.assert_called_once_with(mock_portfolio_instance)

    def test_deploy_without_engine_returns_false(self):
        """引擎未初始化时 deploy 应返回 False"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = None
        result = worker._handle_deploy({"portfolio_id": "p-001"})
        assert result is False


class TestUnload:
    """unload 命令处理测试"""

    def test_unload_removes_portfolio_from_engine(self):
        """unload 应从引擎中移除指定 Portfolio"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "p-001"

        mock_engine = MagicMock()
        mock_engine.portfolios = [mock_portfolio]

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = mock_engine

        result = worker._handle_unload({"portfolio_id": "p-001"})

        assert result is True
        mock_engine.remove_portfolio.assert_called_once_with(mock_portfolio)

    def test_unload_nonexistent_portfolio(self):
        """unload 不存在的 portfolio 应返回 False"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        mock_engine = MagicMock()
        mock_engine.portfolios = []

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = mock_engine

        result = worker._handle_unload({"portfolio_id": "p-nonexistent"})
        assert result is False

    def test_unload_without_engine_returns_false(self):
        """引擎未初始化时 unload 应返回 False"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = None
        result = worker._handle_unload({"portfolio_id": "p-001"})
        assert result is False


class TestGetInterestedCodes:
    """interested codes 收集测试"""

    def test_collects_from_all_portfolios_selectors(self):
        """应从所有 portfolio 的 selector._interested 收集 codes"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_engine = MagicMock()

        # 两个 portfolio，各有 selector
        mock_selector1 = MagicMock()
        mock_selector1._interested = ["000001.SZ", "000002.SZ"]
        mock_portfolio1 = MagicMock()
        mock_portfolio1._selectors = [mock_selector1]

        mock_selector2 = MagicMock()
        mock_selector2._interested = ["600036.SH"]
        mock_portfolio2 = MagicMock()
        mock_portfolio2._selectors = [mock_selector2]

        mock_engine.portfolios = [mock_portfolio1, mock_portfolio2]
        worker._engine = mock_engine

        codes = worker._get_interested_codes()
        assert "000001.SZ" in codes
        assert "000002.SZ" in codes
        assert "600036.SH" in codes

    def test_deduplicates_codes(self):
        """应去重 codes"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_engine = MagicMock()

        mock_selector1 = MagicMock()
        mock_selector1._interested = ["000001.SZ"]
        mock_portfolio1 = MagicMock()
        mock_portfolio1._selectors = [mock_selector1]

        mock_selector2 = MagicMock()
        mock_selector2._interested = ["000001.SZ"]  # 重复
        mock_portfolio2 = MagicMock()
        mock_portfolio2._selectors = [mock_selector2]

        mock_engine.portfolios = [mock_portfolio1, mock_portfolio2]
        worker._engine = mock_engine

        codes = worker._get_interested_codes()
        assert codes.count("000001.SZ") == 1

    def test_empty_portfolios_returns_empty(self):
        """没有 portfolio 时返回空列表"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_engine = MagicMock()
        mock_engine.portfolios = []
        worker._engine = mock_engine

        codes = worker._get_interested_codes()
        assert codes == []


class TestStartStop:
    """启动/停止测试"""

    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoConsumer")
    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer")
    def test_start_sets_running_true(self, mock_producer_cls, mock_consumer_cls):
        """start 应设置 is_running=True"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker.start()
        assert worker.is_running is True

    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoConsumer")
    @patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer")
    def test_stop_sets_running_false(self, mock_producer_cls, mock_consumer_cls):
        """stop 应设置 is_running=False"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._running = True
        worker.stop()
        assert worker.is_running is False


class TestDailyCycleResult:
    """DailyCycleResult 数据类测试"""

    def test_result_attributes(self):
        """DailyCycleResult 应包含 skipped 和 advanced 属性"""
        from ginkgo.workers.paper_trading_worker import DailyCycleResult

        result = DailyCycleResult(skipped=True, advanced=False)
        assert result.skipped is True
        assert result.advanced is False

    def test_result_default_values(self):
        """DailyCycleResult 默认值应为 False"""
        from ginkgo.workers.paper_trading_worker import DailyCycleResult

        result = DailyCycleResult()
        assert result.skipped is False
        assert result.advanced is False
