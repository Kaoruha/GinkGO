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
    from ginkgo.trading.strategies import BaseStrategy
    from ginkgo.trading.engines.base_engine import BaseEngine
else:
    # 运行时导入，避免循环依赖
    from ginkgo.trading.engines.base_engine import BaseEngine

from ginkgo.entities.base import Base
from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import ContextMixin
from ginkgo.entities.mixins import EngineBindableMixin
from ginkgo.entities.mixins import NamedMixin
from ginkgo.trading.mixins.subscribable_mixin import SubscribableMixin, subscribes
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
from ginkgo.enums import DIRECTION_TYPES, RECORDSTAGE_TYPES, SOURCE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES, DEFAULT_ANALYZER_SET, EVENT_TYPES
from ginkgo.libs import GCONF, GLOG, to_decimal


console = Console()


class PortfolioBase(TimeMixin, ContextMixin, EngineBindableMixin, SubscribableMixin,
                   NamedMixin, Base, ABC):
    """
    投资组合组件基类

    组合完整的管理能力，为所有投资组合组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, task_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    # 内置默认分析器配置（字符串列表）
    BUILTIN_DEFAULT_ANALYZERS = {
        DEFAULT_ANALYZER_SET.MINIMAL: ['net_value', 'profit'],
        DEFAULT_ANALYZER_SET.STANDARD: ['net_value', 'profit', 'max_drawdown', 'sharpe_ratio', 'win_rate',
                                     'trade_win_rate', 'annualized_return', 'signal_count', 'order_count',
                                     'profit_factor', 'avg_win_loss_ratio', 'max_consecutive_losses',
                                     'avg_holding_period'],
        DEFAULT_ANALYZER_SET.FULL: ['net_value', 'profit', 'max_drawdown', 'sharpe_ratio',
                                     'win_rate', 'trade_win_rate', 'volatility', 'sortino_ratio', 'calmar_ratio',
                                     'hold_pct', 'signal_count', 'order_count', 'annualized_return',
                                     'consecutive_pnl', 'underwater_time', 'skew_kurtosis', 'var_cvar',
                                     'profit_factor', 'avg_win_loss_ratio', 'max_consecutive_losses',
                                     'avg_holding_period'],
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
        self._strategies: List["BaseStrategy"] = []
        self._sizer: SizerBase = None
        self._risk_managers: List[RiskBase] = []
        self._selectors = []  # 支持多个selector
        self._data_feeder = None
        self._analyzers: Dict[str, "BaseAnalyzer"] = {}
        self._analyzer_activate_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
        self._analyzer_record_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
        # 注意：不要覆盖_context_mixin提供的_engine_id，它由ContextMixin管理
        self._interested: List = []
        self._engine_put = None

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
        from ginkgo.trading.analysis.analyzers.trade_win_rate import TradeWinRate
        from ginkgo.trading.analysis.analyzers.order_count import OrderCount
        from ginkgo.trading.analysis.analyzers.annualized_returns import AnnualizedReturn
        from ginkgo.trading.analysis.analyzers.consecutive_pnl import ConsecutivePnL
        from ginkgo.trading.analysis.analyzers.underwater_time import UnderwaterTime
        from ginkgo.trading.analysis.analyzers.skew_kurtosis import SkewKurtosis
        from ginkgo.trading.analysis.analyzers.var_cvar import VarCVar
        from ginkgo.trading.analysis.analyzers.profit_factor import ProfitFactor
        from ginkgo.trading.analysis.analyzers.avg_win_loss_ratio import AvgWinLossRatio
        from ginkgo.trading.analysis.analyzers.max_consecutive_losses import MaxConsecutiveLosses
        from ginkgo.trading.analysis.analyzers.avg_holding_period import AvgHoldingPeriod

        # 内置分析器映射
        builtin_map = {
            'net_value': NetValue,
            'profit': Profit,
            'max_drawdown': MaxDrawdown,
            'sharpe_ratio': SharpeRatio,
            'win_rate': WinRate,
            'trade_win_rate': TradeWinRate,
            'volatility': Volatility,
            'sortino_ratio': SortinoRatio,
            'calmar_ratio': CalmarRatio,
            'hold_pct': HoldPCT,
            'signal_count': SignalCount,
            'order_count': OrderCount,
            'annualized_return': AnnualizedReturn,
            'consecutive_pnl': ConsecutivePnL,
            'underwater_time': UnderwaterTime,
            'skew_kurtosis': SkewKurtosis,
            'var_cvar': VarCVar,
            'profit_factor': ProfitFactor,
            'avg_win_loss_ratio': AvgWinLossRatio,
            'max_consecutive_losses': MaxConsecutiveLosses,
            'avg_holding_period': AvgHoldingPeriod,
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
        self._data_feeder = feeder
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

    def end_day(self) -> None:
        """D 日日终结算：刷新账面值并触发 ENDDAY 分析器钩子。

        由引擎在把共享时钟推进到新日**之前**调用
        （time_controlled_engine._handle_time_advance_event），
        此刻时钟=D、持仓价=D 日收盘价，分析器读到的是纯 D 日状态。
        PortfolioLive 同样继承此入口，LIVE 日终事件化接入时复用。
        """
        self.update_worth()
        self.update_profit()
        for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ENDDAY]:
            func(RECORDSTAGE_TYPES.ENDDAY, self.get_info())
        for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ENDDAY]:
            func(RECORDSTAGE_TYPES.ENDDAY, self.get_info())

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

    def _propagate_context(self, component) -> None:
        """
        把 portfolio 当前上下文同步给单个组件（#4607 提取，消除 add/bind 系列重复传播）。

        bind_portfolio 总是执行；bind_engine / set_time_provider / bind_data_feeder
        仅当 portfolio 已持有对应对象时传播（与原 add_strategy/bind_selector/bind_sizer 行为一致）。
        """
        component.bind_portfolio(self)
        if self._bound_engine is not None:
            component.bind_engine(self._bound_engine)
        if self._time_provider is not None:
            component.set_time_provider(self._time_provider)
        if self._data_feeder is not None:
            component.bind_data_feeder(self._data_feeder)

    def _rebind_portfolio_and_engine(self, component, engine) -> None:
        """
        bind_engine 变更引擎时对已注册组件重绑（#4607 提取，消除 bind_engine 循环内重复）。
        仅重绑 portfolio 引用与新 engine，不触碰 time_provider/data_feeder（保持原两步语义）。
        """
        component.bind_portfolio(self)
        component.bind_engine(engine)

    def bind_selector(self, selector: SelectorBase) -> None:
        """
        Bind selector to portfolio, and bind portfolio itself to selector.
        支持添加多个selector到列表中。
        """
        if not isinstance(selector, SelectorBase):
            GLOG.ERROR(f"Selector bind only support Selector, {type(selector)} {selector} is not supported.")
            return
        self._selectors.append(selector)
        # 传播 portfolio 上下文（engine/time_provider/data_feeder）
        self._propagate_context(selector)

    def _iter_components(self):
        """
        全部已挂载组件的单一事实来源（组件清单收敛,2026-08-16）。

        此前 bind_engine 重绑 / set_time_provider 下传各自手写四类组件清单,
        risk_managers 在两处被遗漏——风控组件"挂上了但没人认领"（无时钟/无身份,
        信号 business_timestamp 与 engine_id 全空）。所有对全量组件的传播遍历
        （时钟/引擎/context 重绑/未来的任何下传）一律经本迭代器——新增组件类型
        只改此处一份清单,遍历点自动覆盖。

        顺序:strategies → sizer → selectors → risk_managers → analyzers。

        形态注记:sizer 是五类中唯一的"单值槽位"(组合同一时刻只能有一个仓位
        算法,双 sizer 对"这单买多少"会给冲突答案)——未绑定时为 None,须守卫,
        否则 yield from None 抛 TypeError。其余四类为集合(list/dict),"没有
        组件"即空集合,空迭代天然无害无需守卫。将来新增单值型组件同样要带
        is not None 守卫,集合型直接 yield from。
        """
        yield from self._strategies
        # 唯一单值槽位:None=未绑定,守卫防 yield from None;领域语义见 docstring
        if self._sizer is not None:
            yield self._sizer
        yield from self._selectors
        yield from self.risk_managers
        yield from self._analyzers.values()

    def bind_engine(self, engine: BaseEngine):
        """
        Bind engine to portfolio and propagate to all bound components.
        """
        if not isinstance(engine, BaseEngine):
            raise TypeError(f"Expected BaseEngine, got {type(engine)}")

        # 绑定引擎到portfolio自身 - ContextMixin.bind_engine在MRO中
        super().bind_engine(engine)
        # 入方向：注册组件订阅的事件处理器（ADR-017，与出方向 _engine_put 对称）
        self.register_handlers(engine)

        # 如果引擎有TimeProvider，设置给Portfolio
        if engine._time_provider is not None:
            self.set_time_provider(engine._time_provider)

        # 全量组件重绑（单一清单,见 _iter_components）:
        # bind_portfolio 设 _context → bind_engine 更新引擎引用与 context
        for component in self._iter_components():
            self._rebind_portfolio_and_engine(component, engine)

    def set_time_provider(self, time_provider) -> None:
        """
        重写时间提供者设置，自动传递给所有已绑定的组件（单一清单,见 _iter_components）
        """
        super().set_time_provider(time_provider)
        for component in self._iter_components():
            component.set_time_provider(time_provider)

    def add_risk_manager(self, risk: RiskBase) -> None:
        """
        Add risk manager to portfolio.
        """
        if not isinstance(risk, RiskBase):
            GLOG.ERROR(f"Risk manager only support RiskBase, {type(risk)} {risk} is not supported.")
            return
        if risk not in self.risk_managers:
            self.risk_managers.append(risk)
            # 传播 portfolio 上下文(engine/time_provider/data_feeder)——与其他组件
            # 挂载方法(add_strategy/bind_sizer/bind_selector)对齐。此前风控是唯一
            # 漏传播的组件:RiskBase.create_signal 工厂里 get_time_provider() 为 None
            # → 风控信号 business_timestamp 落空(入库 epoch0/timestamp 退化真实时间),
            # id 注入同样失效(2026-08-16 Loss Limit 信号实例)
            self._propagate_context(risk)

    def add_strategy(self, strategy: "BaseStrategy") -> None:
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            # 传播 portfolio 上下文（engine/time_provider/data_feeder）
            self._propagate_context(strategy)

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
        # 传播 portfolio 上下文（engine/time_provider/data_feeder）
        self._propagate_context(sizer)

    def freeze(self, money: any) -> bool:
        """
        Freeze the capital.
        """
        money = to_decimal(money)
        if money > self.cash:
            GLOG.WARN(f"We cant freeze {money}, we only have {self.cash}.")
            return False
        self._frozen += money
        self._cash -= money
        GLOG.INFO(f"💰 [CASH MONITOR] freeze_cash: -{money} (old: {self._cash + money} -> new: {self._cash}, frozen: {self._frozen})")
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
            shortfall = cost - self.frozen
            if shortfall > self._cash:
                # 真实超支:冻结+现金都不够 → 拒(合法拒绝)
                GLOG.ERROR(f"Cannot deduct ${cost}: frozen ${self.frozen} + cash ${self._cash} insufficient")
                raise ValueError(
                    f"Insufficient funds: frozen ${self.frozen} + cash ${self._cash} < cost ${cost}"
                )
            # 常态兜底(2026-08-16):T日冻结按预估价、T+1成交按实际价,隔夜价差
            # 使 cost 略超冻结是价格合法变动的常态而非超支——差额从现金补,
            # 不再整单拒绝(旧语义:差$40拒一单,系统性"只让次日跌的买入成交")
            GLOG.WARN(
                f"[CASH MONITOR] frozen short ${shortfall}, covered from cash "
                f"(T+1 price gap; frozen ${self.frozen} -> cost ${cost})"
            )
            self._cash -= shortfall
            self._frozen = to_decimal(0)
            return self._frozen

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

    @subscribes(EVENT_TYPES.PRICEUPDATE)
    def on_price_received(self, event: EventPriceUpdate) -> None:
        raise NotImplementedError("Portfolio must implement on_price_received method")

    @subscribes(EVENT_TYPES.SIGNALGENERATION)
    def on_signal(self, event: EventSignalGeneration) -> Optional[Order]:
        raise NotImplementedError("Portfolio must implement on_signal method")

    # 不订阅 ORDERPARTIALLYFILLED：回测路径经 TradeGateway.on_order_partially_filled
    # 路由器按 portfolio_id 转发调用此方法（方法调用，非引擎订阅）。直接订阅会导致
    # 引擎触发 + Gateway 路由双重处理。抽象方法保留以约束子类实现供 Gateway 路由调用。
    def on_order_partially_filled(self, event: EventOrderPartiallyFilled) -> None:
        raise NotImplementedError("Portfolio must implement on_order_partially_filled method")

    @subscribes(EVENT_TYPES.ORDERCANCELACK)
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
            # 绑定 portfolio，让 analyzer 通过 ContextMixin 获取 task_id 等上下文信息
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

    def _handle_analyzer_error(self, analyzer, error, stage, portfolio_info):
        """
        统一的分析器错误处理
        """
        error_msg = f"Analyzer {analyzer.name} failed at stage {stage}: {str(error)}"
        GLOG.ERROR(error_msg)

        # 记录到Portfolio级别的错误日志
        if not hasattr(self, "_analyzer_errors"):
            self._analyzer_errors = []

        from ginkgo.trading.time.clock import now as clock_now
        self._analyzer_errors.append(
            {"analyzer": analyzer.name, "stage": stage, "error": str(error), "timestamp": clock_now()}
        )

    # ========== 状态快照与恢复 ==========

    def snapshot_state(self) -> dict:
        """
        序列化运行时状态（进程内 handoff，供 worker→service 持久化）。

        positions 直接携带 Position 实体（trading 层原生类型），由 service 层在
        DB 边界用 PositionMapper.entity_to_model 转 MPosition——不在此处构造 ORM、
        不展开 dict key（ADR-010 entity/model 分层，避免 dict key 漂移导致持仓静默丢失）。
        外层 cash/frozen/fee 走 str(Decimal) 便于日志可读。

        Returns:
            dict: cash/frozen/fee 标量 + positions: List[Position]
        """
        return {
            "cash": str(self._cash),
            "frozen": str(self._frozen),
            "fee": str(self._fee),
            "positions": list(self._positions.values()),
        }

    def restore_state(self, state: dict) -> None:
        """
        从快照恢复运行时状态（直接设内部字段，不发事件，不写 DB）。

        positions 已是 Position 实体（load_persisted_state 在 DB 边界用
        PositionMapper.model_to_entity 还原），直接装回 self._positions。

        Args:
            state: load_persisted_state 返回的状态字典（兼容 snapshot_state 形状）
        """
        self._cash = Decimal(state["cash"])
        self._frozen = Decimal(state["frozen"])
        self._fee = Decimal(state["fee"])

        self._positions = {}
        for pos in state.get("positions", []):
            self._positions[pos.code] = pos

        self.update_worth()
        self.update_profit()

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
            "task_id": self.task_id,
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