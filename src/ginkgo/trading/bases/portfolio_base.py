# Upstream: Backtest Engines (管理Portfolio实例)、Strategies/RiskManagers/Selectors (添加到Portfolio)
# Downstream: TimeMixin/ContextMixin/EngineBindableMixin/NamedMixin/LoggableMixin (5个Mixin提供时间/上下文/引擎绑定/命名/日志能力)、Base/ABC (基础类和抽象基类)
# Role: PortfolioBase投资组合抽象基类继承5个Mixin和Base/ABC提供7维能力管理策略/风控/选择器/持仓/订单/资金账户






"""
投资组合组件基类

组合完整的管理能力，为所有投资组合组件提供基础功能
"""

import uuid
import datetime
import sys
from rich.console import Console
from typing import TYPE_CHECKING, List, Dict, Optional
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import timedelta

if TYPE_CHECKING:
    from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
    from ginkgo.trading.strategies import StrategyBase
    from ginkgo.trading.signal_processing.batch_processor import TimeWindowBatchProcessor
    from ginkgo.trading.engines.base_engine import BaseEngine
else:
    # 运行时导入，避免循环依赖
    from ginkgo.trading.engines.base_engine import BaseEngine

from ginkgo.entities.base import Base
from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import ContextMixin
from ginkgo.entities.mixins import EngineBindableMixin
from ginkgo.entities.mixins import NamedMixin
from ginkgo.trading.bases.selector_base import SelectorBase
from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck,
    EventOrderPartiallyFilled,
    EventOrderRejected,
    EventOrderExpired,
    EventOrderCancelAck,
)
from ginkgo.entities import Position
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, RECORDSTAGE_TYPES, SOURCE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES, DEFAULT_ANALYZER_SET
from ginkgo.libs import GCONF, GLOG, to_decimal


console = Console()


