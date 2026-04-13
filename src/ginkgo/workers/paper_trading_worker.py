# Upstream: TaskTimer (Kafka控制命令触发每日循环)、CLI deploy/unload/baseline 命令
# Downstream: TimeControlledEventEngine (引擎组装与时间推进)、DeviationChecker (偏差检测)、PortfolioService (状态持久化)
# Role: 纸上交易 Worker，REPLAY模式批量快进历史、LIVE_PAPER模式每日实时推进，含偏差检测与状态持久化


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
from typing import Dict, List, Optional

from ginkgo.enums import (
    EXECUTION_MODE,
    PORTFOLIO_MODE_TYPES,
    PORTFOLIO_RUNSTATE_TYPES,
    MARKET_TYPES,
    FREQUENCY_TYPES,
    SOURCE_TYPES,
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
        self._deviation_detectors: Dict[str, object] = {}  # portfolio_id → LiveDeviationDetector
        self._deviation_checker = None

    @property
    def deviation_checker(self):
        """Lazy-init DeviationChecker to avoid triggering evaluation module imports at load time."""
        if self._deviation_checker is None:
            from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker
            self._deviation_checker = DeviationChecker(
                producer=self._producer,
                source=f"paper-trading-{self.worker_id}",
                takedown_callback=lambda pid: self._handle_unload({"portfolio_id": pid}),
            )
        return self._deviation_checker

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

        # 8. 恢复状态 / 首次初始化（在设置 run_id 和 time provider 之前，需要读取持久化时间）
        portfolio_service = container.portfolio_service()
        persisted_engine_time = None
        for portfolio in engine.portfolios:
            try:
                state_result = portfolio_service.load_persisted_state(portfolio.portfolio_id)
                if state_result.is_success() and state_result.data.get("has_state", False):
                    portfolio.restore_state(state_result.data)
                    GLOG.INFO(
                        f"[PAPER-WORKER] Restored state for portfolio "
                        f"{portfolio.code}: cash={state_result.data['cash']}"
                    )
                    # 提取持久化的引擎时间（取最新的）
                    et = state_result.data.get("engine_current_time")
                    if et:
                        t = datetime.fromisoformat(et)
                        if persisted_engine_time is None or t > persisted_engine_time:
                            persisted_engine_time = t
                else:
                    # 首次运行，从 initial_capital 开始
                    db_rec = next(
                        (p for p in db_portfolios if p.uuid == portfolio.portfolio_id), None
                    )
                    init_capital = float(db_rec.initial_capital) if db_rec else 100000.0
                    portfolio.add_cash(init_capital)
                    GLOG.INFO(
                        f"[PAPER-WORKER] First run for portfolio "
                        f"{portfolio.code}: initial_capital={init_capital}"
                    )
            except Exception as e:
                GLOG.ERROR(
                    f"[PAPER-WORKER] State restore failed for "
                    f"{portfolio.portfolio_id}: {e}"
                )

        # 9. 检测模式并配置 run_id / source_type / time_provider
        real_now = datetime.now()
        is_replay = (
            persisted_engine_time is not None
            and persisted_engine_time.replace(hour=0, minute=0, second=0, microsecond=0).date() < real_now.date()
        )
        session_ts = real_now.strftime("%Y%m%d%H%M%S")

        if is_replay:
            run_id = f"replay-{session_ts}"
            engine.set_run_id(run_id)
            engine.set_source_type(SOURCE_TYPES.PAPER_REPLAY)

            # 用 LogicalTimeProvider 从上次位置开始
            from ginkgo.trading.time.providers import LogicalTimeProvider
            replay_provider = LogicalTimeProvider(
                initial_time=persisted_engine_time,
                end_time=real_now,
            )
            engine._time_provider = replay_provider
            GLOG.INFO(
                f"[PAPER-WORKER] REPLAY mode: engine_time={persisted_engine_time}, "
                f"run_id={run_id}"
            )
        else:
            run_id = f"paper-{session_ts}"
            engine.set_run_id(run_id)
            engine.set_source_type(SOURCE_TYPES.PAPER_LIVE)
            GLOG.INFO(f"[PAPER-WORKER] LIVE_PAPER mode: run_id={run_id}")

        # 10. 启动引擎
        engine.start()

        # 11. 初始化偏差检测器
        self._deviation_detectors = {}
        for portfolio in engine.portfolios:
            try:
                baseline = self._get_baseline(portfolio.portfolio_id)
                if baseline:
                    from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
                    evaluator = BacktestEvaluator()
                    config = self._get_deviation_config(portfolio.portfolio_id)
                    confidence_levels = config.get("confidence_levels", [0.68, 0.95, 0.99])
                    detector = evaluator.create_live_monitor(baseline, confidence_levels)
                    self._deviation_detectors[portfolio.portfolio_id] = detector
                    self.deviation_checker.set_detector(portfolio.portfolio_id, detector)
                    GLOG.INFO(
                        f"[PAPER-WORKER] Deviation detector initialized for {portfolio.code}"
                    )
                else:
                    GLOG.WARN(
                        f"[PAPER-WORKER] No baseline for {portfolio.portfolio_id[:8]}, "
                        f"deviation check disabled"
                    )
            except Exception as e:
                GLOG.WARN(
                    f"[PAPER-WORKER] Failed to init deviation detector for "
                    f"{portfolio.portfolio_id[:8]}: {e}"
                )

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
            if portfolio.state == PORTFOLIO_RUNSTATE_TYPES.OFFLINE:
                continue
            if hasattr(portfolio, "_selectors"):
                for selector in portfolio._selectors:
                    if hasattr(selector, "_interested"):
                        codes.extend(selector._interested)

        # 去重
        return list(set(codes))

    def _get_baseline(self, portfolio_id: str) -> Optional[dict]:
        return self.deviation_checker.get_baseline(portfolio_id)

    def _get_deviation_config(self, portfolio_id: str) -> dict:
        return self.deviation_checker.get_deviation_config(portfolio_id)

    def _run_deviation_check(self) -> None:
        """遍历所有 portfolio 执行偏差检测（点时 + 切片完成）"""
        if not self.deviation_checker._detectors:
            return

        effective_date = self._engine.now if self._engine else datetime.now()

        for portfolio in self._engine.portfolios:
            try:
                records = self._load_today_records(portfolio.portfolio_id, effective_date)

                # Mode A: 每日点时对比
                try:
                    day_index = self._get_day_index(portfolio, effective_date)
                    current_metrics = self._extract_current_metrics(records)
                    if day_index and current_metrics:
                        self.deviation_checker.run_daily_point_check(
                            portfolio.portfolio_id, day_index, current_metrics
                        )
                except Exception as e:
                    GLOG.ERROR(f"[PAPER-WORKER] Daily point check error: {e}")

                # Mode B: 切片完成深度对比
                result = self.deviation_checker.run_deviation_check(
                    portfolio.portfolio_id, records
                )
                if result:
                    config = self._get_deviation_config(portfolio.portfolio_id)
                    self.deviation_checker.handle_deviation_result(
                        portfolio.portfolio_id, result,
                        auto_takedown=config.get("auto_takedown", False),
                    )
            except Exception as e:
                GLOG.ERROR(
                    f"[PAPER-WORKER] Deviation check error for "
                    f"{portfolio.portfolio_id[:8]}: {e}"
                )

    def _get_day_index(self, portfolio, effective_date: datetime = None) -> Optional[int]:
        """计算当前 portfolio 在切片周期内的天数"""
        if effective_date is None:
            effective_date = self._engine.now if self._engine else datetime.now()
        try:
            detector = self.deviation_checker._detectors.get(portfolio.portfolio_id)
            if not detector or not detector.current_slice_data.get("start_date"):
                return None
            start = detector.current_slice_data["start_date"]
            return (effective_date - start).days + 1
        except Exception:
            return None

    def _extract_current_metrics(self, records: Dict) -> Dict[str, float]:
        """从当日记录中提取最新指标值"""
        metrics = {}
        for record in records.get("analyzers", []):
            name = record.get("name", "")
            value = record.get("value", 0)
            metrics[name] = float(value)
        return metrics
    def _load_today_records(self, portfolio_id: str, effective_date: datetime = None) -> Dict:
        """查询指定日期的 analyzer/signal/order records"""
        from ginkgo import services

        if effective_date is None:
            effective_date = self._engine.now if self._engine else datetime.now()

        target_date_str = effective_date.strftime("%Y-%m-%d")
        records = {"analyzers": [], "signals": [], "orders": []}

        try:
            analyzer_service = services.data.services.analyzer_service()
            result = analyzer_service.get_by_run_id(
                run_id=self._engine.run_id if self._engine else "paper",
                portfolio_id=portfolio_id,
            )
            if result.is_success() and result.data:
                for r in result.data:
                    ts = str(getattr(r, 'timestamp', ''))[:10]
                    if ts == target_date_str:
                        records["analyzers"].append({
                            "name": getattr(r, 'name', ''),
                            "value": float(getattr(r, 'value', 0)),
                        })
        except Exception as e:
            GLOG.DEBUG(f"[PAPER-WORKER] Failed to load analyzer records: {e}")

        # 补充 signal 记录
        try:
            signal_crud = services.data.cruds.signal()
            signal_records = signal_crud.find(filters={"portfolio_id": portfolio_id})
            for r in (signal_records or []):
                ts = str(getattr(r, 'timestamp', ''))[:10]
                if ts == target_date_str:
                    records["signals"].append({
                        "code": getattr(r, 'code', ''),
                        "direction": getattr(r, 'direction', 0),
                        "volume": getattr(r, 'volume', 0),
                    })
        except Exception as e:
            GLOG.DEBUG(f"[PAPER-WORKER] Failed to load signal records: {e}")

        # 补充 order 记录
        try:
            order_crud = services.data.cruds.order_record()
            order_records = order_crud.find(filters={"portfolio_id": portfolio_id})
            for r in (order_records or []):
                ts = str(getattr(r, 'timestamp', ''))[:10]
                if ts == target_date_str:
                    records["orders"].append({
                        "code": getattr(r, 'code', ''),
                        "volume": getattr(r, 'volume', 0),
                        "price": float(getattr(r, 'transaction_price', 0)),
                    })
        except Exception as e:
            GLOG.DEBUG(f"[PAPER-WORKER] Failed to load order records: {e}")

        return records
    def _handle_deviation_result(self, portfolio, result: Dict) -> None:
        """处理偏差检测结果：告警 + 可选自动下线"""
        level = result.get("overall_level", "NORMAL")

        if level == "NORMAL":
            GLOG.DEBUG(
                f"[PAPER-WORKER] {portfolio.code}: deviation NORMAL"
            )
            return

        deviations = result.get("deviations", {})
        severity_metrics = [
            f"{k} (z={v['z_score']:.1f})"
            for k, v in deviations.items()
            if v.get("level") != "NORMAL"
        ]

        if level == "MODERATE":
            GLOG.WARN(
                f"[PAPER-WORKER] {portfolio.code}: MODERATE deviation - "
                f"{', '.join(severity_metrics)}"
            )
        elif level == "SEVERE":
            GLOG.ERROR(
                f"[PAPER-WORKER] {portfolio.code}: SEVERE deviation - "
                f"{', '.join(severity_metrics)}"
            )

        # 发送通知
        self._send_deviation_alert(portfolio, level, result)

        # SEVERE + auto_takedown → 卸载
        if level == "SEVERE":
            config = self._get_deviation_config(portfolio.portfolio_id)
            if config.get("auto_takedown", False):
                GLOG.ERROR(
                    f"[PAPER-WORKER] Auto-takedown triggered for "
                    f"{portfolio.portfolio_id[:8]}"
                )
                self._handle_unload({"portfolio_id": portfolio.portfolio_id})

    def _send_deviation_alert(self, portfolio, level: str, result: Dict) -> None:
        """发送偏差告警到 Kafka SYSTEM_EVENTS"""
        if not self._producer:
            return

        deviations = result.get("deviations", {})
        severity_metrics = {
            k: {"level": v.get("level"), "z_score": v.get("z_score", 0)}
            for k, v in deviations.items()
            if v.get("level") != "NORMAL"
        }

        try:
            self._producer.send(
                KafkaTopics.SYSTEM_EVENTS,
                {
                    "source": f"paper-trading-{self.worker_id}",
                    "type": "deviation_alert",
                    "level": level,
                    "portfolio_id": portfolio.portfolio_id,
                    "portfolio_code": portfolio.code,
                    "metrics": severity_metrics,
                    "risk_score": result.get("risk_score", 0),
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Failed to send deviation alert: {e}")

    def _persist_all_portfolios(self) -> None:
        """遍历所有 portfolio 执行 snapshot → persist"""
        if not self._engine:
            return

        from ginkgo import services

        portfolio_service = services.data.container.portfolio_service()
        engine_current_time = self._engine.now

        for portfolio in self._engine.portfolios:
            try:
                state = portfolio.snapshot_state()
                state["engine_current_time"] = engine_current_time.isoformat()
                result = portfolio_service.persist_portfolio_state(portfolio.portfolio_id, state)
                if result.is_success():
                    GLOG.DEBUG(
                        f"[PAPER-WORKER] Persisted state for {portfolio.code}"
                    )
                else:
                    GLOG.ERROR(
                        f"[PAPER-WORKER] Persist failed for {portfolio.code}: "
                        f"{result.error_message}"
                    )
            except Exception as e:
                GLOG.ERROR(
                    f"[PAPER-WORKER] Error persisting {portfolio.code}: {e}"
                )

    def _is_replay_mode(self) -> bool:
        """检查引擎当前是否处于 REPLAY 模式"""
        if not self._engine or not self._engine._time_provider:
            return False
        from ginkgo.trading.time.providers import LogicalTimeProvider
        return isinstance(self._engine._time_provider, LogicalTimeProvider)

    def run_daily_cycle(self) -> DailyCycleResult:
        """
        执行每日循环

        根据引擎时间模式自动分发：
        - REPLAY: 批量快进历史交易日（_run_replay_cycle）
        - LIVE_PAPER: 每日实时推进（_run_live_paper_cycle）

        Returns:
            DailyCycleResult: 执行结果
        """
        if not self._engine:
            GLOG.WARN("[PAPER-WORKER] Engine not initialized, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        if not self._engine.portfolios:
            GLOG.DEBUG("[PAPER-WORKER] No portfolios loaded, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        if self._is_replay_mode():
            return self._run_replay_cycle()
        else:
            return self._run_live_paper_cycle()

    def _run_replay_cycle(self) -> DailyCycleResult:
        """批量快进历史交易日直到追上当前日期"""
        from ginkgo import services

        real_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        trade_day_crud = services.data.cruds.trade_day()
        total_advanced = 0

        while True:
            current_engine_date = self._engine.now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            if current_engine_date.date() >= real_today.date():
                GLOG.INFO(
                    f"[PAPER-WORKER] REPLAY caught up to {real_today.date()}, "
                    f"total_advanced={total_advanced}"
                )
                break

            # 查找下一个交易日
            next_day = trade_day_crud.get_next_trading_day(current_engine_date)
            if next_day is None or next_day.date() >= real_today.date():
                GLOG.INFO(
                    f"[PAPER-WORKER] REPLAY: no more historical trading days"
                )
                break

            # 推进引擎（数据已在 DB 中，无需同步）
            try:
                GLOG.DEBUG(f"[PAPER-WORKER] REPLAY: advancing to {next_day.date()}")
                self._engine.advance_time_to(next_day)
                total_advanced += 1
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] REPLAY advance error at {next_day.date()}: {e}")
                break

        if total_advanced > 0:
            # 偏差检查
            try:
                self._run_deviation_check()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Deviation check error in REPLAY: {e}")

            # 持久化
            self._persist_all_portfolios()

            # 切换到 LIVE_PAPER 模式
            self._transition_to_live()

            return DailyCycleResult(skipped=False, advanced=True)

        # 没有推进过，可能已经追上了
        self._transition_to_live()
        return DailyCycleResult(skipped=False, advanced=False)

    def _transition_to_live(self) -> None:
        """从 REPLAY 切换到 LIVE_PAPER 模式"""
        from ginkgo.trading.time.providers import SystemTimeProvider

        real_provider = SystemTimeProvider()
        self._engine.set_time_provider(real_provider)

        # 更新 run_id 和 source_type
        real_now = datetime.now()
        session_ts = real_now.strftime("%Y%m%d%H%M%S")
        self._engine._run_id = f"paper-{session_ts}"
        self._engine._engine_context.set_run_id(self._engine._run_id)
        self._engine.set_source_type(SOURCE_TYPES.PAPER_LIVE)

        GLOG.INFO(
            f"[PAPER-WORKER] Transitioned to LIVE_PAPER mode, "
            f"run_id={self._engine._run_id}"
        )

    def _run_live_paper_cycle(self) -> DailyCycleResult:
        """
        实时模拟盘每日循环

        流程：
        1. 检查是否为交易日
        2. 收集所有 Portfolio 的 interested codes
        3. 调用 bar_service.sync_range_batch 拉取当日数据
        4. 调用 engine.advance_time_to 推进到下一个交易日

        Returns:
            DailyCycleResult: 执行结果
        """
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

        # 2. 过滤 OFFLINE portfolio
        active_portfolios = [
            p for p in self._engine.portfolios
            if p.state != PORTFOLIO_RUNSTATE_TYPES.OFFLINE
        ]
        if not active_portfolios:
            GLOG.DEBUG("[PAPER-WORKER] All portfolios offline, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        for p in self._engine.portfolios:
            if p.state == PORTFOLIO_RUNSTATE_TYPES.OFFLINE:
                GLOG.DEBUG(f"[PAPER-WORKER] Skipping offline portfolio {p.portfolio_id[:8]}")

        # 3. 收集 interested codes
        codes = self._get_interested_codes()
        if not codes:
            GLOG.WARN("[PAPER-WORKER] No interested codes, skipping daily cycle")
            return DailyCycleResult(skipped=True, advanced=False)

        # 4. 同步拉取当日数据
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

        # 5. 推进引擎到下一个交易日
        try:
            next_day = trade_day_crud.get_next_trading_day(today)
            if next_day is None:
                GLOG.WARN(f"[PAPER-WORKER] No next trading day found after {today.date()}")
                return DailyCycleResult(skipped=True, advanced=False)

            GLOG.INFO(f"[PAPER-WORKER] Advancing engine to {next_day.date()}")
            self._engine.advance_time_to(next_day)

            # 偏差检查
            try:
                self._run_deviation_check()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Deviation check error: {e}")

            # 持久化所有 portfolio 状态
            self._persist_all_portfolios()

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
        启动 Worker（订阅 Kafka topic，进入消费循环）

        连接 Kafka，消费控制命令直到收到停止信号。
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

        # 进入消费循环
        self._consume_loop()

    def _consume_loop(self) -> None:
        """
        Kafka 消费主循环

        持续从 CONTROL_COMMANDS topic 消费消息并分发处理。
        """
        while self._running:
            try:
                messages = self._consumer.consumer.poll(timeout_ms=2000)

                if not messages:
                    continue

                for tp, records in messages.items():
                    for message in records:
                        if not self._running:
                            break

                        try:
                            event_data = message.value
                            command = event_data.get("command", "")
                            params = event_data.get("params", {})

                            GLOG.INFO(
                                f"[PAPER-WORKER] Received command: {command}, "
                                f"params: {params}"
                            )

                            success = self._handle_command(command, params)

                            # 发送处理结果
                            self._send_response(command, success, params)

                            # 成功处理后提交 offset
                            try:
                                self._consumer.commit()
                            except Exception as e:
                                GLOG.ERROR(
                                    f"[PAPER-WORKER] Failed to commit offset: {e}"
                                )

                        except Exception as e:
                            GLOG.ERROR(
                                f"[PAPER-WORKER] Error processing message: {e}"
                            )

            except Exception as e:
                if self._running:
                    GLOG.ERROR(f"[PAPER-WORKER] Error in consume loop: {e}")

    def _send_response(self, command: str, success: bool, params: Dict) -> None:
        """
        发送命令处理结果到 Kafka

        Args:
            command: 原始命令
            success: 是否处理成功
            params: 原始参数
        """
        if not self._producer:
            return

        try:
            self._producer.send(
                KafkaTopics.SYSTEM_EVENTS,
                {
                    "source": f"paper-trading-{self.worker_id}",
                    "command": command,
                    "success": success,
                    "params": params,
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Failed to send response: {e}")

    def stop(self) -> None:
        """
        停止 Worker（优雅关闭）

        设置停止标志，关闭 Kafka 连接，停止引擎。
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

        # 关闭 Kafka Producer（flush 确保消息发出）
        if self._producer:
            try:
                self._producer.flush()
                self._producer.close()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error closing producer: {e}")

        # 停止引擎前持久化所有 portfolio 状态
        if self._engine:
            try:
                self._persist_all_portfolios()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error persisting state on stop: {e}")

        # 停止引擎
        if self._engine:
            try:
                self._engine.stop()
            except Exception as e:
                GLOG.ERROR(f"[PAPER-WORKER] Error stopping engine: {e}")

        GLOG.INFO(f"[PAPER-WORKER] {self.worker_id}: Stopped")
