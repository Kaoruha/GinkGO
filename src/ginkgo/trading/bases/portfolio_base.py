"""
投资组合组件基类

组合完整的管理能力，为所有投资组合组件提供基础功能
"""

import uuid
import datetime
from rich.console import Console
from typing import TYPE_CHECKING, List, Dict, Optional
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import timedelta

if TYPE_CHECKING:
    from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
    from ginkgo.trading.strategies import BaseStrategy
    from ginkgo.trading.signal_processing.batch_processor import TimeWindowBatchProcessor
    from ginkgo.trading.engines.base_engine import BaseEngine
else:
    # 运行时导入，避免循环依赖
    from ginkgo.trading.engines.base_engine import BaseEngine

from ginkgo.trading.core.base import Base
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
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
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, RECORDSTAGE_TYPES, SOURCE_TYPES
from ginkgo.libs import GCONF, to_decimal


console = Console()


class PortfolioBase(TimeMixin, ContextMixin, EngineBindableMixin,
                   NamedMixin, LoggableMixin, Base, ABC):
    """
    投资组合组件基类

    组合完整的管理能力，为所有投资组合组件提供基础功能：
    - 时间戳管理 (timestamp, business_timestamp)
    - 上下文管理 (engine_id, run_id, portfolio_id)
    - 引擎绑定 (bind_engine, engine_put)
    - 名称管理 (name)
    - 日志管理 (log, add_logger)
    - 组件基础功能 (uuid, component_type, dataframe转换)
    """

    def __init__(
        self,
        name: str = "Portfolio",
        *args,
        **kwargs,
    ) -> None:
        """
        初始化投资组合基类

        Args:
            name: 投资组合名称
            **kwargs: 传递给父类的参数
        """
        # 显式初始化各个Mixin，确保正确的初始化顺序

        # TimeMixin初始化
        TimeMixin.__init__(self, **kwargs)

        # ContextMixin初始化
        ContextMixin.__init__(self, **kwargs)

        # EngineBindableMixin初始化
        EngineBindableMixin.__init__(self, **kwargs)

        # NamedMixin初始化 - 传递name参数
        NamedMixin.__init__(self, name=name, **kwargs)

        # LoggableMixin初始化
        LoggableMixin.__init__(self, **kwargs)

        # Base初始化
        Base.__init__(self)

        # Portfolio核心业务属性
        self._cash: Decimal = Decimal("100000")
        self._worth: Decimal = self._cash
        self._profit: Decimal = Decimal("0")
        self._frozen: Decimal = Decimal("0")
        self._fee = Decimal("0")
        self._positions: dict = {}
        self._strategies: List["BaseStrategy"] = []
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

    # ========== 基础属性和方法 ==========

    def set_event_publisher(self, publisher) -> None:
        """
        Inject an event publisher (typically engine.put) for pushing events back to engine.
        """
        self._engine_put = publisher

    def bind_data_feeder(self, feeder, *args, **kwargs):
        if self._sizer is not None:
            self._sizer.bind_data_feeder(feeder)
        for selector in self._selectors:
            selector.bind_data_feeder(feeder)
        for i in self._strategies:
            i.bind_data_feeder(feeder)

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            self.log("ERROR", f"Engine put not bind. Events can not put back to the engine.")
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
        if money <= 0:
            self.log("ERROR", f"The money should not under 0. {money} is illegal.")
        else:
            self._cash += money
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
            self.log("ERROR", f"The fee should not under 0. {fee} is illegal.")
        else:
            self.log("DEBUG", f"Add FEE {fee}")
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
            self.log("ERROR", f"Portfolio Sizer not set. Can not handle the signal. Please set the SIZER first.")
            return False

        if not self._selectors:
            self.log("ERROR", f"Portfolio Selector not set. Can not pick the code. Please set the SELECTOR first.")
            return False

        if len(self.risk_managers) == 0:
            self.log("WARN", f"Portfolio RiskManager not set. Backtest will go on without Risk Control.")

        if len(self.strategies) == 0:
            self.log("ERROR", f"No strategy register. No signal will come.")
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
            self.log("ERROR", f"Error checking event time: {e}")
            return False

    # ========== 绑定方法 ==========

    def bind_selector(self, selector: SelectorBase) -> None:
        """
        Bind selector to portfolio, and bind portfolio itself to selector.
        支持添加多个selector到列表中。
        """
        if not isinstance(selector, SelectorBase):
            self.log("ERROR", f"Selector bind only support Selector, {type(selector)} {selector} is not supported.")
            return
        self._selectors.append(selector)
        # 绑定portfolio引用，让selector可以直接从portfolio获取ID
        selector.bind_portfolio(self)
        # 如果portfolio已绑定engine，也绑定给selector
        if self._bound_engine is not None:
            selector.bind_engine(self._bound_engine)
        # 传递时间提供者给selector
        if self.get_time_provider() is not None:
            selector.set_time_provider(self.get_time_provider())

    def bind_engine(self, engine: BaseEngine):
        """
        Bind engine to portfolio and propagate to all bound components.
        """
        if not isinstance(engine, BaseEngine):
            raise TypeError(f"Expected BaseEngine, got {type(engine)}")

        # 绑定引擎到portfolio自身
        super(PortfolioBase, self).bind_engine(engine)

        # 通过ContextMixin的公共接口同步给所有已绑定的组件
        # 策略组件（支持多个）
        for strategy in self._strategies:
            strategy.bind_engine(engine)

        # Sizer组件（单个）- 需要engine_id创建Order
        if self._sizer is not None:
            self._sizer.bind_engine(engine)
            self._sizer.bind_portfolio(self)

        # Selector组件（支持多个）
        for selector in self._selectors:
            selector.bind_engine(engine)
            selector.bind_portfolio(self)

        # 分析器组件（支持多个）
        for analyzer in self._analyzers.values():
            analyzer.bind_engine(engine)
            analyzer.bind_portfolio(self)

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
            self.log("ERROR", f"Risk manager only support RiskBase, {type(risk)} {risk} is not supported.")
            return
        if risk not in self.risk_managers:
            self.risk_managers.append(risk)

    def add_strategy(self, strategy: "BaseStrategy") -> None:
        if strategy not in self.strategies:
            self.strategies.append(strategy)
            # 绑定portfolio引用给strategy
            strategy.bind_portfolio(self)

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
            self.log("ERROR", f"Sizer bind only support Sizer, {type(sizer)} {sizer} is not supported.")
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
        if money >= self.cash:
            self.log("WARN", f"We cant freeze {money}, we only have {self.cash}.")
            return False
        self.log("DEBUG", f"TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
        console.print(f":ice: TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
        self._frozen += money
        self._cash -= money
        self.log("DEBUG", f"DONE FREEZE ${money}. CURRENFROZEN: ${self._frozen}. CURRENTCASH: ${self.cash} ")
        console.print(f":money_bag: DONE FREEZE ${money}. CURRENFROZEN: ${self._frozen}. CURRENTCASH: ${self.cash} ")
        return True

    def unfreeze(self, money: any) -> Decimal:
        """
        Unfreeze the money.
        """
        money = to_decimal(money)
        if money > self.frozen:
            if money - self.frozen > GCONF.EPSILON:
                self.log("ERROR", f"Cant unfreeze ${money}, the max unfreeze is only ${self.frozen}")
                console.print(f":prohibited: Cant unfreeze ${money}, the max unfreeze is only ${self.frozen}")
                return
            else:
                self._frozen = 0
                self.log("DEBUG", f"DONE UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
        else:
            self.log("DEBUG", f"TRYING UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
            self._frozen -= money
            self.log("DEBUG", f"DONE UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
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
        if analyzer.name in self._analyzers:
            self.log(
                "WARN", f"Analyzer {analyzer.name} already in the analyzers. Please Rename the ANALYZER and try again."
            )
            return
        if hasattr(analyzer, "activate") and callable(analyzer.activate):
            analyzer.portfolio_id = self.portfolio_id
            analyzer.engine_id = self.engine_id
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
                self.log("DEBUG", f"Added Analyzer {analyzer.name} activate to stage {stage} hook.")

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
            self.log("DEBUG", f"Added Analyzer {analyzer.name} record to stage {analyzer.record_stage} hook.")

        else:
            self.log("WARN", f"Analyzer {analyzer.name} not support activate function. Please check.")

    def analyzer(self, key: str) -> "BaseAnalyzer":
        """
        Get the analyzer.
        """
        if key not in self.analyzers:
            self.log("ERROR", f"Analyzer {key} not in the analyzers. Please check.")
            return
        return self.analyzers[key]

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
                        self.log(
                            "WARN",
                            f"Strategy {strategy.name} returned single Signal instead of List[Signal], auto-wrapped",
                        )
                    else:
                        self.log(
                            "ERROR",
                            f"Strategy {strategy.name} returned invalid type {type(strategy_signals)}, ignoring",
                        )
                        strategy_signals = []

                signals.extend(strategy_signals)
            except Exception as e:
                self.log("ERROR", f"Strategy {strategy.name} generate signal failed: {e}")
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
                        self.log(
                            "WARN",
                            f"Risk manager {risk_manager.name} returned single Signal instead of List[Signal], auto-wrapped",
                        )
                    else:
                        self.log(
                            "ERROR",
                            f"Risk manager {risk_manager.name} returned invalid type {type(risk_signals)}, ignoring",
                        )
                        risk_signals = []

                signals.extend(risk_signals)
            except Exception as e:
                self.log("ERROR", f"Risk manager {risk_manager.name} generate signal failed: {e}")
        return signals

    # ========== 批处理系统支持（简化版本）==========

    def enable_batch_processing(self, batch_processor: "TimeWindowBatchProcessor") -> None:
        """
        启用批处理模式
        """
        try:
            from ginkgo.trading.signal_processing.batch_processor import TimeWindowBatchProcessor

            if not isinstance(batch_processor, TimeWindowBatchProcessor):
                self.log("ERROR", "Invalid batch processor type")
                return

            # 保存原始信号处理方法
            if not self._original_on_signal:
                self._original_on_signal = self.on_signal

            self._batch_processor = batch_processor
            self._batch_processing_enabled = True

            # 设置批处理器的组合信息获取函数
            self._batch_processor.get_portfolio_info = self.get_info

            self.log("INFO", f"Batch processing enabled with {batch_processor.window_type.value} window")

        except Exception as e:
            self.log("ERROR", f"Failed to enable batch processing: {e}")

    def disable_batch_processing(self) -> None:
        """禁用批处理模式，回退到原始信号处理"""
        self._batch_processing_enabled = False
        self._batch_processor = None
        self.log("INFO", "Batch processing disabled")

    def get_batch_processing_stats(self) -> Dict:
        """
        获取批处理统计信息
        """
        if not self._batch_processing_enabled or not self._batch_processor:
            return {"enabled": False}

        stats = self._batch_processor.get_stats()
        stats["enabled"] = True
        return stats