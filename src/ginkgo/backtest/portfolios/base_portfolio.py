import uuid
import datetime
from rich.console import Console
from typing import TYPE_CHECKING, List, Dict
from decimal import Decimal


if TYPE_CHECKING:
    from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
    from ginkgo.backtest.strategies import StrategyBase


from ginkgo.backtest.engines.base_engine import BaseEngine
from ginkgo.backtest.selectors import BaseSelector
from ginkgo.backtest.backtest_base import BacktestBase
from ginkgo.backtest.risk_managements.base_risk import BaseRiskManagement
from ginkgo.backtest.sizers.base_sizer import BaseSizer
from ginkgo.backtest.events.base_event import EventBase
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.order import Order
from ginkgo.backtest.position import Position
from ginkgo.enums import DIRECTION_TYPES, RECORDSTAGE_TYPES
from ginkgo.libs import GCONF, to_decimal


console = Console()


class BasePortfolio(BacktestBase):
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
        self._strategies = []
        self._sizer = None
        self._risk_manager = None
        self._selector = None
        self._analyzers: Dict[str, "BaseAnalyzer"] = {}
        self._analyzer_hook: Dict[RECORDSTAGE_TYPES, List] = {i: [] for i in RECORDSTAGE_TYPES}
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
            self.log("INFO", f"Add FOUND {money}")
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

        if self.risk_manager is None:
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
            self.log("ERROR", f"EngineBind only support Type Engine, {type(BaseEngine)} {engine} is not supported.")
            return
        super(BasePortfolio, self).bind_engine(engine)
        for i in self.strategies:
            i.bind_engine(engine)
        if self._selector is not None:
            self._selector.bind_engine(engine)
        if self._sizer is not None:
            self._sizer.bind_engine(engine)
        for i in self._analyzers:
            self._analyzers[i].bind_engine(engine)

    def bind_risk(self, risk: BaseRiskManagement) -> None:
        """
        Bind risk manager to portfolio.
        Args:
            risk(BaseRiskManagement): risk module
        Return:
            None
        """
        if not isinstance(risk, BaseRiskManagement):
            self.log("ERROR", f"Risk bind only support Riskmanagement, {type(risk)} {risk} is not supported.")
            return
        self._risk_manager = risk

    @property
    def risk_manager(self) -> BaseRiskManagement:
        return self._risk_manager

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

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            self.log("ERROR", f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

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
            analyzer.set_portfolio_id(self.portfolio_id)
            self._analyzers[analyzer.name] = analyzer
            for i in analyzer.active_stage:
                self._analyzer_hook[i].append(analyzer.activate)
                self.log("DEBUG", f"Add Analyzer {analyzer.name} in stage {i}.")
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

    @property
    def positions(self) -> dict:
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
        raise NotImplemented

    def on_price_recived(self, price: Bar) -> Position:
        raise NotImplemented

    def on_signal(self, code: str) -> Order:
        raise NotImplemented

    def on_order_filled(self, order):
        raise NotImplemented

    def on_order_canceled(self, order):
        raise NotImplemented

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
        codes = self.selector.pick()
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
        }
        return info
