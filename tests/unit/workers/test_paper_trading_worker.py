"""
性能: 319MB RSS, 1.41s, 43 tests [FAIL(4)]
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

        # mock consumer.poll 返回空 dict，让 _consume_loop 的 while 循环
        # 在下一次迭代前通过 stop() 退出
        mock_consumer = MagicMock()
        mock_consumer.consumer.poll.return_value = {}
        mock_consumer_cls.return_value = mock_consumer

        worker = PaperTradingWorker(worker_id="test-1")
        # 在另一个线程中 start，主线程短暂等待后 stop
        import threading
        t = threading.Thread(target=worker.start)
        t.start()
        import time
        time.sleep(0.1)
        assert worker.is_running is True
        worker.stop()
        t.join(timeout=2)

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


class TestGetBaseline:
    """_get_baseline 测试"""

    def _make_worker(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        return PaperTradingWorker(worker_id="test-1")

    def test_returns_cached_baseline_from_redis(self):
        """Redis 有缓存时应直接返回，不查 ClickHouse"""
        worker = self._make_worker()
        cached_baseline = {"slice_period_days": 30, "baseline_stats": {"sharpe_ratio": {"mean": 1.5}}}

        mock_redis = MagicMock()
        mock_redis.get.return_value = '{"slice_period_days": 30}'

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            result = worker._get_baseline("p-001")

        assert result == {"slice_period_days": 30}

    def test_computes_baseline_on_redis_miss(self):
        """Redis 无缓存时应从 ClickHouse 计算"""
        worker = self._make_worker()

        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: None  # 所有 key 都 miss

        # Mock source mapping
        mock_redis.get.side_effect = lambda key: "source_uuid" if "source" in key else None

        # Mock backtest task
        mock_task = MagicMock()
        mock_task.run_id = "task-001"
        mock_task.engine_id = "engine-001"
        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = MagicMock(
            is_success=True,
            data=[mock_task],
        )

        # Mock evaluator
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate_backtest_stability.return_value = {
            "status": "success",
            "monitoring_baseline": {"slice_period_days": 14, "baseline_stats": {}},
        }

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            mock_services.data.backtest_task_service.return_value = mock_task_svc
            with patch("ginkgo.trading.analysis.evaluation.backtest_evaluator.BacktestEvaluator",
                       return_value=mock_evaluator):
                result = worker._get_baseline("p-001")

        assert result is not None
        assert result["slice_period_days"] == 14

    def test_returns_none_when_no_source_mapping(self):
        """无 source 映射时应返回 None"""
        worker = self._make_worker()

        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            result = worker._get_baseline("p-001")

        assert result is None

    def test_returns_none_when_no_completed_backtest(self):
        """无已完成回测时应返回 None"""
        worker = self._make_worker()

        mock_redis = MagicMock()
        mock_redis.get.side_effect = lambda key: "source_uuid" if "source" in key else None

        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = MagicMock(is_success=True, data=[])

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            mock_services.data.backtest_task_service.return_value = mock_task_svc
            result = worker._get_baseline("p-001")

        assert result is None


class TestGetDeviationConfig:
    """_get_deviation_config 测试"""

    def test_returns_default_config_when_no_redis(self):
        """Redis 无配置时应返回默认值"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")

        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            config = worker._get_deviation_config("p-001")

        assert config["auto_takedown"] is False
        assert config["slice_period_days"] is None
        assert config["alert_channels"] == ["kafka"]

    def test_returns_config_from_redis(self):
        """Redis 有配置时应返回存储的配置"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")

        mock_redis = MagicMock()
        mock_redis.get.return_value = '{"auto_takedown": true, "slice_period_days": 14}'

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            config = worker._get_deviation_config("p-001")

        assert config["auto_takedown"] is True
        assert config["slice_period_days"] == 14


class TestDeviationCheck:
    """偏差检测流程测试"""

    def _make_worker_with_portfolio(self, portfolio_id="p-001"):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_engine = MagicMock()
        mock_portfolio = MagicMock()
        mock_portfolio.portfolio_id = portfolio_id
        mock_portfolio.code = "test-strategy"
        mock_engine.portfolios = [mock_portfolio]
        worker._engine = mock_engine
        # 用 MagicMock 替换懒加载的真实 deviation_checker
        worker._deviation_checker = MagicMock()
        return worker, mock_portfolio

    def test_skip_when_no_detectors(self):
        """无 detector 时应跳过检查"""
        worker, _ = self._make_worker_with_portfolio()
        worker.deviation_checker._detectors = {}

        # 不应抛异常
        worker._run_deviation_check()

    def test_calls_run_deviation_check(self):
        """应调用 deviation_checker.run_deviation_check 处理偏差检测"""
        worker, mock_portfolio = self._make_worker_with_portfolio()

        mock_result = {
            "status": "completed",
            "overall_level": "NORMAL",
            "deviations": {},
        }
        worker.deviation_checker.run_deviation_check.return_value = mock_result
        worker.deviation_checker.run_daily_point_check.return_value = None

        with patch.object(worker, "_load_today_records", return_value={"analyzers": []}):
            with patch.object(worker, "_get_deviation_config", return_value={"auto_takedown": False}):
                worker._run_deviation_check()

        worker.deviation_checker.run_deviation_check.assert_called_once()
        worker.deviation_checker.handle_deviation_result.assert_called_once()

    def test_no_handle_when_no_result(self):
        """run_deviation_check 返回 None 时不应调用 handle_deviation_result"""
        worker, _ = self._make_worker_with_portfolio()

        worker.deviation_checker.run_deviation_check.return_value = None

        with patch.object(worker, "_load_today_records", return_value={"analyzers": []}):
            worker._run_deviation_check()

        worker.deviation_checker.handle_deviation_result.assert_not_called()

    def test_continues_on_portfolio_error(self):
        """单个 portfolio 异常不应中断其他 portfolio 的检查"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_engine = MagicMock()

        mock_p1 = MagicMock()
        mock_p1.portfolio_id = "p-001"
        mock_p2 = MagicMock()
        mock_p2.portfolio_id = "p-002"
        mock_engine.portfolios = [mock_p1, mock_p2]
        worker._engine = mock_engine
        worker._deviation_checker = MagicMock()
        worker.deviation_checker.run_deviation_check.side_effect = Exception("clickhouse error")

        with patch.object(worker, "_load_today_records", return_value={"analyzers": []}):
            # 不应抛异常
            worker._run_deviation_check()

        # run_deviation_check 对每个 portfolio 都会被调用
        assert worker.deviation_checker.run_deviation_check.call_count == 2


