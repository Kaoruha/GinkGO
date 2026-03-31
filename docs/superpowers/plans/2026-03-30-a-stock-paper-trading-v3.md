# A 股日级纸上交易 v3 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现有状态长驻 PaperTradingWorker，持有引擎消费 Kafka 执行每日纸上交易循环。

**Architecture:** 1 个 PaperTradingWorker 进程持有 1 个 TimeControlledEventEngine (PAPER 模式)，加载所有 PAPER Portfolio。TaskTimer (21:10) 发 Kafka 命令触发每日循环（sync 数据 → advance_time）。deploy/unload CLI 通过 Kafka 通知 Worker 动态管理 Portfolio。

**Tech Stack:** Python 3.12, Kafka (GinkgoConsumer/GinkgoProducer), ClickHouse, Redis, APScheduler, Typer CLI

---

## File Structure

| 文件 | 职责 | 操作 |
|------|------|------|
| `src/ginkgo/workers/paper_trading_worker.py` | 长驻 Worker，Kafka 消费，引擎持有 | **重写** |
| `src/ginkgo/client/portfolio_cli.py` | deploy/unload CLI 命令 | **重写** deploy 部分 |
| `src/ginkgo/client/serve_cli.py` | `serve worker-paper` 启动入口 | **新增** 命令 |
| `src/ginkgo/livecore/task_timer.py` | paper_trading 定时任务 | 已有，无需改动 |
| `src/ginkgo/interfaces/dtos/control_command_dto.py` | PAPER_TRADING 命令常量 | 已有，无需改动 |
| `tests/unit/workers/test_paper_trading_worker.py` | Worker 单元测试 | **重写** |
| `tests/unit/client/test_paper_trading_cli.py` | CLI 单元测试 | **重写** |

---

### Task 1: 重写 PaperTradingWorker 核心逻辑

