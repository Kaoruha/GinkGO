# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 从 BacktestTask 构建回测引擎


"""
TaskEngineBuilder - 从 BacktestTask 构建引擎

从 engine_assembly_service.py 提取，负责：
- build_engine_from_task: 公共 API
- Portfolio 创建/加载/转换
- Feeder 创建
- Gateway 创建
"""

from typing import Optional

import datetime

from ginkgo.libs import GLOG


class TaskEngineBuilder:
    """
    从 BacktestTask 构建回测引擎

    此方法从 EngineBuilder 迁移而来，用于统一引擎装配逻辑。
    """

    def __init__(self, file_service=None, portfolio_service=None, engine_service=None, logger=None):
        """
        初始化 TaskEngineBuilder

        Args:
            file_service: 文件服务（保留接口，当前未直接使用）
            portfolio_service: Portfolio 服务（保留接口，当前未直接使用）
            engine_service: 引擎服务（保留接口，当前未直接使用）
            logger: 日志记录器
        """
        self._file_service = file_service
        self._portfolio_service = portfolio_service
        self._engine_service = engine_service
        self._logger = logger or GLOG

    def build_engine_from_task(self, task) -> "TimeControlledEventEngine":
        """
        从 BacktestTask 构建回测引擎

        Args:
            task: BacktestTask 实例，包含回测配置

        Returns:
            装配好的 TimeControlledEventEngine
        """
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.enums import EXECUTION_MODE

        self._logger.INFO(f"[{task.task_uuid[:8]}] Building backtest engine from task...")

        # 1. 创建引擎
        engine = TimeControlledEventEngine(
            name=f"BacktestEngine_{task.task_uuid[:8]}",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.datetime.strptime(task.config.start_date, "%Y-%m-%d"),
            timer_interval=0.01,  # 提高性能
        )

        # 设置时间边界和 run_id
        engine.set_start_time(datetime.datetime.strptime(task.config.start_date, "%Y-%m-%d"))
        engine.set_end_time(datetime.datetime.strptime(task.config.end_date, "%Y-%m-%d"))
        engine.set_run_id(task.task_uuid)

        # 2. 创建并添加 Portfolio
        portfolio = self._create_portfolio_from_task(task)
        engine.add_portfolio(portfolio)
        self._logger.INFO(f"[{task.task_uuid[:8]}] Portfolio created: {portfolio.name}")

        # 3. 创建数据源（Feeder）
        feeder = self._create_feeder_from_task(task, portfolio)
        engine.set_data_feeder(feeder)
        self._logger.INFO(f"[{task.task_uuid[:8]}] Feeder created")

        # 4. 创建模拟经纪商和 Gateway
        gateway = self._create_gateway_from_task(task)
        engine.bind_router(gateway)
        self._logger.INFO(f"[{task.task_uuid[:8]}] Gateway created")

        # 5. 设置进度回调
        if hasattr(task.config, 'get') and task.config.get('_progress_callback'):
            engine.set_progress_callback(task.config.get('_progress_callback'))

        # 6. 注册 Feeder 事件
        from ginkgo.enums import EVENT_TYPES
        engine.register(EVENT_TYPES.INTERESTUPDATE, feeder.on_interest_update)

        self._logger.INFO(f"[{task.task_uuid[:8]}] Engine assembled successfully")
        return engine

    def _create_portfolio_from_task(self, task):
        """从 BacktestTask 创建 Portfolio"""
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from decimal import Decimal

        # 尝试从数据库加载 Portfolio
        portfolio = self._load_portfolio_from_task(task)
        if portfolio:
            return portfolio

        # 如果数据库中没有，创建默认 Portfolio
        self._logger.WARN(f"[{task.task_uuid[:8]}] Portfolio {task.portfolio_uuid} not found in DB, creating default")
        return self._create_default_portfolio_from_task(task)

    def _load_portfolio_from_task(self, task, max_retries: int = 3, retry_delay: float = 0.5):
        """从数据库加载 Portfolio（带重试机制）"""
        import time
        from ginkgo import services

        last_error = None
        for attempt in range(max_retries):
            try:
                portfolio_service = services.data.services.portfolio_service()
                result = portfolio_service.load_portfolio_with_components(
                    portfolio_id=task.portfolio_uuid
                )

                if result.is_success() and result.data:
                    from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
                    if isinstance(result.data, PortfolioLive):
                        return self._convert_to_backtest_portfolio(result.data, task)
                    return result.data

                if attempt < max_retries - 1:
                    self._logger.DEBUG(f"[{task.portfolio_uuid[:8]}] Portfolio not ready (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay)
                else:
                    self._logger.WARN(f"[{task.portfolio_uuid[:8]}] Portfolio not found after {max_retries} attempts")

            except Exception as e:
                last_error = e
                self._logger.WARN(f"[{task.portfolio_uuid[:8]}] Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        if last_error:
            self._logger.ERROR(f"[{task.portfolio_uuid[:8]}] Failed to load portfolio: {last_error}")
        return None

    def _convert_to_backtest_portfolio(self, portfolio_live, task):
        """将 PortfolioLive 转换为 PortfolioT1Backtest"""
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest

        backtest_portfolio = PortfolioT1Backtest(
            uuid=portfolio_live.uuid,
            name=portfolio_live.name
        )

        # 复制现金
        backtest_portfolio.add_cash(portfolio_live.get_cash())

        # 复制策略
        if hasattr(portfolio_live, '_strategies'):
            for strategy in portfolio_live._strategies.values():
                backtest_portfolio.add_strategy(strategy)

        # 复制 Sizer
        if hasattr(portfolio_live, '_sizer'):
            backtest_portfolio.bind_sizer(portfolio_live._sizer)

        # 复制风控管理器
        if hasattr(portfolio_live, '_risk_managers'):
            for risk_mgr in portfolio_live._risk_managers:
                backtest_portfolio.add_risk_manager(risk_mgr)

        return backtest_portfolio

    def _create_default_portfolio_from_task(self, task):
        """创建默认 Portfolio"""
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from ginkgo.trading.strategies.empty_strategy import EmptyStrategy
        from ginkgo.trading.sizers.fixed_sizer import FixedSizer
        from ginkgo.trading.risk_managers.no_risk import NoRiskManagement
        from decimal import Decimal

        portfolio = PortfolioT1Backtest(
            uuid=task.portfolio_uuid,
            name=task.name or f"Backtest_{task.task_uuid[:8]}"
        )

        # 添加初始资金
        portfolio.add_cash(Decimal(str(task.config.initial_cash)))

        # 添加空策略（用户需要自己配置策略才有意义）
        portfolio.add_strategy(EmptyStrategy())

        # 添加固定 Sizer
        portfolio.bind_sizer(FixedSizer(volume=100))

        # 添加无风控
        portfolio.add_risk_manager(NoRiskManagement())

        self._logger.WARN(f"[{task.task_uuid[:8]}] Using default empty portfolio - user should configure strategies")
        return portfolio

    def _create_feeder_from_task(self, task, portfolio):
        """从 BacktestTask 创建数据源"""
        from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder

        # 获取 Portfolio 订阅的股票代码
        codes = self._get_portfolio_codes_from_portfolio(portfolio)

        if not codes:
            self._logger.WARN(f"[{task.task_uuid[:8]}] No codes in portfolio, using default")
            codes = ["000001.SZ"]  # 默认使用平安银行

        feeder = BacktestFeeder(name=f"BacktestFeeder_{task.task_uuid[:8]}")

        # 订阅股票代码
        for code in codes:
            feeder.subscribe(code)

        self._logger.INFO(f"[{task.task_uuid[:8]}] Feeder subscribed to {len(codes)} codes: {codes[:3]}...")
        return feeder

    def _get_portfolio_codes_from_portfolio(self, portfolio) -> list:
        """获取 Portfolio 订阅的股票代码"""
        codes = []

        # 从策略的 interest map 获取
        if hasattr(portfolio, '_strategies'):
            for strategy in portfolio._strategies.values():
                if hasattr(strategy, 'interest_map'):
                    codes.extend(strategy.interest_map.keys())
                elif hasattr(strategy, '_interested'):
                    codes.extend(strategy._interested)

        # 从 Selector 获取
        if hasattr(portfolio, '_selector'):
            selector = portfolio._selector
            if hasattr(selector, '_interested'):
                codes.extend(selector._interested)

        # 去重
        return list(set(codes))

    def _create_gateway_from_task(self, task):
        """从 BacktestTask 创建 TradeGateway"""
        from ginkgo.trading.gateway.trade_gateway import TradeGateway
        from ginkgo.trading.brokers.sim_broker import SimBroker
        from ginkgo.enums import ATTITUDE_TYPES

        broker = SimBroker(
            name="SimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=task.config.commission_rate,
            commission_min=5,
        )

        gateway = TradeGateway(name="UnifiedTradeGateway", brokers=[broker])
        return gateway