class TestLoadTodayRecords:
    """_load_today_records 测试"""

    def test_filters_records_by_today(self):
        """应只返回当日的 analyzer 记录"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = MagicMock()

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = "2020-01-01"

        # Mock records
        mock_record_today = MagicMock()
        mock_record_today.name = "net_value"
        mock_record_today.value = 1.05
        mock_record_today.timestamp = f"{today} 15:00:00"

        mock_record_old = MagicMock()
        mock_record_old.name = "net_value"
        mock_record_old.value = 1.03
        mock_record_old.timestamp = f"{yesterday} 15:00:00"

        mock_analyzer_svc = MagicMock()
        mock_analyzer_svc.get_by_run_id.return_value = MagicMock(
            is_success=True,
            data=[mock_record_today, mock_record_old],
        )

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.services.analyzer_service.return_value = mock_analyzer_svc
            records = worker._load_today_records("p-001")

        assert len(records["analyzers"]) == 1
        assert records["analyzers"][0]["name"] == "net_value"

    def test_returns_empty_on_service_error(self):
        """服务异常时应返回空记录"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = MagicMock()

        mock_analyzer_svc = MagicMock()
        mock_analyzer_svc.get_by_run_id.return_value = MagicMock(
            is_success=False,
            data=None,
        )

        with patch("ginkgo.services", create=True) as mock_services:
            mock_services.data.services.analyzer_service.return_value = mock_analyzer_svc
            records = worker._load_today_records("p-001")

        assert records["analyzers"] == []


