"""
Engine Builder

回测引擎装配器（BacktestWorker特有模块）

职责：
- 利用EngineAssemblyService装配回测引擎
- 创建BacktestFeeder（加载历史数据）
- 创建SimBroker（模拟交易）
- 装配完整的TimeControlledEventEngine
"""

from typing import Optional, List, Callable
from datetime import datetime
import uuid
import time

from ginkgo.workers.backtest_worker.models import BacktestTask, BacktestConfig, AnalyzerConfig
from ginkgo.trading.engines import TimeControlledEventEngine
from ginkgo.trading.feeders import BacktestFeeder
from ginkgo.trading.brokers.sim_broker import SimBroker
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo import services
from ginkgo.enums import EXECUTION_MODE, SOURCE_TYPES
# GLOG removed
from datetime import datetime as dt


class EngineBuilder:
    """回测引擎装配器"""

    def build(self, task: BacktestTask) -> TimeControlledEventEngine:
        """
        装配TimeControlledEventEngine

        Args:
            task: 回测任务

        Returns:
            装配好的引擎
        """
        print(f"[{task.task_uuid[:8]}] Building backtest engine...")

        # 1. 创建引擎
        engine = TimeControlledEventEngine(
            name=f"BacktestEngine_{task.task_uuid[:8]}",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime.strptime(task.config.start_date, "%Y-%m-%d"),
        )

        # 设置时间边界
        engine.set_start_time(datetime.strptime(task.config.start_date, "%Y-%m-%d"))
        engine.set_end_time(datetime.strptime(task.config.end_date, "%Y-%m-%d"))
        engine.set_run_id(task.task_uuid)

        # 2. 创建并添加Portfolio
        portfolio = self._create_portfolio(task)
        engine.add_portfolio(portfolio)
        print(f"[{task.task_uuid[:8]}] Portfolio created: {portfolio.name}")

        # 3. 创建数据源（Feeder）
        feeder = self._create_feeder(task, portfolio)
        engine.set_feeder(feeder)
        print(f"[{task.task_uuid[:8]}] Feeder created")

        # 4. 创建模拟经纪商
        broker = self._create_broker(task)
        engine.set_broker(broker)
        print(f"[{task.task_uuid[:8]}] Broker created")

        # 5. 设置进度回调
        engine.set_progress_callback(task.config.get('_progress_callback'))

        # 6. 添加分析器（Engine 级别）
        if task.config.analyzers:
            analyzers = self._create_analyzers(task)
            for analyzer in analyzers:
                engine.add_analyzer(analyzer)
            print(f"[{task.task_uuid[:8]}] {len(analyzers)} analyzers added")

        print(f"[{task.task_uuid[:8]}] Engine assembled successfully")

        return engine

    def _create_portfolio(self, task: BacktestTask) -> PortfolioT1Backtest:
        """创建Portfolio（从数据库或使用配置）"""
        # 尝试从数据库加载
        portfolio = self._load_portfolio_from_db(task.portfolio_uuid)
        if portfolio:
            return portfolio

        # 如果数据库中没有，创建默认Portfolio
        print(f"[{task.task_uuid[:8]}] Portfolio {task.portfolio_uuid} not found in DB, creating default")
        return self._create_default_portfolio(task)

    def _load_portfolio_from_db(self, portfolio_uuid: str, max_retries: int = 3, retry_delay: float = 0.5) -> Optional[PortfolioT1Backtest]:
        """
        从数据库加载Portfolio（带重试机制）

        Args:
            portfolio_uuid: Portfolio UUID
            max_retries: 最大重试次数（默认3次）
            retry_delay: 重试间隔秒数（默认0.5秒）

        Returns:
            加载的Portfolio，失败返回None
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                # 使用PortfolioService加载
                portfolio_service = services.data.services.portfolio_service()
                result = portfolio_service.load_portfolio_with_components(
                    portfolio_id=portfolio_uuid
                )

                if result.is_success() and result.data:
                    # 注意：load_portfolio_with_components返回的是PortfolioLive
                    # 回测需要PortfolioT1Backtest，需要转换或重新创建
                    from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
                    if isinstance(result.data, PortfolioLive):
                        # 转换为回测Portfolio
                        return self._convert_to_backtest_portfolio(result.data)
                    return result.data

                # 如果不是最后一次尝试，等待重试
                if attempt < max_retries - 1:
                    print(f"[{portfolio_uuid[:8]}] Portfolio not ready (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    print(f"[{portfolio_uuid[:8]}] Portfolio not found after {max_retries} attempts")

            except Exception as e:
                last_error = e
                print(f"[{portfolio_uuid[:8]}] Attempt {attempt + 1}/{max_retries} failed: {e}")

                # 如果不是最后一次尝试，等待重试
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        # 所有尝试都失败
        if last_error:
            print(f"[{portfolio_uuid[:8]}] Failed to load portfolio after {max_retries} attempts: {last_error}")
        return None

    def _convert_to_backtest_portfolio(self, portfolio_live):
        """将PortfolioLive转换为PortfolioT1Backtest"""
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest

        # 创建回测Portfolio
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

        # 复制Sizer
        if hasattr(portfolio_live, '_sizer'):
            backtest_portfolio.set_sizer(portfolio_live._sizer)

        # 复制风控管理器
        if hasattr(portfolio_live, '_risk_managers'):
            for risk_mgr in portfolio_live._risk_managers:
                backtest_portfolio.add_risk_manager(risk_mgr)

        return backtest_portfolio

    def _create_default_portfolio(self, task: BacktestTask) -> PortfolioT1Backtest:
        """创建默认Portfolio"""
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from ginkgo.trading.strategy.strategies.empty_strategy import EmptyStrategy
        from ginkgo.trading.strategy.sizers.fixed_sizer import FixedSizer
        from ginkgo.trading.strategy.risk_managers.no_risk import NoRiskManagement

        portfolio = PortfolioT1Backtest(
            uuid=task.portfolio_uuid,
            name=task.name or f"Backtest_{task.task_uuid[:8]}"
        )

        # 添加初始资金
        portfolio.add_cash(task.config.initial_cash)

        # 添加空策略（用户需要自己配置策略才有意义）
        portfolio.add_strategy(EmptyStrategy())

        # 添加固定Sizer
        portfolio.set_sizer(FixedSizer(volume=100))

        # 添加无风控
        portfolio.add_risk_manager(NoRiskManagement())

        print(f"[{task.task_uuid[:8]}] Using default empty portfolio - user should configure strategies")

        return portfolio

    def _create_feeder(self, task: BacktestTask, portfolio: PortfolioT1Backtest) -> BacktestFeeder:
        """创建数据源"""
        # 获取Portfolio订阅的股票代码
        codes = self._get_portfolio_codes(portfolio)

        if not codes:
            print(f"[{task.task_uuid[:8]}] No codes in portfolio, using default")
            codes = ["000001.SZ"]  # 默认使用平安银行

        feeder = BacktestFeeder(
            name=f"BacktestFeeder_{task.task_uuid[:8]}"
        )

        # 订阅股票代码
        for code in codes:
            feeder.subscribe(code)

        print(f"[{task.task_uuid[:8]}] Feeder subscribed to {len(codes)} codes: {codes[:3]}...")

        return feeder

    def _get_portfolio_codes(self, portfolio: PortfolioT1Backtest) -> list:
        """获取Portfolio订阅的股票代码"""
        codes = []

        # 从策略的interest map获取
        if hasattr(portfolio, '_strategies'):
            for strategy in portfolio._strategies.values():
                if hasattr(strategy, 'interest_map'):
                    codes.extend(strategy.interest_map.keys())

        # 去重
        return list(set(codes))

    def _create_broker(self, task: BacktestTask) -> SimBroker:
        """创建模拟经纪商"""
        broker = SimBroker(
            initial_cash=task.config.initial_cash,
            commission_rate=task.config.commission_rate,
            slippage_rate=task.config.slippage_rate,
        )

        return broker

    def _create_analyzers(self, task: BacktestTask) -> list:
        """
        创建分析器（Engine 级别）

        分析器通过 Hook 机制接收 Portfolio 的事件：
        - on_bar_closed: 每个周期结束时调用
        - on_order_filled: 订单成交时调用
        - on_position_changed: 持仓变化时调用
        - on_backtest_end: 回测结束时调用
        """
        analyzers = []

        for analyzer_config in task.config.analyzers:
            try:
                analyzer = self._create_analyzer(task, analyzer_config)
                if analyzer:
                    analyzers.append(analyzer)
                    print(f"[{task.task_uuid[:8]}] Analyzer created: {analyzer_config.name} ({analyzer_config.type})")
            except Exception as e:
                print(f"[{task.task_uuid[:8]}] Failed to create analyzer {analyzer_config.name}: {e}")

        return analyzers

    def _create_analyzer(self, task: BacktestTask, config: AnalyzerConfig):
        """
        根据类型创建分析器实例

        支持的分析器类型：
        - SharpeAnalyzer: 夏普比率分析
        - DrawdownAnalyzer: 回撤分析
        - ReturnAnalyzer: 收益率分析
        - PortfolioAnalyzer: 单Portfolio分析
        - ComparisonAnalyzer: Portfolio间对比分析
        """
        analyzer_type = config.type.lower()

        # 创建对应的分析器
        if analyzer_type == "sharpeanalyzer":
            return self._create_sharpe_analyzer(task, config)
        elif analyzer_type == "drawdownanalyzer":
            return self._create_drawdown_analyzer(task, config)
        elif analyzer_type == "returnanalyzer":
            return self._create_return_analyzer(task, config)
        elif analyzer_type == "portfolioanalyzer":
            return self._create_portfolio_analyzer(task, config)
        elif analyzer_type == "comparisonanalyzer":
            return self._create_comparison_analyzer(task, config)
        else:
            print(f"[{task.task_uuid[:8]}] Unknown analyzer type: {config.type}")
            return None

    def _create_sharpe_analyzer(self, task: BacktestTask, config: AnalyzerConfig):
        """创建夏普比率分析器"""
        # TODO: 实现或导入实际的 SharpeAnalyzer
        # from ginkgo.trading.analysis.sharpe_analyzer import SharpeAnalyzer
        # return SharpeAnalyzer(name=config.name, **config.config)

        # 临时返回模拟对象
        return MockAnalyzer(name=config.name, type=config.type, config=config.config)

    def _create_drawdown_analyzer(self, task: BacktestTask, config: AnalyzerConfig):
        """创建回撤分析器"""
        # TODO: 实现或导入实际的 DrawdownAnalyzer
        return MockAnalyzer(name=config.name, type=config.type, config=config.config)

    def _create_return_analyzer(self, task: BacktestTask, config: AnalyzerConfig):
        """创建收益率分析器"""
        # TODO: 实现或导入实际的 ReturnAnalyzer
        return MockAnalyzer(name=config.name, type=config.type, config=config.config)

    def _create_portfolio_analyzer(self, task: BacktestTask, config: AnalyzerConfig):
        """创建单Portfolio分析器"""
        # TODO: 实现或导入实际的 PortfolioAnalyzer
        return MockAnalyzer(name=config.name, type=config.type, config=config.config)

    def _create_comparison_analyzer(self, task: BacktestTask, config: AnalyzerConfig):
        """创建对比分析器"""
        # TODO: 实现或导入实际的 ComparisonAnalyzer
        return MockAnalyzer(name=config.name, type=config.type, config=config.config)


class MockAnalyzer:
    """
    模拟分析器（临时实现，等待 Ginkgo 核心库提供真正的 Analyzer）

    Hook 机制：
    - Engine 在不同阶段调用分析器的 hook 方法
    - 分析器收集数据并计算指标
    - 回测结束时获取分析结果
    """

    def __init__(self, name: str, type: str, config: dict = None):
        self.name = name
        self.type = type
        self.config = config or {}
        self._data = []

    def on_bar_closed(self, portfolio_uuid: str, bar_data, positions):
        """周期结束时的 hook"""
        # 收集数据
        self._data.append({
            'event': 'bar_closed',
            'portfolio_uuid': portfolio_uuid,
            'timestamp': bar_data.datetime if hasattr(bar_data, 'datetime') else None,
        })

    def on_order_filled(self, portfolio_uuid: str, order):
        """订单成交时的 hook"""
        self._data.append({
            'event': 'order_filled',
            'portfolio_uuid': portfolio_uuid,
            'order_id': order.uuid if hasattr(order, 'uuid') else None,
        })

    def on_position_changed(self, portfolio_uuid: str, position):
        """持仓变化时的 hook"""
        self._data.append({
            'event': 'position_changed',
            'portfolio_uuid': portfolio_uuid,
            'code': position.code if hasattr(position, 'code') else None,
        })

    def on_backtest_end(self):
        """回测结束时的 hook"""
        # 计算最终结果
        result = {
            'analyzer': self.name,
            'type': self.type,
            'events_count': len(self._data),
        }
        print(f"[{self.name}] Backtest ended, collected {len(self._data)} events")
        return result

    def get_result(self):
        """获取分析结果"""
        return {
            'name': self.name,
            'type': self.type,
            'config': self.config,
            'events_count': len(self._data),
        }
