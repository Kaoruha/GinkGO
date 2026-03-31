# Upstream: TaskTimer (Kafka control commands), CLI deploy command
# Downstream: TimeControlledEventEngine (daily cycle execution)
# Role: 纸上交易 Worker — 持有 TimeControlledEventEngine，消费 Kafka 命令推进


"""
PaperTradingWorker — A股日级纸上交易长驻进程

职责：
- 启动时从 DB 加载所有 PAPER 模式 Portfolio 并组装引擎
- 订阅 Kafka ginkgo.live.control.commands，消费命令
- 每日循环：检查交易日 → 同步数据 → 推进引擎时间
- 支持 deploy（动态加载）/ unload（卸载）命令
"""

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from ginkgo.enums import (
    EXECUTION_MODE,
    PORTFOLIO_MODE_TYPES,
    MARKET_TYPES,
    FREQUENCY_TYPES,
)
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG


@dataclass
class DailyCycleResult:
    """每日循环执行结果"""
    skipped: bool = False
    advanced: bool = False


class PaperTradingWorker:
    """
    纸上交易 Worker

    长驻进程，持有 TimeControlledEventEngine(PAPER 模式)。
    1 Worker = 1 Engine = N PAPER Portfolios。

    通过 Kafka 接收控制命令：
    - paper_trading: 每日循环（TaskTimer cron 21:10 触发）
    - deploy: 动态加载新 Portfolio 到引擎
    - unload: 从引擎卸载指定 Portfolio
    """

    def __init__(self, worker_id: str):
        """
        初始化 PaperTradingWorker

        Args:
            worker_id: Worker 唯一标识
        """
        self.worker_id = worker_id
        self._engine = None
        self._consumer = None
        self._producer = None
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Worker 运行状态"""
        return self._running

    def assemble_engine(self, container) -> None:
        """
        从 DB 加载所有 PAPER 模式的 Portfolio 并组装引擎

        Args:
            container: 服务容器（用于访问 CRUD 和 Service）
        """
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
        from ginkgo.trading.gateway.trade_gateway import TradeGateway
        from ginkgo.trading.brokers.sim_broker import SimBroker
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader
        from ginkgo.client.portfolio_cli import collect_portfolio_components

        GLOG.INFO(f"[PAPER-WORKER] {self.worker_id}: Assembling engine...")

        # 1. 查询所有 PAPER 模式的 Portfolio
        portfolio_crud = container.cruds.portfolio()
        db_portfolios = portfolio_crud.find(
            filters={"mode": PORTFOLIO_MODE_TYPES.PAPER.value}
        )

        if not db_portfolios:
            GLOG.WARN(f"[PAPER-WORKER] {self.worker_id}: No PAPER portfolios found in DB")
            return

        # 2. 创建 PAPER 模式的引擎
        engine = TimeControlledEventEngine(
            name=f"PaperTrading-{self.worker_id}",
            mode=EXECUTION_MODE.PAPER,
            progress_callback=None,
        )

        # 3. 创建共享组件
        feeder = BacktestFeeder()
        broker = SimBroker()
        gateway = TradeGateway(broker=broker)
        loader = ComponentLoader()

        # 4. 加载每个 Portfolio
        for db_portfolio in db_portfolios:
            try:
                # 收集组件绑定信息
                components = collect_portfolio_components(
                    portfolio_id=db_portfolio.uuid,
                    container=container,
                )

                # 创建 Portfolio 实例
                portfolio = PortfolioT1Backtest()
                portfolio.portfolio_id = db_portfolio.uuid
                portfolio.code = db_portfolio.code

                # 加载组件（通过 ComponentLoader）
                self._load_components(portfolio, components, loader)

                # 添加到引擎
                engine.add_portfolio(portfolio)
                GLOG.INFO(
                    f"[PAPER-WORKER] Loaded portfolio {db_portfolio.code} "
                    f"({db_portfolio.uuid[:8]})"
                )

            except Exception as e:
                GLOG.ERROR(
                    f"[PAPER-WORKER] Failed to load portfolio "
                    f"{db_portfolio.uuid}: {e}"
                )

        # 5. 绑定 Feeder
        engine.set_data_feeder(feeder)

        # 6. 绑定 Gateway + Broker
        engine.bind_router(gateway)

        # 7. 初始化 selector interested codes
        for portfolio in engine.portfolios:
            try:
                if hasattr(portfolio, "_selectors") and portfolio._selectors:
                    for selector in portfolio._selectors:
                        if hasattr(selector, "pick"):
                            selector.pick()
            except Exception as e:
                GLOG.WARN(
                    f"[PAPER-WORKER] selector.pick() failed for "
                    f"{portfolio.code}: {e}"
                )

        # 8. 启动引擎
        engine.start()

        self._engine = engine
        GLOG.INFO(
            f"[PAPER-WORKER] {self.worker_id}: Engine assembled with "
            f"{len(engine.portfolios)} portfolios"
        )

    def _load_components(self, portfolio, components: Dict, loader) -> None:
        """将组件从配置字典加载到 Portfolio（消除 assemble_engine 和 _handle_deploy 的重复）"""
        component_bindings = [
            ("strategies", "strategy", portfolio.add_strategy),
            ("risk_managers", "risk_manager", portfolio.add_risk_manager),
            ("selectors", "selector", portfolio.bind_selector),
            ("sizers", "sizer", portfolio.bind_sizer),
            ("analyzers", "analyzer", portfolio.add_analyzer),
        ]
        for key, comp_type, bind_fn in component_bindings:
            for info in components.get(key, []):
                try:
                    comp = loader.instantiate_component_from_dict(info, comp_type)
                    if comp:
                        bind_fn(comp)
                except Exception as e:
                    name = info.get("name", "?")
                    GLOG.ERROR(f"[PAPER-WORKER] Failed to load {comp_type} {name}: {e}")

    def _get_interested_codes(self) -> List[str]:
        """
        从所有 Portfolio 的 selector._interested 收集感兴趣股票代码

        Returns:
            去重后的股票代码列表
        """
        if not self._engine:
            return []

        codes = []
        for portfolio in self._engine.portfolios:
            if hasattr(portfolio, "_selectors"):
                for selector in portfolio._selectors:
                    if hasattr(selector, "_interested"):
                        codes.extend(selector._interested)

        # 去重
        return list(set(codes))

    def run_daily_cycle(self) -> DailyCycleResult:
        """
        执行每日循环

        流程：
        1. 检查是否为交易日
        2. 收集所有 Portfolio 的 interested codes
        3. 调用 bar_service.sync_range_batch 拉取当日数据
        4. 调用 engine.advance_time_to 推进到下一个交易日

        Returns:
            DailyCycleResult: 执行结果
        """
        if not self._engine:
            GLOG.WARN("[PAPER-WORKER] Engine not initialized, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        if not self._engine.portfolios:
            GLOG.DEBUG("[PAPER-WORKER] No portfolios loaded, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        from ginkgo import services

        # 1. 检查交易日
        trade_day_crud = services.data.cruds.trade_day()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        trade_day_records = trade_day_crud.find(
            filters={"timestamp": today, "market": MARKET_TYPES.CHINA.value}
        )

        if not trade_day_records or not trade_day_records[0].is_open:
            GLOG.INFO(f"[PAPER-WORKER] {today.date()} is not a trading day, skipping")
            return DailyCycleResult(skipped=True, advanced=False)

        # 2. 收集 interested codes
        codes = self._get_interested_codes()
        if not codes:
            GLOG.WARN("[PAPER-WORKER] No interested codes, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        # 3. 同步拉取当日数据
        try:
            bar_service = services.data.services.bar_service()
            sync_result = bar_service.sync_range_batch(
                codes=codes,
                start_date=today,
                end_date=today,
                frequency=FREQUENCY_TYPES.DAY,
            )

            batch_details = sync_result.data if sync_result.data else {}
            successful = batch_details.get("successful_codes", 0)
            failed = batch_details.get("failed_codes", 0)

            GLOG.INFO(
                f"[PAPER-WORKER] Data sync: {successful} succeeded, "
                f"{failed} failed, {len(codes)} total codes"
            )

            if failed > 0:
                failures = batch_details.get("failures", [])
                for f in failures:
                    GLOG.WARN(f"[PAPER-WORKER] Sync failure: {f}")

        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Data sync error: {e}")
            # 同步失败仍尝试推进引擎

        # 4. 推进引擎到下一个交易日
        try:
            next_day = trade_day_crud.get_next_trading_day(today)
            if next_day is None:
                GLOG.WARN(f"[PAPER-WORKER] No next trading day found after {today.date()}")
                return DailyCycleResult(skipped=True, advanced=False)

            GLOG.INFO(f"[PAPER-WORKER] Advancing engine to {next_day.date()}")
            self._engine.advance_time_to(next_day)
            return DailyCycleResult(skipped=False, advanced=True)

        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Engine advance error: {e}")
            return DailyCycleResult(skipped=False, advanced=False)

    def _handle_deploy(self, params: Dict) -> bool:
        """
        处理 deploy 命令：动态加载新 Portfolio 到引擎

        Args:
            params: 命令参数，包含 portfolio_id

        Returns:
            是否成功
        """
        if not self._engine:
            GLOG.ERROR("[PAPER-WORKER] Engine not initialized, cannot deploy")
            return False

        portfolio_id = params.get("portfolio_id")
        if not portfolio_id:
            GLOG.ERROR("[PAPER-WORKER] deploy command missing portfolio_id")
            return False

        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader
        from ginkgo.client.portfolio_cli import collect_portfolio_components
        from ginkgo import services

        try:
            # 从 DB 读取 Portfolio 配置
            container = services.data.container
            portfolio_crud = container.cruds.portfolio()
            db_portfolios = portfolio_crud.find(filters={"uuid": portfolio_id})

            if not db_portfolios:
                GLOG.ERROR(f"[PAPER-WORKER] Portfolio {portfolio_id} not found in DB")
                return False

            db_portfolio = db_portfolios[0]

            # 收集组件绑定信息
            components = collect_portfolio_components(
                portfolio_id=portfolio_id,
                container=container,
            )

            # 创建 Portfolio 实例
            portfolio = PortfolioT1Backtest()
            portfolio.portfolio_id = db_portfolio.uuid
            portfolio.code = db_portfolio.code

            # 加载组件
            loader = ComponentLoader()
            self._load_components(portfolio, components, loader)

            # 添加到引擎
            with self._lock:
                self._engine.add_portfolio(portfolio)

            GLOG.INFO(
                f"[PAPER-WORKER] Deployed portfolio {db_portfolio.code} "
                f"({portfolio_id[:8]})"
            )
            return True

        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Deploy failed for {portfolio_id}: {e}")
            return False

    def _handle_unload(self, params: Dict) -> bool:
        """
        处理 unload 命令：从引擎卸载指定 Portfolio

        Args:
            params: 命令参数，包含 portfolio_id

        Returns:
            是否成功
        """
        if not self._engine:
            GLOG.ERROR("[PAPER-WORKER] Engine not initialized, cannot unload")
            return False

        portfolio_id = params.get("portfolio_id")
        if not portfolio_id:
            GLOG.ERROR("[PAPER-WORKER] unload command missing portfolio_id")
            return False

        # 在锁内查找并移除，避免 TOCTOU 竞态
        with self._lock:
            target_portfolio = None
            for portfolio in self._engine.portfolios:
                if portfolio.uuid == portfolio_id:
                    target_portfolio = portfolio
                    break

            if target_portfolio is None:
                GLOG.WARN(
                    f"[PAPER-WORKER] Portfolio {portfolio_id} not found in engine"
                )
                return False

            self._engine.remove_portfolio(target_portfolio)

        GLOG.INFO(f"[PAPER-WORKER] Unloaded portfolio {portfolio_id[:8]}")
        return True

    def _handle_command(self, command: str, params: Dict) -> bool:
        """
        处理 Kafka 控制命令

        Args:
            command: 命令类型
            params: 命令参数

        Returns:
            是否成功处理
        """
        if command == "paper_trading":
            result = self.run_daily_cycle()
            GLOG.INFO(
                f"[PAPER-WORKER] Daily cycle: "
                f"skipped={result.skipped}, advanced={result.advanced}"
            )
            return True
        elif command == "deploy":
            return self._handle_deploy(params)
        elif command == "unload":
            return self._handle_unload(params)
        else:
            GLOG.WARN(f"[PAPER-WORKER] Unknown command: {command}")
            return False

    def start(self) -> None:
        """
        启动 Worker（订阅 Kafka topic）

        连接 Kafka，开始消费控制命令。
        """
        if self._running:
            GLOG.WARN(f"[PAPER-WORKER] {self.worker_id} is already running")
            return

        from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer, GinkgoProducer

        self._running = True

        GLOG.INFO(f"[PAPER-WORKER] {self.worker_id}: Starting...")

        # 初始化 Kafka Consumer
        group_id = f"paper-trading-{self.worker_id}"
        self._consumer = GinkgoConsumer(
            topic=KafkaTopics.CONTROL_COMMANDS,
            group_id=group_id,
            offset="latest",
        )

        # 初始化 Kafka Producer（用于发送响应）
        self._producer = GinkgoProducer()

        GLOG.INFO(f"[PAPER-WORKER] {self.worker_id}: Started")
        GLOG.INFO(
            f"[PAPER-WORKER] {self.worker_id}: Subscribed to "
            f"{KafkaTopics.CONTROL_COMMANDS}"
        )

    def stop(self) -> None:
        """
        停止 Worker（优雅关闭）

        关闭 Kafka 连接，停止引擎。
        """
        if not self._running:
            return

        GLOG.INFO(f"[PAPER-WORKER] {self.worker_id}: Stopping...")
        self._running = False

        # 关闭 Kafka Consumer
        if self._consumer:
            try:
                self._consumer.close()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error closing consumer: {e}")

        # 关闭 Kafka Producer
        if self._producer:
            try:
                self._producer.close()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error closing producer: {e}")

        # 停止引擎
        if self._engine:
            try:
                self._engine.stop()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error stopping engine: {e}")

        GLOG.INFO(f"[PAPER-WORKER] {self.worker_id}: Stopped")