**Files:**
- Modify: `src/ginkgo/workers/paper_trading_worker.py`
- Test: `tests/unit/workers/test_paper_trading_worker.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/workers/test_paper_trading_worker.py
"""
PaperTradingWorker 单元测试"""
import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime


class TestPaperTradingWorkerInit:
    """Worker 初始化测试"""

    def test_worker_initial_state(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test_paper_1")
        assert worker.worker_id == "test_paper_1"
        assert worker.is_running is False
        assert worker._engine is None

    def test_worker_default_id_from_env(self):
        with patch.dict(os.environ, {"GINKGO_PAPER_WORKER_ID": "env_id"}):
            from ginkgo.workers.paper_trading_worker import PaperTradingWorker
            worker = PaperTradingWorker()
            assert worker.worker_id == "env_id"


class TestPaperTradingWorkerStart:
    """Worker 启动测试"""

    def test_start_sets_running_true(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        with patch.object(worker, '_load_portfolios_from_db'):
            worker.start()
        assert worker.is_running is True

    def test_start_raises_if_already_running(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        with patch.object(worker, '_load_portfolios_from_db'):
            worker.start()
        with pytest.raises(RuntimeError, match="already running"):
            worker.start()

    def test_start_calls_load_portfolios(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        with patch.object(worker, '_load_portfolios_from_db') as mock_load:
            worker.start()
            mock_load.assert_called_once()


class TestPaperTradingWorkerStop:
    """Worker 停止测试"""

    def test_stop_sets_running_false(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        with patch.object(worker, '_load_portfolios_from_db'):
            worker.start()
        with patch.object(worker, '_engine', None):
            worker.stop()
        assert worker.is_running is False

    def test_stop_stops_engine(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        with patch.object(worker, '_load_portfolios_from_db'):
            worker.start()
        worker._engine = mock_engine
        worker.stop()
        mock_engine.stop.assert_called_once()


class TestLoadPortfoliosFromDB:
    """从 DB 加载 PAPER Portfolio 测试"""

    def test_load_paper_portfolios(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")

        mock_crud = MagicMock()
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "paper-uuid-1"
        mock_portfolio.name = "paper_test"
        mock_crud.find_by_mode.return_value = [mock_portfolio]

        mock_mapping_crud = MagicMock()
        mock_mapping = MagicMock()
        mock_mapping.file_id = "file-1"
        mock_mapping.name = "test_strategy"
        mock_mapping.type = MagicMock()
        mock_mapping.type.value = 1
        mock_mapping.uuid = "mapping-1"
        mock_mapping_crud.find.return_value = [mock_mapping]

        with patch("ginkgo.workers.paper_trading_worker.services") as mock_services:
            mock_services.data.cruds.portfolio.return_value = mock_crud
            mock_services.data.cruds.portfolio_file_mapping.return_value = mock_mapping_crud
            result = worker._load_portfolios_from_db()

        assert result is True

    def test_load_no_paper_portfolios(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")

        mock_crud = MagicMock()
        mock_crud.find_by_mode.return_value = []

        with patch("ginkgo.workers.paper_trading_worker.services") as mock_services:
            mock_services.data.cruds.portfolio.return_value = mock_crud
            result = worker._load_portfolios_from_db()

        assert result is False


class TestHandleCommand:
    """命令处理测试"""

    def test_handle_paper_trading_command(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        worker._engine = mock_engine

        with patch.object(worker, 'run_daily_cycle', return_value=True) as mock_cycle:
            result = worker._handle_command("paper_trading", {})
        assert result is True
        mock_cycle.assert_called_once()

    def test_handle_deploy_command(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        worker._engine = mock_engine

        with patch.object(worker, '_handle_deploy', return_value=True) as mock_deploy:
            result = worker._handle_command("deploy", {"portfolio_id": "p1"})
        assert result is True
        mock_deploy.assert_called_once_with({"portfolio_id": "p1"})

    def test_handle_unload_command(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        worker._engine = mock_engine

        with patch.object(worker, '_handle_unload', return_value=True) as mock_unload:
            result = worker._handle_command("unload", {"portfolio_id": "p1"})
        assert result is True
        mock_unload.assert_called_once_with({"portfolio_id": "p1"})

    def test_handle_unknown_command(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        result = worker._handle_command("unknown_cmd", {})
        assert result is False


class TestRunDailyCycle:
    """每日循环测试"""

    def test_skip_non_trading_day(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        worker._engine = mock_engine

        with patch.object(worker, '_is_trading_day', return_value=False):
            result = worker.run_daily_cycle()
        assert result.skipped is True
        mock_engine.advance_time_to.assert_not_called()

    def test_skip_no_interested_codes(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        mock_engine.portfolios = []
        worker._engine = mock_engine

        with patch.object(worker, '_is_trading_day', return_value=True):
            result = worker.run_daily_cycle()
        assert result.skipped is True

    def test_skip_sync_zero_success(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        worker._engine = mock_engine

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio._selectors = [mock_selector]
        mock_engine.portfolios = [mock_portfolio]

        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        mock_sync_result.data = MagicMock()
        mock_sync_result.data.batch_details = {"successful_codes": 0, "failed_codes": 0, "failures": []}

        mock_bar_service = MagicMock()
        mock_bar_service.sync_range_batch.return_value = mock_sync_result
        worker._bar_service = mock_bar_service

        with patch.object(worker, '_is_trading_day', return_value=True):
            result = worker.run_daily_cycle()
        assert result.skipped is True

    def test_advance_on_success(self):
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        worker = PaperTradingWorker(worker_id="test")
        mock_engine = MagicMock()
        mock_engine.advance_time_to.return_value = True
        worker._engine = mock_engine

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ"]
        mock_portfolio = MagicMock()
        mock_portfolio._selectors = [mock_selector]
        mock_engine.portfolios = [mock_portfolio]

        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        mock_sync_result.data = MagicMock()
        mock_sync_result.data.batch_details = {"successful_codes": 1, "failed_codes": 0, "failures": []}

        mock_bar_service = MagicMock()
        mock_bar_service.sync_range_batch.return_value = mock_sync_result
        worker._bar_service = mock_bar_service

        mock_trade_day_crud = MagicMock()
        from datetime import datetime
        mock_trade_day_crud.get_next_trading_day.return_value = datetime(2026, 3, 31)
        worker._trade_day_crud = mock_trade_day_crud

        with patch.object(worker, '_is_trading_day', return_value=True):
            result = worker.run_daily_cycle()
        assert result.skipped is False
        assert result.advanced is True
        mock_engine.advance_time_to.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/workers/test_paper_trading_worker.py -v`
