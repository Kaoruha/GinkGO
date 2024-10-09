import uuid
import datetime
from rich.console import Console
from typing import TYPE_CHECKING


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
from ginkgo.libs import GinkgoSingleLinkedList
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.ginkgo_data import GDATA


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
        self._cash: float = 100000
        self._worth: float = 100000
        self._profit: float = 0
        self._frozen: float = 0
        self._positions: dict = {}
        self._strategies = GinkgoSingleLinkedList()
        self._sizer = None
        self._risk_manager = None
        self._selector = None
        self.analyzers: dict = {}
        self._engine = None
        self._interested = GinkgoSingleLinkedList()
        self._fee = 0

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

    def get_count_of_price(self, date: any) -> int:
        raise NotImplemented("Must implement the Function to get the count of coming price info.")

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

    def update_profit(self) -> None:
        """
        Update the PROFIT of Portfolio
        Args:
            None
        Return:
            None
        """
        self._profit = 0
        for key in self.positions:
            self._profit += self.positions[key].profit
        if not isinstance(self.profit, (float, int)):
            pass

    @property
    def profit(self) -> float:
        return self._profit

    @property
    def worth(self) -> float:
        return self._worth

    def add_found(self, money: float) -> float:
        """
        [Obsolete]Add Found.
        Args:
            money(float): Income money.
        Returns:
            current cash
        """
        if money <= 0:
            GLOG.ERROR(f"The money should not under 0. {money} is illegal.")
            return 0
        GLOG.DEBUG(f"Add FOUND {money}")
        self._cash += money
        self.update_worth()
        return self.cash

    def add_cash(self, money: float) -> float:
        """
        Add Found.
        Args:
            money(float): Income money.
        Returns:
            current cash
        """
        if money <= 0:
            GLOG.ERROR(f"The money should not under 0. {money} is illegal.")
        else:
            GLOG.DEBUG(f"Add FOUND {money}")
            self._cash += money
            self.update_worth()
        return self.cash

    @property
    def cash(self) -> float:
        """
        return the cash of portfolio
        """
        return self._cash

    @property
    def frozen(self) -> float:
        """
        return the money frozen of portfolio
        """
        return self._frozen

    @property
    def fee(self) -> float:
        """
        return the total fee
        """
        return self._fee

    def add_fee(self, fee: float) -> float:
        """
        Add fee.
        Args:
            fee(float): number of fee
        Returns:
            total fee of this portfolio
        """
        if fee < 0:
            GLOG.ERROR(f"The fee should not under 0. {fee} is illegal.")
        else:
            GLOG.DEBUG(f"Add FEE {fee}")
            self._fee += fee
        return self.fee

    @property
    def interested(self) -> GinkgoSingleLinkedList():
        """
        Interested Codes.
        """
        return self._interested

    def record(self, stage: RECORDSTAGE_TYPES) -> None:
        """
        Try do record. Iterrow each analyzer, do record.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            None
        """
        for k, v in self.analyzers.items():
            v.activate(stage)
            v.record(stage)

    def is_all_set(self) -> bool:
        """
        Check if all parts set
        Args:
            None
        Returns:
            Is all preparation complete?
        """
        if self.engine is None:
            GLOG.WARN(f"Engine not bind. Events can not put back to the ENGINE.")
            return False

        if self.sizer is None:
            GLOG.WARN(f"Portfolio Sizer not set. Can not handle the signal. Please set the SIZER first.")
            return False

        if self.risk_manager is None:
            GLOG.WARN(f"Portfolio RiskManager not set. Can not Adjust the order. Please set the RISKMANAGER first.")
            return False

        if self.selector is None:
            GLOG.WARN(f"Portfolio Selector not set. Can not pick the code. Please set the SELECTOR first.")
            return False

        if len(self.strategies) == 0:
            GLOG.WARN(f"No strategy register. No signal will come.")

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
            GLOG.ERROR(f"Selector bind only support Selector, {type(selector)} {selector} is not supported.")
            return
        self._selector = selector
        self._selector.bind_portfolio(self)

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
            GLOG.ERROR(f"EngineBind only support Type Engine, {type(BaseEngine)} {engine} is not supported.")
            return
        self._engine = engine
        self.set_backtest_id(engine.backtest_id)

    @property
    def engine(self):
        return self._engine

    def bind_risk(self, risk: BaseRiskManagement) -> None:
        """
        Bind risk manager to portfolio.
        Args:
            risk(BaseRiskManagement): risk module
        Return:
            None
        """
        if not isinstance(risk, BaseRiskManagement):
            GLOG.ERROR(f"Risk bind only support Riskmanagement, {type(risk)} {risk} is not supported.")
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
            GLOG.ERROR(f"Sizer bind only support Sizer, {type(sizer)} {sizer} is not supported.")
            return
        self._sizer = sizer
        self.sizer.bind_portfolio(self)

    @property
    def sizer(self) -> BaseSizer:
        return self._sizer

    def freeze(self, money: float) -> bool:
        """
        Freeze the capital.
        Args:
            money(float): ready to freeze target money
        Return:
            None
        """
        if money >= self.cash:
            GLOG.WARN(f"We cant freeze {money}, we only have {self.cash}.")
            return False
        GLOG.DEBUG(f"TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
        console.print(f":ice: TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
        self._frozen += money
        self._cash -= money
        GLOG.DEBUG(f"DONE FREEZE ${money}. CURRENFROZEN: ${self._frozen}. CURRENTCASH: ${self.cash} ")
        console.print(f":money_bag: DONE FREEZE ${money}. CURRENFROZEN: ${self._frozen}. CURRENTCASH: ${self.cash} ")
        return True

    def unfreeze(self, money: float) -> float:
        """
        Unfreeze the money.
        Args:
            money(float): unfreeze money.
        Return:
            Current frozen money.
        """
        if money > self.frozen:
            if money - self.frozen > GCONF.EPSILON:
                GLOG.ERROR(f"Cant unfreeze ${money}, the max unfreeze is only ${self.frozen}")
                console.print(f":prohibited: Cant unfreeze ${money}, the max unfreeze is only ${self.frozen}")
                return
            else:
                self._frozen = 0
                GLOG.DEBUG(f"DONE UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
        else:
            GLOG.DEBUG(f"TRYING UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
            self._frozen -= money
            # self._frozen = round(self._frozen, 4)
            GLOG.DEBUG(f"DONE UNFREEZE ${money}. CURRENTFROZEN: ${self.frozen}")
        return self.frozen

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self.engine is None:
            GLOG.ERROR(f"Engine not bind. Events can not put back to the engine.")
            return
        self.engine.put(event)

    def add_analyzer(self, analyzer: "BaseAnalyzer") -> None:
        """
        Add Analyzer.
        Args:
            analyzer(BaseAnalyzer): new analyzer
        Return:
            None
        """
        if analyzer.name in self.analyzers.keys():
            GLOG.WARN(f"Analyzer {analyzer.name} already in the analyzers. Please check.")
            return
        analyzer.set_backtest_id(self.backtest_id)
        self.analyzers[analyzer.name] = analyzer
        self.analyzers[analyzer.name].bind_portfolio(self)

    def analyzer(self, key: str) -> "BaseAnalyzer":
        """
        Get the analyzer.
        Args:
            key(str): key
        Return:
            The analyzer[key]
        """
        # TODO
        if key in self.analyzers.keys():
            return self.analyzers[key].value
        else:
            GLOG.ERROR(f"Analyzer {key} not in the analyzers. Please check.")
            return None

    @property
    def positions(self) -> dict:
        """
        Return Positions[dict] of portfolio
        """
        return self._positions

    @property
    def strategies(self) -> dict:
        """
        Return Strategies[dict] of portfolio
        """
        return self._strategies

    def add_strategy(self, strategy: "StrategyBase") -> None:
        if strategy in self.strategies:
            return
        self.strategies.append(strategy)
        if strategy.portfolio is None:
            strategy.bind_portfolio(self)

    def add_position(self, position: Position) -> None:
        code = position.code
        if code in self.positions.keys():
            self._positions[code].deal(DIRECTION_TYPES.LONG, position.cost, position.volume)
        else:
            self._positions[code] = position

    def get_position(self, code: str) -> Position:
        raise NotImplemented

    def on_price_update(self, price: Bar) -> Position:
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
        if not self.is_all_set():
            GLOG.WARN(f"{time} comes. But portfolio:{self.name} is no ready.")
            return
        self.sizer.on_time_goes_by(time)
        self._interested = GinkgoSingleLinkedList()
        codes = self.selector.pick()

        for code in codes:
            self._interested.append(code)

        for analyzer_key in self.analyzers.keys():
            self.analyzers[analyzer_key].on_time_goes_by(time)

        for strategy in self.strategies:
            strategy.value.on_time_goes_by(time, *args, **kwargs)

        self.update_profit()
        self.update_worth()
        self.record(RECORDSTAGE_TYPES.NEWDAY)

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
            vol = pos.volume + pos.frozen
            if vol == 0:
                del_list.append(key)
        for code in del_list:
            del self.positions[code]

    def set_backtest_id(self, value: str, *args, **kwargs) -> None:
        super(BasePortfolio, self).set_backtest_id(value, *args, **kwargs)
        # Pass the backtest id to analyzers, strategies and positions.
        for i in self.strategies:
            if i.value is not None:
                i.value.set_backtest_id(value)
        for i in self.analyzers.keys():
            self.analyzers[i].set_backtest_id(value)
        for i in self.positions.keys():
            self.positions[i].set_backtest_id(value)

    def record_positions(self) -> None:
        self.clean_positions()
        if len(self.positions) == 0:
            return
        l = []
        for i in self.positions.keys():
            l.append(self.positions[i])
        GDATA.add_position_records(self.uuid, self.now, l)

    def bought(self, code: str, price: str, volume: int, fee: float) -> None:
        if volume < 0:
            # LOG
            return
        if fee < 0:
            # LOG
            return
        pos = Position()
        pos.set(code, price, volume)
        self.add_position(pos)

    def sold(self, code: str, price: str, volume: int, fee: float) -> None:
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
                GLOG.ERROR(
                    f"Current time is {self.now.strftime('%Y-%m-%d %H:%M:%S')}, The Event {event.event_type} generated at {event.timestamp}, Can not handle the future infomation."
                )
                return True
        except Exception as e:
            print(e)
            return False
        finally:
            return False
