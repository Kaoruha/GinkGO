import uuid
import datetime
from rich.console import Console
from typing import TYPE_CHECKING, List, Dict, Optional
from abc import ABC, abstractmethod
from decimal import Decimal


if TYPE_CHECKING:
    from ginkgo.backtest.analysis.analyzers.base_analyzer import BaseAnalyzer
    from ginkgo.backtest.strategy.strategies import StrategyBase


from ginkgo.backtest.execution.engines.base_engine import BaseEngine
from ginkgo.backtest.strategy.selectors import BaseSelector
from ginkgo.backtest.core.backtest_base import BacktestBase
from ginkgo.backtest.strategy.risk_managements.base_risk import BaseRiskManagement
from ginkgo.backtest.strategy.sizers.base_sizer import BaseSizer
from ginkgo.backtest.execution.events.base_event import EventBase
from ginkgo.backtest.execution.events.price_update import EventPriceUpdate
from ginkgo.backtest.execution.events.signal_generation import EventSignalGeneration
from ginkgo.backtest.execution.events.order_filled import EventOrderFilled
from ginkgo.backtest.execution.events.order_canceled import EventOrderCanceled
from ginkgo.backtest.entities.bar import Bar
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.entities.position import Position
from ginkgo.enums import DIRECTION_TYPES, RECORDSTAGE_TYPES
from ginkgo.libs import GCONF, to_decimal


console = Console()