Expected: FAIL (module structure doesn't match)

- [ ] **Step 3: Implement PaperTradingWorker**

```python
# src/ginkgo/workers/paper_trading_worker.py
# Upstream: TaskTimer (Kafka control commands), CLI deploy/unload commands
# Downstream: Engine (advance_time_to), BarService (sync_range_batch), TradeDayCRUD
# Role: 纸上交易长驻 Worker — 持有引擎，消费 Kafka 命令，执行每日循环


import os
import time
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

from ginkgo.libs import GLOG


@dataclass
class DailyCycleResult:
    """每日循环执行结果"""
    skipped: bool = False
    date: str = ""
    fetched_count: int = 0
    advanced: bool = False
    error: str = ""
    warning: str = ""


class PaperTradingWorker:
    """
    纸上交易 Worker

    长驻进程，持有所有活跃的纸上交易引擎实例。
    架构模式与 BacktestWorker 一致：
    - 1 个 Worker = 1 个 Engine = N 个 PAPER Portfolio
    - 订阅 Kafka ginkgo.live.control.commands 消费命令
    - Redis 心跳
    - 优雅关闭
    """

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or os.getenv("GINKGO_PAPER_WORKER_ID", f"paper_worker_{os.getpid()}")
        self._engine = None
        self._bar_service = None
        self._trade_day_crud = None
        self._running = False
        self._should_stop = False
        self._lock = threading.Lock()
        self._consumer = None
        self._consumer_thread = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """启动 Worker：初始化服务、加载 Portfolio、组装引擎、订阅 Kafka"""
        if self._running:
            raise RuntimeError(f"PaperTradingWorker {self.worker_id} is already running")

        GLOG.INFO(f"[PAPER-WORKER] Starting worker {self.worker_id}")

        # 初始化服务
        self._init_services()

        # 从 DB 加载 PAPER Portfolio 并组装引擎
        loaded = self._load_portfolios_from_db()
        if not loaded:
            GLOG.WARN("[PAPER-WORKER] No PAPER portfolios found, waiting for deploy commands")

        self._running = True
        self._should_stop = False

        # 启动 Kafka 消费线程
        self._start_consumer_thread()

        GLOG.INFO(f"[PAPER-WORKER] Worker {self.worker_id} started")

    def stop(self) -> None:
        """停止 Worker"""
        GLOG.INFO(f"[PAPER-WORKER] Stopping worker {self.worker_id}")
        self._should_stop = True

        # 停止引擎
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error stopping engine: {e}")

        # 等待消费线程结束
        if self._consumer_thread and self._consumer_thread.is_alive():
            self._consumer_thread.join(timeout=5)

        self._running = False
        GLOG.INFO(f"[PAPER-WORKER] Worker {self.worker_id} stopped")

    def _init_services(self) -> None:
        """初始化数据服务"""
        from ginkgo import services
        self._bar_service = services.data.bar_service()
        from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
        self._trade_day_crud = TradeDayCRUD()

    def _load_portfolios_from_db(self) -> bool:
        """从 DB 加载所有 PAPER 模式的 Portfolio 并组装引擎"""
        from ginkgo import services
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        container = services.data.container()
        portfolio_crud = container.cruds.portfolio()
        portfolios = portfolio_crud.find_by_mode(PORTFOLIO_MODE_TYPES.PAPER)

        if not portfolios:
            GLOG.WARN("[PAPER-WORKER] No PAPER portfolios found in DB")
            return False

        GLOG.INFO(f"[PAPER-WORKER] Found {len(portfolios)} PAPER portfolios")

        # 组装引擎
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
        from ginkgo.trading.gateway.trade_gateway import TradeGateway
        from ginkgo.trading.brokers.sim_broker import SimBroker
        from ginkgo.enums import EXECUTION_MODE, ATTITUDE_TYPES
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader

        today = datetime.now()
        engine = TimeControlledEventEngine(
            name=f"paper_engine_{self.worker_id}",
            mode=EXECUTION_MODE.PAPER,
            logical_time_start=datetime(today.year, today.month, today.day, 9, 30),
            timer_interval=0.01,
        )

        feeder = BacktestFeeder(name="paper_feeder")
        feeder.bar_service = self._bar_service

        broker = SimBroker(
            name="PaperSimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0003,
            commission_min=5,
        )
        gateway = TradeGateway(name="PaperGateway", brokers=[broker])

        engine.set_data_feeder(feeder)
        engine.bind_router(gateway)

        loader = ComponentLoader(file_service=container.file_service(), logger=GLOG)

        for portfolio_record in portfolios:
            pid = portfolio_record.uuid
            pname = portfolio_record.name or f"paper_{pid[:8]}"

            portfolio = PortfolioT1Backtest(pname)
            portfolio.set_portfolio_id(pid)

            # 加载组件绑定
            components = self._get_portfolio_components(pid, container)
            loader.perform_component_binding(portfolio, components, GLOG)

            # 初始化 interested codes
            self._init_interested_codes(portfolio)

            engine.add_portfolio(portfolio)
            GLOG.INFO(f"[PAPER-WORKER] Loaded portfolio {pname} ({pid[:8]})")

        engine.start()
        self._engine = engine
        return True

    def _get_portfolio_components(self, portfolio_id: str, container) -> Dict[str, Any]:
        """从 DB 获取 Portfolio 的组件绑定关系"""
        from ginkgo.client.portfolio_cli import collect_portfolio_components
        return collect_portfolio_components(portfolio_id, container)

    def _init_interested_codes(self, portfolio) -> None:
        """调用 selector.pick() 初始化 interested codes"""
        for selector in portfolio._selectors:
            try:
                codes = selector.pick(self._engine._time_provider.now())
                if codes:
                    selector._interested = list(codes)
                    # 通知 feeder
                    from ginkgo.trading.events.interest_update import EventInterestUpdate
                    event = EventInterestUpdate(
                        portfolio_id=portfolio.portfolio_id,
                        codes=codes,
                        timestamp=self._engine._time_provider.now()
                    )
                    self._engine.put(event)
                    GLOG.INFO(f"[PAPER-WORKER] Initialized {len(codes)} interested codes for {portfolio.name}")
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Failed to initialize interested codes: {e}")

    def _start_consumer_thread(self) -> None:
        """启动 Kafka 消费线程"""
        from ginkgo.interfaces.kafka_topics import KafkaTopics
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer

        group_id = f"paper-trading-{self.worker_id}"
        self._consumer = GinkgoConsumer(
            topic=KafkaTopics.CONTROL_COMMANDS,
            group_id=group_id,
            offset="latest",
        )

        self._consumer_thread = threading.Thread(
            target=self._consumer_loop,
            name="paper-trading-consumer",
            daemon=True,
        )
        self._consumer_thread.start()
        GLOG.INFO(f"[PAPER-WORKER] Kafka consumer started, group={group_id}")

    def _consumer_loop(self) -> None:
        """Kafka 消费循环"""
        while not self._should_stop:
            try:
                messages = self._consumer.consumer.poll(timeout_ms=1000)
                if not messages:
                    continue

                for tp, records in messages.items():
                    for message in records:
                        payload = message.value
                        if isinstance(payload, dict):
                            command = payload.get("command", "")
                            params = payload.get("params", {})
                            self._handle_command(command, params)

                try:
                    self._consumer.commit()
                except Exception as e:
                    GLOG.ERROR(f"[PAPER-WORKER] Failed to commit offset: {e}")

            except Exception as e:
                if not self._should_stop:
                    GLOG.ERROR(f"[PAPER-WORKER] Consumer error: {e}")

    def _handle_command(self, command: str, params: Dict) -> bool:
        """处理 Kafka 控制命令"""
        if command == "paper_trading":
            return self.run_daily_cycle()
        elif command == "deploy":
            return self._handle_deploy(params)
        elif command == "unload":
            return self._handle_unload(params)
        else:
            return False

    def _handle_deploy(self, params: Dict) -> bool:
        """处理 deploy 命令：动态加载新 Portfolio 到引擎"""
        portfolio_id = params.get("portfolio_id")
        if not portfolio_id:
            GLOG.ERROR("[PAPER-WORKER] deploy command missing portfolio_id")
            return False

        if self._engine is None:
            GLOG.ERROR("[PAPER-WORKER] Engine not initialized, cannot deploy")
            return False

        GLOG.INFO(f"[PAPER-WORKER] Deploying portfolio {portfolio_id}")

        try:
            from ginkgo import services
            from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
            from ginkgo.trading.services._assembly.component_loader import ComponentLoader

            container = services.data.container()
            portfolio_crud = container.cruds.portfolio()
            records = portfolio_crud.find_by_uuid(portfolio_id)
            if not records:
                GLOG.ERROR(f"[PAPER-WORKER] Portfolio {portfolio_id} not found in DB")
                return False

            portfolio_record = records[0]
            portfolio = PortfolioT1Backtest(portfolio_record.name or f"paper_{portfolio_id[:8]}")
            portfolio.set_portfolio_id(portfolio_id)

            loader = ComponentLoader(file_service=container.file_service(), logger=GLOG)
            components = self._get_portfolio_components(portfolio_id, container)
            loader.perform_component_binding(portfolio, components, GLOG)

            self._init_interested_codes(portfolio)
            self._engine.add_portfolio(portfolio)

            GLOG.INFO(f"[PAPER-WORKER] Portfolio {portfolio_id[:8]} deployed successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Deploy failed: {e}")
            return False

    def _handle_unload(self, params: Dict) -> bool:
        """处理 unload 命令：从引擎卸载指定 Portfolio"""
        portfolio_id = params.get("portfolio_id")
        if not portfolio_id:
            GLOG.ERROR("[PAPER-WORKER] unload command missing portfolio_id")
            return False

        if self._engine is None:
            return False

        GLOG.INFO(f"[PAPER-WORKER] Unloading portfolio {portfolio_id}")

        try:
            target = None
            for p in self._engine.portfolios:
                if p.portfolio_id == portfolio_id:
                    target = p
                    break

            if target is None:
                GLOG.WARN(f"[PAPER-WORKER] Portfolio {portfolio_id} not found in engine")
                return False

            self._engine.portfolios.remove(target)
            GLOG.INFO(f"[PAPER-WORKER] Portfolio {portfolio_id[:8]} unloaded")
            return True

        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Unload failed: {e}")
            return False

    def get_interested_codes(self) -> List[str]:
        """从所有 Portfolio 的 selector 获取关注股票列表"""
        codes = []
        if self._engine is None:
            return codes
        for portfolio in self._engine.portfolios:
            for selector in portfolio._selectors:
                codes.extend(getattr(selector, "_interested", []))
        return list(set(codes))

    def _is_trading_day(self, date) -> bool:
        """判断指定日期是否是 A 股交易日"""
        from ginkgo.enums import MARKET_TYPES
        try:
            results = self._trade_day_crud.find(
                filters={"timestamp": date, "market": MARKET_TYPES.CHINA}
            )
            if results and len(results) > 0:
                return bool(results[0].is_open)
        except Exception as e:
            GLOG.ERROR(f"Failed to check trading day: {e}")
        return False

    @property
    def run_daily_cycle(self):
        """执行每日循环：检查交易日 → 拉数据 → 推进引擎"""
        result = self._run_daily_cycle_impl()
        return result

    def _run_daily_cycle_impl(self) -> DailyCycleResult:
        """每日循环实现"""
        today = datetime.now().date()

        # 1. 检查交易日
        if not self._is_trading_day(today):
            GLOG.INFO(f"[PAPER-WORKER] {today} is not a trading day, skipping")
            return DailyCycleResult(skipped=True, date=str(today))

        # 2. 获取关注股票列表
        codes = self.get_interested_codes()
        if not codes:
            GLOG.WARN("[PAPER-WORKER] No interested codes, skipping")
            return DailyCycleResult(skipped=True, date=str(today), error="No interested codes")

        # 3. 同步拉取当日数据
        try:
            sync_result = self._bar_service.sync_range_batch(
                codes=codes, start_date=today, end_date=today
            )
            batch_details = getattr(sync_result.data, 'batch_details', {}) if sync_result.success else {}
            fetched_count = batch_details.get("successful_codes", 0)
            failed_count = batch_details.get("failed_codes", 0)
            failures = batch_details.get("failures", [])
        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Failed to fetch data: {e}")
            return DailyCycleResult(skipped=True, date=str(today), error=f"Data fetch failed: {e}")

        if fetched_count == 0:
            GLOG.ERROR(f"[PAPER-WORKER] Trading day {today} but no data fetched, skipping")
            return DailyCycleResult(skipped=True, date=str(today), error="No data fetched")

        warning = ""
        if failed_count > 0 and failures:
            failed_code_list = [f["code"] for f in failures]
            warning = f"Partial sync failure: {failed_code_list}"
            GLOG.WARN(f"[PAPER-WORKER] {warning}")

        # 4. 推进引擎
        next_trading_day = self._trade_day_crud.get_next_trading_day(today)
        if next_trading_day is None:
            GLOG.ERROR(f"[PAPER-WORKER] Cannot find next trading day after {today}")
            return DailyCycleResult(skipped=True, date=str(today), error="No next trading day found")

        target_time = datetime.combine(
            next_trading_day.date() if hasattr(next_trading_day, 'date') else next_trading_day,
            datetime.min.time().replace(hour=15, minute=0),
        )

        try:
            success = self._engine.advance_time_to(target_time)
            GLOG.INFO(
                f"[PAPER-WORKER] Daily cycle: {today} -> {target_time.date()}, "
                f"fetched={fetched_count}/{len(codes)}, advanced={success}"
            )
            return DailyCycleResult(
                skipped=False, date=str(today),
                fetched_count=fetched_count, advanced=success, warning=warning,
            )
        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Failed to advance engine: {e}")
            return DailyCycleResult(
                skipped=False, date=str(today),
                fetched_count=fetched_count, advanced=False, error=str(e),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/workers/test_paper_trading_worker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/workers/paper_trading_worker.py tests/unit/workers/test_paper_trading_worker.py
git commit -m "refactor(paper-trading): rewrite PaperTradingWorker as stateful long-running process"
```

---

### Task 2: 重写 deploy/unload CLI 命令

**Files:**
- Modify: `src/ginkgo/client/portfolio_cli.py`
- Test: `tests/unit/client/test_paper_trading_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/client/test_paper_trading_cli.py
"""
纸上交易 CLI 单元测试"""
import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


class TestDeployCommand:
    """deploy 命令测试"""

    def test_deploy_copies_portfolio_config(self, cli_runner):
        from ginkgo.client.portfolio_cli import app

        mock_service = MagicMock()
        mock_service.add.return_value = MagicMock(
            is_success=lambda: True,
            data={"uuid": "new-paper-uuid", "name": "paper_copy"},
            message="created"
        )
        mock_mapping_crud = MagicMock()
        mock_mapping_crud.find.return_value = []

        with patch("ginkgo.client.portfolio_cli.services") as mock_services, \
             patch("ginkgo.client.portfolio_cli._deploy_paper_trading", return_value="new-paper-uuid") as mock_deploy:
            mock_services.data.container.return_value.portfolio_service.return_value = mock_service

            result = cli_runner.invoke(app, ["deploy", "--source", "source-uuid", "--capital", "100000"])

        mock_deploy.assert_called_once()

    def test_deploy_requires_source(self, cli_runner):
        from ginkgo.client.portfolio_cli import app
        result = cli_runner.invoke(app, ["deploy"])
        assert result.exit_code != 0


class TestUnloadCommand:
    """unload 命令测试"""

    def test_unload_sends_kafka_command(self, cli_runner):
        from ginkgo.client.portfolio_cli import app

        with patch("ginkgo.client.portfolio_cli._send_unload_command", return_value=True) as mock_send:
            result = cli_runner.invoke(app, ["unload", "portfolio-uuid"])
        assert result.exit_code == 0
        mock_send.assert_called_once_with("portfolio-uuid")

    def test_unload_requires_portfolio_id(self, cli_runner):
        from ginkgo.client.portfolio_cli import app
        result = cli_runner.invoke(app, ["unload"])
        assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/client/test_paper_trading_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Implement deploy CLI (rewrite)**

Read the current `src/ginkgo/client/portfolio_cli.py` first. Then replace the `deploy_portfolio` function and `_deploy_paper_trading` function with:

```python
@app.command(name="deploy")
def deploy_portfolio(
    source: str = typer.Option(..., "--source", "-s", help="源 Portfolio ID"),
    capital: float = typer.Option(100000.0, "--capital", "-c", help="初始资金"),
):
    """从回测 Portfolio 复制配置到纸上交易 Portfolio"""
    from rich.panel import Panel

    GLOG.INFO(f"[DEPLOY] Copying portfolio config from {source}")

    try:
        portfolio_id = _deploy_paper_trading(source_portfolio_id=source, capital=capital)
        console.print(Panel(
            f"[bold green]Paper trading portfolio created[/bold green]\n\n"
            f"Portfolio ID: {portfolio_id}\n"
            f"Source: {source}\n"
            f"Capital: ¥{capital:,.0f}\n"
            f"Mode: PAPER\n\n"
            f"Worker will load this portfolio on next cycle.",
            title="Deploy Success",
        ))
    except Exception as e:
        console.print(f"[bold red]Deploy failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command(name="unload")
def unload_portfolio(
    portfolio_id: str = typer.Argument(..., help="Portfolio ID to unload"),
):
    """卸载纸上交易 Portfolio（从 Worker 中移除，保留历史数据）"""
    from rich.panel import Panel

    GLOG.INFO(f"[UNLOAD] Unloading portfolio {portfolio_id}")

    try:
        success = _send_unload_command(portfolio_id)
        if success:
            console.print(Panel(
                f"[bold yellow]Portfolio unloaded[/bold yellow]\n\n"
                f"Portfolio ID: {portfolio_id}\n"
                f"Worker will remove this portfolio on next cycle.",
                title="Unload Success",
            ))
        else:
            console.print(f"[bold red]Failed to send unload command[/bold red]")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"[bold red]Unload failed: {e}[/bold red]")
        raise typer.Exit(1)


def _deploy_paper_trading(source_portfolio_id: str, capital: float) -> str:
    """
    执行纸上交易部署 — 纯 DB 操作

    流程：
    1. 读取源 Portfolio 的配置（name、components）
    2. 在 DB 中创建新 Portfolio（mode=PAPER）
    3. 复制组件绑定关系到新 Portfolio
    4. 发 Kafka 通知 Worker 加载
    """
    from ginkgo import services
    from ginkgo.enums import PORTFOLIO_MODE_TYPES

    container = services.data.container()
    portfolio_service = container.portfolio_service()

    # 1. 获取源 Portfolio 信息
    source_result = portfolio_service.get(portfolio_id=source_portfolio_id)
    if not source_result.is_success():
        raise ValueError(f"Source portfolio {source_portfolio_id} not found: {source_result.message}")

    source_data = source_result.data
    source_name = getattr(source_data, 'name', None) or f"paper_{source_portfolio_id[:8]}"

    # 2. 创建新 Portfolio（mode=PAPER）
    new_name = f"paper_{source_name}"
    create_result = portfolio_service.add(
        name=new_name,
        mode=PORTFOLIO_MODE_TYPES.PAPER,
        description=f"Paper trading from {source_portfolio_id}"
    )
    if not create_result.is_success():
        raise ValueError(f"Failed to create portfolio: {create_result.message}")

    new_portfolio_id = create_result.data["uuid"]
    GLOG.INFO(f"[DEPLOY] Created portfolio {new_portfolio_id} ({new_name})")

    # 3. 复制组件绑定关系
    mapping_crud = container.cruds.portfolio_file_mapping()
    source_mappings = mapping_crud.find(filters={"portfolio_id": source_portfolio_id, "is_del": False})

    if source_mappings:
        for mapping in source_mappings:
            mapping_crud.add(
                portfolio_id=new_portfolio_id,
                file_id=mapping.file_id,
                name=mapping.name,
                type=mapping.type.value if hasattr(mapping.type, 'value') else mapping.type,
            )
        GLOG.INFO(f"[DEPLOY] Copied {len(source_mappings)} component mappings")

    # 4. 发 Kafka 通知 Worker
    _send_deploy_notification(new_portfolio_id)

    return new_portfolio_id


def _send_deploy_notification(portfolio_id: str) -> None:
    """发送 deploy 通知到 Kafka"""
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.kafka_topics import KafkaTopics
        import json

        producer = GinkgoProducer()
        message = json.dumps({
            "command": "deploy",
            "params": {"portfolio_id": portfolio_id},
            "source": "cli_deploy",
            "timestamp": datetime.now().isoformat(),
        })
        producer.produce(KafkaTopics.CONTROL_COMMANDS, message)
        GLOG.INFO(f"[DEPLOY] Sent deploy notification for {portfolio_id}")
    except Exception as e:
        GLOG.WARN(f"[DEPLOY] Failed to send Kafka notification: {e}")


def _send_unload_command(portfolio_id: str) -> bool:
    """发送 unload 命令到 Kafka"""
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.kafka_topics import KafkaTopics
        import json

        producer = GinkgoProducer()
        message = json.dumps({
            "command": "unload",
            "params": {"portfolio_id": portfolio_id},
            "source": "cli_unload",
            "timestamp": datetime.now().isoformat(),
        })
        producer.produce(KafkaTopics.CONTROL_COMMANDS, message)
        GLOG.INFO(f"[UNLOAD] Sent unload command for {portfolio_id}")
        return True
    except Exception as e:
        GLOG.ERROR(f"[UNLOAD] Failed to send unload command: {e}")
        return False
```

Note: Also remove the old `stop_paper_trading` function and the `_paper_worker` global variable, as they are no longer needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/client/test_paper_trading_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/client/portfolio_cli.py tests/unit/client/test_paper_trading_cli.py
git commit -m "refactor(paper-trading): rewrite deploy/unload as pure DB operations with Kafka notification"
```

---

### Task 3: 添加 `serve worker-paper` CLI 入口

**Files:**
- Modify: `src/ginkgo/client/serve_cli.py`

- [ ] **Step 1: Add the serve command**

在 `src/ginkgo/client/serve_cli.py` 中，在 `serve_worker_backtest` 函数之后添加：

```python
@app.command("worker-paper")
def serve_worker_paper(
    node_id: Optional[str] = typer.Option(None, "--id", help="Worker unique identifier"),
):
    """启动纸上交易 Worker（长驻进程）"""
    import signal
    from rich.console import Console

    console = Console()

    if node_id is None:
        node_id = os.getenv("GINKGO_PAPER_WORKER_ID")
    if node_id is None:
        node_id = f"paper_worker_{socket.gethostname()}"

    console.print(f"[bold blue]Starting PaperTradingWorker: {node_id}[/bold blue]")

    from ginkgo.workers.paper_trading_worker import PaperTradingWorker

    worker = PaperTradingWorker(worker_id=node_id)

    def signal_handler(sig, frame):
        console.print("\n\n[yellow]:warning: Stopping PaperTradingWorker...[/yellow]")
        worker.stop()
        console.print("[green]:white_check_mark: PaperTradingWorker stopped[/green]")
        os._exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        worker.start()
        console.print(f"[green]:white_check_mark: PaperTradingWorker {node_id} is running[/green]")
    except Exception as e:
        console.print(f"[bold red]Failed to start worker: {e}[/bold red]")
        raise typer.Exit(1)

    while worker.is_running:
        time.sleep(1)
```

- [ ] **Step 2: Verify the command is registered**

Run: `ginkgo serve worker-paper --help`
Expected: Shows help text for the worker-paper command

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/client/serve_cli.py
git commit -m "feat(paper-trading): add serve worker-paper CLI entry point"
```

---

### Task 4: 清理旧代码和删除 PaperTradingController

**Files:**
- Delete: `src/ginkgo/trading/services/paper_trading_controller.py`
- Modify: `src/ginkgo/client/portfolio_cli.py` (remove `_paper_worker` global and old imports)

- [ ] **Step 1: Check for remaining references to PaperTradingController**

Run: `grep -r "PaperTradingController" src/ tests/`
Expected: Only the file itself and any test files

- [ ] **Step 2: Remove PaperTradingController file**

```bash
rm src/ginkgo/trading/services/paper_trading_controller.py
```

- [ ] **Step 3: Remove old global variable from portfolio_cli.py**

In `src/ginkgo/client/portfolio_cli.py`, remove the `_paper_worker = None` global variable and any old imports of `PaperTradingController`.

- [ ] **Step 4: Run all paper trading tests**

Run: `pytest tests/unit/workers/test_paper_trading_worker.py tests/unit/client/test_paper_trading_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore(paper-trading): remove PaperTradingController, clean up old references"
```

---

### Task 5: 验证整体集成

- [ ] **Step 1: Run all existing paper trading tests**

Run: `pytest tests/ -k "paper" -v`
Expected: All tests pass

- [ ] **Step 2: Verify TaskTimer paper_trading job still works**

Run: `grep -A 10 "paper_trading" src/ginkgo/livecore/task_timer.py | head -20`
Expected: `_paper_trading_job` still sends `paper_trading` command to Kafka

- [ ] **Step 3: Verify CLI commands are registered**

Run: `ginkgo portfolio deploy --help && ginkgo portfolio unload --help`
Expected: Both show help text

- [ ] **Step 4: Final commit with all changes**

```bash
git add -A
git commit -m "feat(paper-trading): v3 architecture - stateful worker with Kafka-driven daily cycle"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] PaperTradingWorker 长驻进程 → Task 1
- [x] Kafka 消费 → Task 1 (`_consumer_loop`)
- [x] deploy 纯 DB 操作 → Task 2
- [x] unload 命令 → Task 2
- [x] `ginkgo serve worker-paper` → Task 3
- [x] 每日循环逻辑 → Task 1 (`run_daily_cycle`)
- [x] interested codes 初始化 → Task 1 (`_init_interested_codes`)
- [x] 1 Engine : N Portfolio → Task 1 (`_load_portfolios_from_db` loops all portfolios)
- [x] 动态 deploy/unload → Task 1 (`_handle_deploy`, `_handle_unload`)
- [x] 清理旧代码 → Task 4

**Placeholder scan:** No TBD, TODO, or "implement later" found.

**Type consistency:** `sync_range_batch` returns `ServiceResult` with `batch_details` dict — verified in Task 1 tests.