class PortfolioBase(TimeMixin, ContextMixin, EngineBindableMixin,
                   NamedMixin, Base, ABC):
    """
    投资组合组件基类

    组合完整的管理能力，为所有投资组合组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    # 内置默认分析器配置（字符串列表）
    BUILTIN_DEFAULT_ANALYZERS = {
        DEFAULT_ANALYZER_SET.MINIMAL: ['net_value', 'profit'],
        DEFAULT_ANALYZER_SET.STANDARD: ['net_value', 'profit', 'max_drawdown', 'sharpe_ratio', 'win_rate'],
        DEFAULT_ANALYZER_SET.FULL: ['net_value', 'profit', 'max_drawdown', 'sharpe_ratio',
                                     'win_rate', 'volatility', 'sortino_ratio', 'calmar_ratio',
                                     'hold_pct', 'signal_count'],
    }

    def __init__(
        self,
        name: str = "Portfolio",
        use_default_analyzers: bool = True,
        default_analyzer_set: DEFAULT_ANALYZER_SET = DEFAULT_ANALYZER_SET.STANDARD,
        *args,
        **kwargs,
    ) -> None:
        """
        初始化投资组合基类

        Args:
            name: 投资组合名称
            use_default_analyzers: 是否使用默认分析器
            default_analyzer_set: 默认分析器集合类型
            **kwargs: 传递给父类的参数
        """
        super().__init__(name=name, *args, **kwargs)

        # 标记为 Portfolio 组件（用于 ContextMixin 识别）
        self._is_portfolio = True

        # Portfolio运行模式和状态
        self._mode: PORTFOLIO_MODE_TYPES = PORTFOLIO_MODE_TYPES.BACKTEST
        self._state: PORTFOLIO_RUNSTATE_TYPES = PORTFOLIO_RUNSTATE_TYPES.INITIALIZED

        # Portfolio核心业务属性
        self._cash: Decimal = Decimal("0")
        self._worth: Decimal = self._cash
        self._profit: Decimal = Decimal("0")
        self._frozen: Decimal = Decimal("0")
        self._fee = Decimal("0")
        self._positions: dict = {}
        self._strategies: List["StrategyBase"] = []
        self._sizer: SizerBase = None
        self._risk_managers: List[RiskBase] = []
        self._selectors = []  # 支持多个selector
        self._analyzers: Dict[str, "BaseAnalyzer"] = {}
        self._analyzer_activate_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
        self._analyzer_record_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
        # 注意：不要覆盖_context_mixin提供的_engine_id，它由ContextMixin管理
        self._interested: List = []
        self._engine_put = None

        # 批处理相关属性
        self._batch_processor: Optional["TimeWindowBatchProcessor"] = None
        self._batch_processing_enabled = False
        self._original_on_signal = None  # 保存原始信号处理方法以便回退

        # 默认分析器配置
        self._use_default_analyzers = use_default_analyzers
        self._default_analyzer_set = default_analyzer_set

        # 初始化默认分析器
        if use_default_analyzers:
            self._init_default_analyzers()

    def _init_default_analyzers(self) -> None:
        """
        初始化内置默认分析器（直接导入，不通过工厂）

        根据配置的分析器集合，自动添加对应的默认分析器到Portfolio。
        用户手动添加的同名分析器不会被覆盖。
        """
        # 延迟导入，避免循环依赖
        from ginkgo.trading.analysis.analyzers.net_value import NetValue
        from ginkgo.trading.analysis.analyzers.profit import Profit
        from ginkgo.trading.analysis.analyzers.max_drawdown import MaxDrawdown
        from ginkgo.trading.analysis.analyzers.sharpe_ratio import SharpeRatio
        from ginkgo.trading.analysis.analyzers.win_rate import WinRate
        from ginkgo.trading.analysis.analyzers.volatility import Volatility
        from ginkgo.trading.analysis.analyzers.sortino_ratio import SortinoRatio
        from ginkgo.trading.analysis.analyzers.calmar_ratio import CalmarRatio
        from ginkgo.trading.analysis.analyzers.hold_pct import HoldPCT
        from ginkgo.trading.analysis.analyzers.signal_count import SignalCount

        # 内置分析器映射
        builtin_map = {
            'net_value': NetValue,
            'profit': Profit,
            'max_drawdown': MaxDrawdown,
            'sharpe_ratio': SharpeRatio,
            'win_rate': WinRate,
            'volatility': Volatility,
            'sortino_ratio': SortinoRatio,
            'calmar_ratio': CalmarRatio,
            'hold_pct': HoldPCT,
            'signal_count': SignalCount,
        }

        analyzer_names = self.BUILTIN_DEFAULT_ANALYZERS.get(self._default_analyzer_set, [])
        added_count = 0

        for name in analyzer_names:
            # 跳过已存在的分析器（用户手动添加的优先）
            if name in self._analyzers:
                GLOG.DEBUG(f"Default analyzer '{name}' already exists, skipping")
                continue

            if name in builtin_map:
                try:
                    analyzer_class = builtin_map[name]
                    analyzer = analyzer_class(name=name)
                    self.add_analyzer(analyzer)
                    added_count += 1
                    GLOG.DEBUG(f"Added default analyzer: {name}")
                except Exception as e:
                    GLOG.ERROR(f"Failed to add default analyzer '{name}': {e}")

        GLOG.INFO(f"Initialized {added_count} default analyzers from set {self._default_analyzer_set.name}")

    # ========== 基础属性和方法 ==========

    def set_event_publisher(self, publisher) -> None:
        """
        Inject an event publisher (typically engine.put) for pushing events back to engine.
        """
        self._engine_put = publisher

    def bind_data_feeder(self, feeder, *args, **kwargs):
        """传播 data_feeder 给所有子组件"""
        if self._sizer is not None:
            self._sizer.bind_data_feeder(feeder)
        for selector in self._selectors:
            selector.bind_data_feeder(feeder)
        for i in self._strategies:
            i.bind_data_feeder(feeder)
        # 也传播给 risk_managers
        for risk in self.risk_managers:
            if hasattr(risk, 'bind_data_feeder'):
                risk.bind_data_feeder(feeder)

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            GLOG.ERROR(f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def portfolio_id(self) -> str:
        return self._uuid

    def set_portfolio_id(self, value: str) -> str:
        """
        Change Portfolio ID
        Args:
            value(str): new portfolio id
        Return:
            New portfolio ID.
        """
        self._uuid = value
        return self.uuid

    def set_portfolio_name(self, value: str) -> None:
        self.set_name(value)

    @property
    def analyzers(self) -> Dict:
        return self._analyzers

    @property
    def mode(self) -> PORTFOLIO_MODE_TYPES:
        """
        投资组合运行模式

        Returns:
            PORTFOLIO_MODE_TYPES: BACKTEST(回测), PAPER(模拟盘), LIVE(实盘)
        """
        return self._mode

    @mode.setter
    def mode(self, value: PORTFOLIO_MODE_TYPES) -> None:
        """
        设置投资组合运行模式

        Args:
            value: PORTFOLIO_MODE_TYPES 枚举值
        """
        if isinstance(value, PORTFOLIO_MODE_TYPES):
            self._mode = value
        elif isinstance(value, int):
            self._mode = PORTFOLIO_MODE_TYPES.from_int(value) or PORTFOLIO_MODE_TYPES.BACKTEST
        else:
            GLOG.WARN(f"Invalid mode value: {value}, using BACKTEST as default")
            self._mode = PORTFOLIO_MODE_TYPES.BACKTEST

    @property
    def state(self) -> PORTFOLIO_RUNSTATE_TYPES:
        """
        投资组合运行状态

        Returns:
            PORTFOLIO_RUNSTATE_TYPES: INITIALIZED, RUNNING, PAUSED, STOPPING, STOPPED, RELOADING, MIGRATING
        """
        return self._state

    @state.setter
    def state(self, value: PORTFOLIO_RUNSTATE_TYPES) -> None:
        """
        设置投资组合运行状态

        Args:
            value: PORTFOLIO_RUNSTATE_TYPES 枚举值
        """
        if isinstance(value, PORTFOLIO_RUNSTATE_TYPES):
            self._state = value
        elif isinstance(value, int):
            self._state = PORTFOLIO_RUNSTATE_TYPES.from_int(value) or PORTFOLIO_RUNSTATE_TYPES.INITIALIZED
        else:
            GLOG.WARN(f"Invalid state value: {value}, using INITIALIZED as default")
            self._state = PORTFOLIO_RUNSTATE_TYPES.INITIALIZED

    @property
    def profit(self) -> Decimal:
        return round(self._profit, 2)

    def update_profit(self) -> None:
        """
        Update the PROFIT of Portfolio
        Args:
            None
        Return:
            None
        """
        profit_sum = 0
        for key in self.positions:
            profit_sum += self.positions[key].total_pnl
        self._profit = profit_sum

    @property
    def worth(self) -> Decimal:
        return self._worth

    def update_worth(self) -> None:
        """
        Update the WORTH of Portfolio.
            Part1: Cash
            Part2: Frozen Money
            Part3: Total value of all Positions
        Args:
            None
        Return:
            None
        """
        self._worth = self.cash + self.frozen
        for key in self.positions:
            self._worth += self.positions[key].worth

    @property
    def cash(self) -> Decimal:
        """
        return the cash of portfolio
        """
        return self._cash

    @property
    def frozen(self) -> Decimal:
        """
        return the money frozen of portfolio
        """
        return self._frozen

    @property
    def fee(self) -> Decimal:
        """
        return the total fee
        """
        return self._fee

    def add_cash(self, money: any) -> Decimal:
        """
        Add Found.
        Args:
            money(any): Income money.
        Returns:
            current cash
        """
        money = to_decimal(money)
        old_cash = self._cash
        if money <= 0:
            GLOG.ERROR(f"The money should not under 0. {money} is illegal.")
        else:
            self._cash += money
            GLOG.INFO(f"💰 [CASH MONITOR] add_cash: +{money} (old: {old_cash} -> new: {self._cash}) [CALLER: ADD_CASH]")
            self.update_worth()
        return self.cash

    def add_fee(self, fee: any) -> Decimal:
        """
        Add fee.
        Args:
            fee(any): number of fee
        Returns:
            total fee of this portfolio
        """
        fee = to_decimal(fee)
        if fee < 0:
            GLOG.ERROR(f"The fee should not under 0. {fee} is illegal.")
        else:
            GLOG.DEBUG(f"Add FEE {fee}")
            self._fee += fee
        return self.fee

    @property
    def interested(self) -> List:
        """
        Interested Codes.
        """
        return self._interested

    @property
    def positions(self) -> Dict[str, Position]:
        """
        Return Positions[dict] of portfolio
        """
        return self._positions

    @property
    def strategies(self) -> List:
        """
        Return Strategies[List] of portfolio
        """
        return self._strategies

    @property
    def risk_managers(self) -> List[RiskBase]:
        return self._risk_managers

    @property
    def selectors(self):
        """
        Target selectors (支持多个)
        """
        return self._selectors

    @property
    def sizer(self) -> SizerBase:
        return self._sizer

    def is_all_set(self) -> bool:
        """
        Check if all parts set
        """
        if self.sizer is None:
            GLOG.ERROR(f"Portfolio Sizer not set. Can not handle the signal. Please set the SIZER first.")
            return False

        if not self._selectors:
            GLOG.ERROR(f"Portfolio Selector not set. Can not pick the code. Please set the SELECTOR first.")
            return False

        if len(self.risk_managers) == 0:
            GLOG.WARN(f"Portfolio RiskManager not set. Backtest will go on without Risk Control.")

        if len(self.strategies) == 0:
            GLOG.ERROR(f"No strategy register. No signal will come.")
            return False

        return True

    def is_event_from_future(self, event) -> bool:
        """检查事件是否来自未来"""
        try:
            # 尝试获取事件时间戳，优先使用business_timestamp（价格数据时间）
            event_time = None
            if hasattr(event, 'business_timestamp'):
                event_time = event.business_timestamp
            elif hasattr(event, 'timestamp'):
                event_time = event.timestamp

            if event_time is None:
                return False

            # 确保时间戳有时区信息
            if event_time.tzinfo is None:
                from datetime import timezone
                event_time = event_time.replace(tzinfo=timezone.utc)

            current_time = self.get_time_provider().now()

            # 如果事件时间晚于当前时间，则来自未来
            return event_time > current_time

        except Exception as e:
            GLOG.ERROR(f"Error checking event time: {e}")
            return False

    # ========== 绑定方法 ==========

    def bind_selector(self, selector: SelectorBase) -> None:
        """
        Bind selector to portfolio, and bind portfolio itself to selector.
        支持添加多个selector到列表中。
        """
        if not isinstance(selector, SelectorBase):
            GLOG.ERROR(f"Selector bind only support Selector, {type(selector)} {selector} is not supported.")
            return
        self._selectors.append(selector)
        # 绑定portfolio引用，让selector可以直接从portfolio获取ID
        selector.bind_portfolio(self)
        # 如果portfolio已绑定引擎，也绑定引擎到selector
        if self._bound_engine is not None:
            selector.bind_engine(self._bound_engine)
        # 如果portfolio有TimeProvider，也设置给selector
        if self._time_provider is not None:
            selector.set_time_provider(self._time_provider)

    def bind_engine(self, engine: BaseEngine):
        """
        Bind engine to portfolio and propagate to all bound components.
        """
        if not isinstance(engine, BaseEngine):
            raise TypeError(f"Expected BaseEngine, got {type(engine)}")

        # 绑定引擎到portfolio自身 - ContextMixin.bind_engine在MRO中
        super().bind_engine(engine)

        # 如果引擎有TimeProvider，设置给Portfolio
        if engine._time_provider is not None:
            self.set_time_provider(engine._time_provider)

        # 通过统一的ContextMixin同步给所有已绑定的组件
        # 策略组件（支持多个）- 先 bind_portfolio 设置 _context，后 bind_engine
        for strategy in self._strategies:
            strategy.bind_portfolio(self)     # 先绑定 Portfolio（设置 PortfolioContext）
            strategy.bind_engine(engine)      # 后绑定 Engine（保留引擎引用，不覆盖 context）

        # Sizer组件（单个）- 需要engine_id创建Order
        if self._sizer is not None:
            self._sizer.bind_portfolio(self)  # 先绑定 Portfolio（设置 PortfolioContext）
            self._sizer.bind_engine(engine)   # 后绑定 Engine（保留引擎引用，不覆盖 context）

        # Selector组件（支持多个）
        for selector in self._selectors:
            selector.bind_portfolio(self)     # 先绑定 Portfolio（设置 PortfolioContext）
            selector.bind_engine(engine)      # 后绑定 Engine（保留引擎引用，不覆盖 context）

        # 分析器组件（支持多个）- 需要更新 context 引用
        # 当 portfolio 绑定到 engine 后，analyzer 需要重新绑定以获取正确的 engine_context
        for analyzer in self._analyzers.values():
            analyzer.bind_portfolio(self)    # 重新绑定 Portfolio（更新 PortfolioContext）
            analyzer.bind_engine(engine)     # 绑定 Engine（设置引擎引用）

    def set_time_provider(self, time_provider) -> None:
        """
        重写时间提供者设置，自动传递给所有已绑定的组件
        """
        super().set_time_provider(time_provider)
        # 传递时间提供者给已绑定的sizer
        if self._sizer is not None:
            self._sizer.set_time_provider(time_provider)
        # 传递时间提供者给已绑定的selectors
        for selector in self._selectors:
            selector.set_time_provider(time_provider)
        # 传递时间提供者给已绑定的strategies
        for strategy in self._strategies:
            strategy.set_time_provider(time_provider)
        # 传递时间提供者给已绑定的analyzers
        for analyzer in self._analyzers.values():
            analyzer.set_time_provider(time_provider)

    def add_risk_manager(self, risk: RiskBase) -> None:
        """
        Add risk manager to portfolio.
        """
        if not isinstance(risk, RiskBase):
            GLOG.ERROR(f"Risk manager only support RiskBase, {type(risk)} {risk} is not supported.")
            return
        if risk not in self.risk_managers:
            self.risk_managers.append(risk)

    def add_strategy(self, strategy: "StrategyBase") -> None:
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            # 绑定portfolio引用给strategy
            strategy.bind_portfolio(self)
            # 如果portfolio已绑定引擎，也绑定引擎到strategy
            if self._bound_engine is not None:
                strategy.bind_engine(self._bound_engine)
            # 如果portfolio有TimeProvider，也设置给strategy
            if self._time_provider is not None:
                strategy.set_time_provider(self._time_provider)

    def add_position(self, position: Position) -> None:
        code = position.code
        if code in self.positions.keys():
            self._positions[code].deal(DIRECTION_TYPES.LONG, position.cost, position.volume)
        else:
            self._positions[code] = position

    def bind_sizer(self, sizer: SizerBase) -> None:
        """
        Bind sizer to portfolio. And bind the portfolio itself to sizer.
        """
        if not isinstance(sizer, SizerBase):
            GLOG.ERROR(f"Sizer bind only support Sizer, {type(sizer)} {sizer} is not supported.")
            return
        self._sizer = sizer
        # 绑定portfolio引用，让sizer可以直接从portfolio获取ID
        sizer.bind_portfolio(self)
        # 如果portfolio已绑定engine，也绑定给sizer
        if self._bound_engine is not None:
            sizer.bind_engine(self._bound_engine)
        # 传递时间提供者给sizer
        if self.get_time_provider() is not None:
            sizer.set_time_provider(self.get_time_provider())

    def freeze(self, money: any) -> bool:
        """
        Freeze the capital.
        """
        money = to_decimal(money)
        if money > self.cash:
            GLOG.WARN(f"We cant freeze {money}, we only have {self.cash}.")
            return False
        GLOG.DEBUG(f"TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
        console.print(f":ice: TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
        self._frozen += money
        self._cash -= money
        GLOG.INFO(f"💰 [CASH MONITOR] freeze_cash: -{money} (old: {self._cash + money} -> new: {self._cash}, frozen: {self._frozen})")
        GLOG.DEBUG(f"DONE FREEZE ${money}. CURRENFROZEN: ${self._frozen}. CURRENTCASH: ${self.cash} ")
        console.print(f":money_bag: DONE FREEZE ${money}. CURRENFROZEN: ${self._frozen}. CURRENTCASH: ${self.cash} ")
        return True

    def unfreeze(self, money: any) -> Decimal:
        """
        Unfreeze the money.
        """
        money = to_decimal(money)
        if money > self.frozen:
            if money - self.frozen > GCONF.EPSILON:
                GLOG.ERROR(f"Cant unfreeze ${money}, the max unfreeze is only ${self.frozen}")
                console.print(f":prohibited: Cant unfreeze ${money}, the max unfreeze is only ${self.frozen}")
                return
            else:
                old_cash = self._cash
                old_frozen = self._frozen
                self._cash += self._frozen  # 恢复全部frozen的cash
                self._frozen = 0
                GLOG.INFO(f"💰 [CASH MONITOR] unfreeze: +{old_frozen} (old: {old_cash} -> new: {self._cash}, frozen: {old_frozen} -> {self._frozen})")
                GLOG.DEBUG(f"DONE UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
        else:
            GLOG.DEBUG(f"TRYING UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
            old_cash = self._cash
            old_frozen = self._frozen
            self._frozen -= money
            self._cash += money  # 🚨 关键修复：unfreeze时需要恢复cash！
            GLOG.INFO(f"💰 [CASH MONITOR] unfreeze: +{money} (old: {old_cash} -> new: {self._cash}, frozen: {old_frozen} -> {self._frozen})")
            GLOG.DEBUG(f"DONE UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
        return self.frozen

    def deduct_from_frozen(self, cost: any, unfreeze_remain: any = None) -> Decimal:
        """
        Deduct transaction cost from frozen funds without returning to cash.
        Only unfreeze the remaining amount if specified.

        Args:
            cost: Transaction cost to deduct from frozen funds
            unfreeze_remain: Amount to unfreeze back to cash (optional)

        Returns:
            Remaining frozen balance

        Example:
            # Partially filled order: deduct cost and unfreeze remaining amount
            portfolio.deduct_from_frozen(transaction_cost=1000, unfreeze_remain=500)

            # Fully filled order: only deduct cost from frozen funds
            portfolio.deduct_from_frozen(transaction_cost=1500)
        """
        cost = to_decimal(cost)

        old_cash = self._cash
        old_frozen = self._frozen

        # Check if we have enough frozen funds
        if cost > self.frozen:
            GLOG.ERROR(f"Cannot deduct ${cost} from frozen ${self.frozen}")
            raise ValueError(f"Insufficient frozen funds: have ${self.frozen}, need ${cost}")

        # Deduct cost from frozen funds (cost is converted to position, not cash)
        self._frozen -= cost

        # Handle unfreeze_remain: None means unfreeze all remaining funds
        if unfreeze_remain is None:
            # Unfreeze all remaining frozen funds
            unfreeze_amount = self._frozen
            if unfreeze_amount > 0:
                self._frozen = 0
                self._cash += unfreeze_amount
        else:
            unfreeze_remain = to_decimal(unfreeze_remain)
            # Check if we have enough frozen funds for unfreeze
            if unfreeze_remain > self.frozen:
                GLOG.ERROR(f"Cannot unfreeze ${unfreeze_remain} from remaining frozen ${self.frozen}")
                raise ValueError(f"Insufficient frozen funds: have ${self.frozen}, need ${unfreeze_remain}")

            # Unfreeze specified amount back to cash
            if unfreeze_remain > 0:
                self._frozen -= unfreeze_remain
                self._cash += unfreeze_remain

        GLOG.INFO(f"💰 [CASH MONITOR] deduct_from_frozen: cost={cost}, unfreeze={unfreeze_remain}")
        GLOG.INFO(f"💰 [CASH MONITOR] cash: {old_cash} -> {self._cash}, frozen: {old_frozen} -> {self._frozen}")

        return self.frozen

    # ========== 抽象方法 ==========

    def get_position(self, code: str) -> Position:
        raise NotImplementedError("Portfolio must implement get_position method")

    def on_price_received(self, event: EventPriceUpdate) -> None:
        raise NotImplementedError("Portfolio must implement on_price_received method")

    def on_signal(self, event: EventSignalGeneration) -> Optional[Order]:
        raise NotImplementedError("Portfolio must implement on_signal method")

    def on_order_partially_filled(self, event: EventOrderPartiallyFilled) -> None:
        raise NotImplementedError("Portfolio must implement on_order_partially_filled method")

    def on_order_cancel_ack(self, event: EventOrderCancelAck) -> None:
        raise NotImplementedError("Portfolio must implement on_order_cancel_ack method")

    # ========== 分析器管理 ==========

    def add_analyzer(self, analyzer: "BaseAnalyzer") -> None:
        """
        Add Analyzer.
        """
        sys.stdout.write(f"[DEBUG] add_analyzer called: {analyzer.name}, has activate: {hasattr(analyzer, 'activate')}, active_stage: {analyzer.active_stage}\n")
        sys.stdout.flush()
        if analyzer.name in self._analyzers:
            GLOG.WARN(f"Analyzer {analyzer.name} already in the analyzers. Please Rename the ANALYZER and try again."
            )
            return
        if hasattr(analyzer, "activate") and callable(analyzer.activate):
            # 绑定 portfolio，让 analyzer 通过 ContextMixin 获取 run_id 等上下文信息
            if hasattr(analyzer, "bind_portfolio"):
                analyzer.bind_portfolio(self)
                GLOG.DEBUG(f"[add_analyzer] {analyzer.name} bind_portfolio done, _context={analyzer._context}")
            else:
                # 兼容旧代码，如果没有 bind_portfolio 方法则手动设置
                analyzer.portfolio_id = self.portfolio_id
                analyzer.engine_id = self.engine_id
            # 如果portfolio已有时间提供者，立即设置给analyzer
            if self._time_provider is not None:
                analyzer.set_time_provider(self._time_provider)
            self._analyzers[analyzer.name] = analyzer

            # 根据analyzer配置的阶段添加到相应的hook
            # activate hook: 添加到配置的active_stage
            for stage in analyzer.active_stage:
                # 修复Lambda闭包陷阱 - 使用函数创建正确的闭包
                def make_activate_func(a):
                    def activate_func(stage, portfolio_info):
                        try:
                            return a.activate(stage, portfolio_info)
                        except Exception as e:
                            self._handle_analyzer_error(a, e, stage, portfolio_info)
                            return False

                    return activate_func

                self._analyzer_activate_hook[stage].append(make_activate_func(analyzer))
                GLOG.INFO(f"Added Analyzer {analyzer.name} activate to stage {stage} hook.")

            # record hook: 添加到配置的record_stage
            # 修复Lambda闭包陷阱 - 使用函数创建正确的闭包
            def make_record_func(a):
                def record_func(stage, portfolio_info):
                    try:
                        return a.record(stage, portfolio_info)
                    except Exception as e:
                        self._handle_analyzer_error(a, e, stage, portfolio_info)
                        return False
                return record_func

            self._analyzer_record_hook[analyzer.record_stage].append(make_record_func(analyzer))
            GLOG.INFO(f"Added Analyzer {analyzer.name} record to stage {analyzer.record_stage} hook.")

        else:
            GLOG.WARN(f"Analyzer {analyzer.name} not support activate function. Please check.")

    def analyzer(self, key: str) -> "BaseAnalyzer":
        """
        Get the analyzer.
        """
        if key not in self.analyzers:
            GLOG.ERROR(f"Analyzer {key} not in the analyzers. Please check.")
            return
        return self.analyzers[key]

    def load_basic_analyzers(self) -> None:
        """
        加载基础分析器

        自动加载 BASIC_ANALYZERS 中定义的基础分析器，
        确保回测结果汇总时能获取到所需的核心指标。
        """
        from ginkgo.trading.analysis.analyzers import BASIC_ANALYZERS

        print(f"[PORTFOLIO] 📊 Loading BASIC_ANALYZERS ({len(BASIC_ANALYZERS)} analyzers)...")
        loaded_count = 0
        failed_analyzers = []

        for analyzer_class in BASIC_ANALYZERS:
            try:
                analyzer = analyzer_class()
                self.add_analyzer(analyzer)
                loaded_count += 1
                print(f"[PORTFOLIO]   ✅ {analyzer_class.__name__} loaded")
            except Exception as e:
                failed_analyzers.append(analyzer_class.__name__)
                GLOG.ERROR(f"Failed to load basic analyzer {analyzer_class.__name__}: {e}")
                print(f"[PORTFOLIO]   ❌ {analyzer_class.__name__} failed: {e}")

        if loaded_count == len(BASIC_ANALYZERS):
            print(f"[PORTFOLIO] ✅ All {loaded_count} BASIC_ANALYZERS loaded successfully")
        else:
            print(f"[PORTFOLIO] ⚠️ Loaded {loaded_count}/{len(BASIC_ANALYZERS)} analyzers. Failed: {failed_analyzers}")

        GLOG.INFO(f"Loaded {loaded_count}/{len(BASIC_ANALYZERS)} basic analyzers")

    def _handle_analyzer_error(self, analyzer, error, stage, portfolio_info):
        """
        统一的分析器错误处理
        """
        error_msg = f"Analyzer {analyzer.name} failed at stage {stage}: {str(error)}"
        analyzer.log("ERROR", error_msg)

        # 记录到Portfolio级别的错误日志
        if not hasattr(self, "_analyzer_errors"):
            self._analyzer_errors = []

        from ginkgo.trading.time.clock import now as clock_now
        self._analyzer_errors.append(
            {"analyzer": analyzer.name, "stage": stage, "error": str(error), "timestamp": clock_now()}
        )

    # ========== 通用方法 ==========

    def get_info(self) -> Dict:
        info = {
            "name": self.name,
            "now": self.get_time_provider().now() if self.get_time_provider() else None,
            "uuid": self.uuid,
            "mode": self._mode,
            "state": self._state,
            "cash": self.cash,
            "frozen": self.frozen,
            "profit": self.profit,
            "worth": self.worth,
            "positions": self.positions,
            "selector": self._selectors,
            "portfolio_id": self.portfolio_id,
            "engine_id": self.engine_id,
            "run_id": self.run_id,
            "available_cash": float(self.cash - self.frozen),
            "total_value": float(self.worth),
            "current_time": self.get_time_provider().now() if self.get_time_provider() else None,
        }
        return info

    # ========== 信号生成 ==========

    def generate_strategy_signals(self, event: EventBase):
        """
        策略信号生成
        遍历所有策略，调用策略的cal方法，返回信号列表
        """
        signals = []
        for strategy in self.strategies:
            try:
                strategy_signals = strategy.cal(self.get_info(), event)

                # 防御性处理：确保strategy_signals是列表类型
                if strategy_signals is None:
                    strategy_signals = []
                elif not isinstance(strategy_signals, list):
                    # 如果返回的是单个Signal对象，包装成列表
                    if hasattr(strategy_signals, "code"):  # 简单检查是否是Signal对象
                        strategy_signals = [strategy_signals]
                        GLOG.WARN(f"Strategy {strategy.name} returned single Signal instead of List[Signal], auto-wrapped",
                        )
                    else:
                        GLOG.ERROR(f"Strategy {strategy.name} returned invalid type {type(strategy_signals)}, ignoring")
                        strategy_signals = []

                signals.extend(strategy_signals)
            except Exception as e:
                GLOG.ERROR(f"Strategy {strategy.name} generate signal failed: {e}")
        return signals

    def generate_risk_signals(self, event: EventBase):
        """
        风控信号生成
        遍历所有风控管理器，调用generate_signals方法，返回信号列表
        """
        signals = []
        for risk_manager in self.risk_managers:
            try:
                risk_signals = risk_manager.generate_signals(self.get_info(), event)

                # 防御性处理：确保risk_signals是列表类型
                if risk_signals is None:
                    risk_signals = []
                elif not isinstance(risk_signals, list):
                    # 如果返回的是单个Signal对象，包装成列表
                    if hasattr(risk_signals, "code"):  # 简单检查是否是Signal对象
                        risk_signals = [risk_signals]
                        GLOG.WARN(f"Risk manager {risk_manager.name} returned single Signal instead of List[Signal], auto-wrapped",
                        )
                    else:
                        GLOG.ERROR(f"Risk manager {risk_manager.name} returned invalid type {type(risk_signals)}, ignoring")
                        risk_signals = []

                signals.extend(risk_signals)
            except Exception as e:
                GLOG.ERROR(f"Risk manager {risk_manager.name} generate signal failed: {e}")
        return signals

    # ========== 批处理系统支持（简化版本）==========

    def enable_batch_processing(self, batch_processor: "TimeWindowBatchProcessor") -> None:
        """
        启用批处理模式
        """
        try:
            from ginkgo.trading.signal_processing.batch_processor import TimeWindowBatchProcessor

            if not isinstance(batch_processor, TimeWindowBatchProcessor):
                GLOG.ERROR("Invalid batch processor type")
                return

            # 保存原始信号处理方法
            if not self._original_on_signal:
                self._original_on_signal = self.on_signal

            self._batch_processor = batch_processor
            self._batch_processing_enabled = True

            # 设置批处理器的组合信息获取函数
            self._batch_processor.get_portfolio_info = self.get_info

            GLOG.INFO(f"Batch processing enabled with {batch_processor.window_type.value} window")

        except Exception as e:
            GLOG.ERROR(f"Failed to enable batch processing: {e}")

    def disable_batch_processing(self) -> None:
        """禁用批处理模式，回退到原始信号处理"""
        self._batch_processing_enabled = False
        self._batch_processor = None
        GLOG.INFO("Batch processing disabled")

    def get_batch_processing_stats(self) -> Dict:
        """
        获取批处理统计信息
        """
        if not self._batch_processing_enabled or not self._batch_processor:
            return {"enabled": False}

        stats = self._batch_processor.get_stats()
        stats["enabled"] = True
        return stats

    def _on_time_advance(self, new_time: datetime.datetime) -> None:
        """
        时间推进钩子 - 调用所有组件的时间推进方法

        在时间推进时，Portfolio需要通知所有绑定的Selector组件，
        让Selector有机会推送新的兴趣集合到引擎。

        Args:
            new_time: 新的业务时间
        """
        # 调用父类的时间推进钩子
        super()._on_time_advance(new_time)

        # 调用所有Selector的advance_time方法
        GLOG.INFO(f"🔧 About to advance time for {len(self._selectors)} selectors")
        for i, selector in enumerate(self._selectors):
            try:
                GLOG.INFO(f"🔧 About to call advance_time on selector #{i+1}: {selector.name}")
                if selector is None:
                    GLOG.ERROR(f"❌ Selector #{i+1} is None!")
                    continue
                if not hasattr(selector, 'advance_time'):
                    GLOG.ERROR(f"❌ Selector {selector.name} has no advance_time method!")
                    continue
                if not callable(selector.advance_time):
                    GLOG.ERROR(f"❌ Selector {selector.name}.advance_time is not callable!")
                    continue

                selector.advance_time(new_time)
                GLOG.INFO(f"✅ Successfully called advance_time on selector: {selector.name}")
            except Exception as e:
                GLOG.ERROR(f"❌ Selector {selector.name} advance_time failed: {e}")
                import traceback
                GLOG.ERROR(f"📋 Selector traceback: {traceback.format_exc()}")

        if not self._selectors:
            GLOG.WARN("No selectors bound to portfolio, interest set will remain empty")