class TestHandleDeviationResult:
    """_handle_deviation_result 测试"""

    def _make_worker(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test-1")
        worker._engine = MagicMock()
        mock_portfolio = MagicMock()
        mock_portfolio.portfolio_id = "p-001"
        mock_portfolio.code = "test-strategy"
        return worker, mock_portfolio

    def test_normal_is_silent(self):
        """NORMAL 级别不应发送告警"""
        worker, mock_portfolio = self._make_worker()

        result = {"overall_level": "NORMAL", "deviations": {}}
        with patch.object(worker, "_send_deviation_alert") as mock_alert:
            worker._handle_deviation_result(mock_portfolio, result)

        mock_alert.assert_not_called()

    def test_moderate_sends_alert(self):
        """MODERATE 级别应发送告警"""
        worker, mock_portfolio = self._make_worker()

        result = {
            "overall_level": "MODERATE",
            "deviations": {"sharpe_ratio": {"level": "MODERATE", "z_score": -1.5}},
        }
        with patch.object(worker, "_send_deviation_alert") as mock_alert:
            with patch.object(worker, "_handle_unload") as mock_unload:
                worker._handle_deviation_result(mock_portfolio, result)

        mock_alert.assert_called_once()
        mock_unload.assert_not_called()

    def test_severe_sends_alert(self):
        """SEVERE 级别应发送告警"""
        worker, mock_portfolio = self._make_worker()

        result = {
            "overall_level": "SEVERE",
            "deviations": {"max_drawdown": {"level": "SEVERE", "z_score": 2.5}},
        }
        with patch.object(worker, "_send_deviation_alert") as mock_alert:
            with patch.object(worker, "_handle_unload") as mock_unload:
                worker._handle_deviation_result(mock_portfolio, result)

        mock_alert.assert_called_once()
        mock_unload.assert_not_called()  # auto_takedown 默认关闭

    def test_severe_auto_takedown_when_enabled(self):
        """SEVERE + auto_takedown=true 应触发 unload"""
        worker, mock_portfolio = self._make_worker()

        result = {
            "overall_level": "SEVERE",
            "deviations": {"max_drawdown": {"level": "SEVERE", "z_score": 2.5}},
        }

        with patch.object(worker, "_get_deviation_config",
                           return_value={"auto_takedown": True}):
            with patch.object(worker, "_send_deviation_alert") as mock_alert:
                with patch.object(worker, "_handle_unload", return_value=True) as mock_unload:
                    worker._handle_deviation_result(mock_portfolio, result)

        mock_unload.assert_called_once_with({"portfolio_id": "p-001"})


class TestSendDeviationAlert:
    """_send_deviation_alert 测试"""

    def test_sends_to_system_events(self):
        """应发送告警到 SYSTEM_EVENTS topic"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        mock_producer = MagicMock()
        worker._producer = mock_producer

        mock_portfolio = MagicMock()
        mock_portfolio.portfolio_id = "p-001"
        mock_portfolio.code = "test-strategy"

        result = {
            "overall_level": "MODERATE",
            "deviations": {"sharpe_ratio": {"level": "MODERATE", "z_score": -1.5}},
        }

        worker._send_deviation_alert(mock_portfolio, "MODERATE", result)

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        assert call_args[0][0] == "ginkgo.live.system.events"
        msg = call_args[0][1]
        assert msg["type"] == "deviation_alert"
        assert msg["level"] == "MODERATE"
        assert msg["portfolio_id"] == "p-001"

    def test_noop_without_producer(self):
        """无 producer 时不应抛异常"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker(worker_id="test-1")
        worker._producer = None

        # 不应抛异常
        worker._send_deviation_alert(MagicMock(), "SEVERE", {})