class BasePortfolio(BacktestBase, ABC):
    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super(BasePortfolio, self).__init__(*args, **kwargs)
        self.set_name("Halo")
        self._uuid: str = uuid.uuid4().hex
        self._cash: Decimal = Decimal("100000")
        self._worth: Decimal = self._cash
        self._profit: Decimal = Decimal("0")
        self._frozen: Decimal = Decimal("0")
        self._fee = Decimal("0")
        self._positions: dict = {}
        self._strategies: List["StrategyBase"] = []
        self._sizer: BaseSizer = None
        self._risk_managers: List[BaseRiskManagement] = []
        self._selector = None
        self._analyzers: Dict[str, "BaseAnalyzer"] = {}
        self._analyzer_activate_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
        self._analyzer_record_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
        self._engine_id = None
        self._interested: List = []
        self._engine_put = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        if self._sizer is not None:
            self._sizer.bind_data_feeder(feeder)
        if self._selector is not None:
            self._selector.bind_data_feeder(feeder)
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

    # def get_count_of_price(self, date: any) -> int:
    #     # TODO ?
    #     raise NotImplemented("Must implement the Function to get the count of coming price info.")

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
            profit_sum += self.positions[key].profit
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

    def is_all_set(self) -> bool:
        """
        Check if all parts set
        Args:
            None
        Returns:
            Is all preparation complete?
        """
        if self.sizer is None:
            self.log("ERROR", f"Portfolio Sizer not set. Can not handle the signal. Please set the SIZER first.")
            return False

        if self.selector is None:
            self.log("ERROR", f"Portfolio Selector not set. Can not pick the code. Please set the SELECTOR first.")
            return False

        if len(self.risk_managers) == 0:
            self.log("WARN", f"Portfolio RiskManager not set. Backtest will go on without Risk Control.")

        if len(self.strategies) == 0:
            self.log("ERROR", f"No strategy register. No signal will come.")
            return False

        return True

    def bind_selector(self, selector: BaseSelector) -> None:
        """
        Bind selector to portfolio, and bind portfolio itself to selector.
        Args:
            selector(BaseSelector): stock, etf picker
        Return:
            None
        """
        if not isinstance(selector, BaseSelector):
            self.log("ERROR", f"Selector bind only support Selector, {type(selector)} {selector} is not supported.")
            return
        self._selector = selector

    @property
    def selector(self):
        """
        Target selector
        """
        return self._selector

    def bind_engine(self, engine: BaseEngine):
        """
        Bind engine to portfolio.
        Args:
            engine(BaseEngine): engine
        Return:
            None
        """
        if not isinstance(engine, BaseEngine):
            raise TypeError(f"Expected BaseEngine, got {type(engine)}")
        super(BasePortfolio, self).bind_engine(engine)
        for i in self.strategies:
            i.bind_engine(engine)
        if self._selector is not None:
            self._selector.bind_engine(engine)
        if self._sizer is not None:
            self._sizer.bind_engine(engine)
        for i in self._analyzers:
            self._analyzers[i].bind_engine(engine)

    def add_risk_manager(self, risk: BaseRiskManagement) -> None:
        """
        Add risk manager to portfolio.
        Args:
            risk(BaseRiskManagement): risk module
        Return:
            None
        """
        if not isinstance(risk, BaseRiskManagement):
            self.log("ERROR", f"Risk manager only support BaseRiskManagement, {type(risk)} {risk} is not supported.")
            return
        if risk not in self.risk_managers:
            self.risk_managers.append(risk)

    @property
    def risk_managers(self) -> List[BaseRiskManagement]:
        return self._risk_managers

    def bind_sizer(self, sizer: BaseSizer) -> None:
        """
        Bind sizer to portfolio. And bind the portfolio itself to sizer.
        Args:
            sizer(BaseSizer): Calculate the volume of order.
        Return:
            None
        """
        if not isinstance(sizer, BaseSizer):
            self.log("ERROR", f"Sizer bind only support Sizer, {type(sizer)} {sizer} is not supported.")
            return
        self._sizer = sizer

    @property
    def sizer(self) -> BaseSizer:
        return self._sizer

    def freeze(self, money: any) -> bool:
        """
        Freeze the capital.
        Args:
            money(any): ready to freeze target money
        Return:
            None
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
        Args:
            money(any): unfreeze money.
        Return:
            Current frozen money.
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

    def add_analyzer(self, analyzer: "BaseAnalyzer") -> None:
        """
        Add Analyzer.
        Args:
            analyzer(BaseAnalyzer): new analyzer
        Return:
            None
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
        Args:
            key(str): key
        Return:
            The analyzer[key]
        """
        if key not in self.analyzers:
            self.log("ERROR", f"Analyzer {key} not in the analyzers. Please check.")
            return
        return self.analyzers[key]
    
    def _handle_analyzer_error(self, analyzer, error, stage, portfolio_info):
        """
        统一的分析器错误处理
        Args:
            analyzer: 出错的分析器实例
            error: 异常对象
            stage: 出错的阶段
            portfolio_info: 投资组合信息
        """
        error_msg = f"Analyzer {analyzer.name} failed at stage {stage}: {str(error)}"
        analyzer.log("ERROR", error_msg)
        
        # 记录到Portfolio级别的错误日志
        if not hasattr(self, '_analyzer_errors'):
            self._analyzer_errors = []
        
        self._analyzer_errors.append({
            'analyzer': analyzer.name,
            'stage': stage,
            'error': str(error),
            'timestamp': datetime.datetime.now()
        })

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

    def add_strategy(self, strategy: "StrategyBase") -> None:
        if strategy not in self.strategies:
            self.strategies.append(strategy)

    def add_position(self, position: Position) -> None:
        code = position.code
        if code in self.positions.keys():
            self._positions[code].deal(DIRECTION_TYPES.LONG, position.cost, position.volume)
        else:
            self._positions[code] = position

    def get_position(self, code: str) -> Position:
        raise NotImplementedError("Portfolio must implement get_position method")

    def on_price_received(self, event: EventPriceUpdate) -> None:
        raise NotImplementedError("Portfolio must implement on_price_received method")

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

    def on_signal(self, event: EventSignalGeneration) -> Optional[Order]:
        raise NotImplementedError("Portfolio must implement on_signal method")

    def on_order_filled(self, event: EventOrderFilled) -> None:
        raise NotImplementedError("Portfolio must implement on_order_filled method")

    def on_order_canceled(self, event: EventOrderCanceled) -> None:
        raise NotImplementedError("Portfolio must implement on_order_canceled method")

    def on_time_goes_by(self, time: any, *args, **kwargs) -> None:
        """
        Go next frame.
        """
        super(BasePortfolio, self).on_time_goes_by(time, *args, **kwargs)
        # TODO
        if not self.is_all_set():
            self.log("WARN", f"{time} comes. But portfolio:{self.name} is no ready.")
            return
        self.sizer.on_time_goes_by(time)

        self._interested = []
        codes = self.selector.pick(time)
        for code in codes:
            self._interested.append(code)

        for analyzer_key in self.analyzers.keys():
            self.analyzers[analyzer_key].on_time_goes_by(time)

        for strategy in self.strategies:
            strategy.on_time_goes_by(time, *args, **kwargs)

        self.update_profit()
        self.update_worth()

    def clean_positions(self) -> None:
        """
        if some position's volome and frozen == 0, remove it from positions of portfolio.
        """
        if len(self.positions.keys()) == 0:
            return
        del_list = []

        for key in self.positions.keys():
            pos = self.get_position(key)
            if pos is None:
                continue
            vol = pos.volume + pos.frozen_volume
            if vol == 0:
                del_list.append(key)
        for code in del_list:
            del self.positions[code]

    def bought(self, code: str, price: any, volume: int, fee: any) -> None:
        price = to_decimal(price)
        fee = to_decimal(fee)
        if volume < 0:
            # LOG
            return
        if fee < 0:
            # LOG
            return
        pos = Position()
        pos.set(code, price, volume)
        self.add_position(pos)

    def sold(self, code: str, price: any, volume: int, fee: any) -> None:
        price = to_decimal(price)
        fee = to_decimal(fee)
        p = self.get_position(code)
        if p is None:
            # LOG
            return
        if volume > p.volume:
            # LOG
            return
        if fee < 0:
            # LOG
            return
        p.volume -= volume
        self.add_fee(fee)
        self._cash += price * volume - fee

    def is_event_from_future(self, event) -> bool:
        """
        Prevent the event from future.
        """
        try:
            if event.timestamp > self.now:
                self.log(
                    "CRITICAL",
                    f"Current time is {self.now.strftime('%Y-%m-%d %H:%M:%S')}, The Event {event.event_type} generated at {event.timestamp}, Can not handle the future infomation.",
                )
                return True
            else:
                return False
        except Exception as e:
            self.log("ERROR", e)
            return True
        finally:
            pass

    def get_info(self) -> Dict:
        info = {
            "name": self.name,
            "now": self.now,
            "uuid": self.uuid,
            "cash": self.cash,
            "frozen": self.frozen,
            "profit": self.profit,
            "worth": self.worth,
            "positions": self.positions,
            "selector": self.selector,
            "portfolio_id": self.portfolio_id,
            "engine_id": self.engine_id,
        }
        return info
