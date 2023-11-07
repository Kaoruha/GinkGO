import datetime
import pandas as pd
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.order import Order
from ginkgo.backtest.position import Position
from ginkgo.backtest.strategies import StrategyBase
from ginkgo.backtest.engines.base_engine import BaseEngine
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.sizers import BaseSizer
from ginkgo.backtest.selectors import BaseSelector
from ginkgo.backtest.risk_managements.base_risk import BaseRiskManagement
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.libs import cal_fee, datetime_normalize, GinkgoSingleLinkedList
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.backtest_base import BacktestBase


class BasePortfolio(BacktestBase):
    def __init__(self, *args, **kwargs) -> None:
        super(BasePortfolio, self).__init__(*args, **kwargs)
        self.set_name("HaloPortfolio")
        self._cash: float = 100000
        self._frozen: float = 0
        self._positions: dict = {}
        self._strategies = GinkgoSingleLinkedList()
        self._sizer = None
        self._risk_manager = None
        self._selector = None
        self.indexes: dict = {}
        self._engine = None
        self._interested = GinkgoSingleLinkedList()
        self._fee = 0

    def get_count_of_price(self, date):
        raise NotImplemented

    @property
    def profit(self) -> float:
        profit = 0
        for i in self.positions.keys():
            profit += self.positions[i].profit
        return profit

    @property
    def worth(self) -> float:
        r = 0
        r += self.cash + self.frozen
        for key in self.positions:
            r += self.positions[key].worth
        return round(r, 4)

    def add_found(self, money: float) -> float:
        if money < 0:
            GLOG.ERROR(f"The money should not under 0. {money} is illegal.")
        else:
            GLOG.WARN(f"Add FOUND {money}")
            self._cash += money
        return self.cash

    def add_cash(self, money: float) -> float:
        if money < 0:
            GLOG.ERROR(f"The money should not under 0. {money} is illegal.")
        else:
            GLOG.WARN(f"Add FOUND {money}")
            self._cash += money
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
        return the total fee of each trade
        """
        return self._fee

    def add_fee(self, fee: float) -> float:
        if fee < 0:
            GLOG.ERROR(f"The fee should not under 0. {fee} is illegal.")
        else:
            GLOG.WARN(f"Add FEE {fee}")
            self._fee += fee
        return self.fee

    @property
    def interested(self) -> GinkgoSingleLinkedList():
        return self._interested

    def is_all_set(self) -> bool:
        """
        check if all parts set
        """
        r = True
        if self.engine is None:
            GLOG.ERROR(f"Engine not bind. Events can not put back to the ENGINE.")
            r = False

        if self.sizer is None:
            GLOG.ERROR(
                f"Portfolio Sizer not set. Can not handle the signal. Please set the SIZER first."
            )
            r = False

        if self.risk_manager is None:
            GLOG.ERROR(
                f"Portfolio RiskManager not set. Can not Adjust the order. Please set the RISKMANAGER first."
            )
            r = False

        if self.selector is None:
            GLOG.ERROR(
                f"Portfolio Selector not set. Can not pick the code. Please set the SELECTOR first."
            )
            r = False

        if len(self.strategies) == 0:
            GLOG.WARN(f"No strategy register. No signal will come.")

        return r

    def bind_selector(self, selector: BaseSelector):
        if not isinstance(selector, BaseSelector):
            GLOG.ERROR(
                f"Selector bind only support Selector, {type(selector)} {selector} is not supported."
            )
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
        if not isinstance(engine, BaseEngine):
            GLOG.ERROR(
                f"EngineBind only support Type Engine, {type(BaseEngine)} {engine} is not supported."
            )
            return
        self._engine = engine

    @property
    def engine(self):
        return self._engine

    def bind_risk(self, risk: BaseRiskManagement):
        if not isinstance(risk, BaseRiskManagement):
            GLOG.ERROR(
                f"Risk bind only support Riskmanagement, {type(risk)} {risk} is not supported."
            )
            return
        self._risk_manager = risk

    @property
    def risk_manager(self) -> BaseRiskManagement:
        return self._risk_manager

    def bind_sizer(self, sizer: BaseSizer) -> None:
        if not isinstance(sizer, BaseSizer):
            GLOG.ERROR(
                f"Sizer bind only support Sizer, {type(sizer)} {sizer} is not supported."
            )
            return
        self._sizer = sizer
        self.sizer.bind_portfolio(self)
        if self.engine:
            if self.engine.datafeeder:
                self.sizer.bind_datafeeder(self.engine.datafeeder)

    @property
    def sizer(self) -> BaseSizer:
        return self._sizer

    def freeze(self, money: float) -> bool:
        """
        Freeze the capital.
        """
        if money >= self.cash:
            GLOG.WARN(f"We cant freeze {money}, we only have {self.cash}.")
            return False
        else:
            GLOG.WARN(f"TRYING FREEZE {money}. CURRENFROZEN: {self._frozen} ")
            print(f"FF: {self._frozen} + {money}")
            self._frozen += money
            print(f"= {self._frozen}")
            self._cash -= money
            GLOG.WARN(f"DONE FREEZE {money}. CURRENFROZEN: {self._frozen} ")
            # self._frozen = round(self._frozen, 4)
            # self._cash = round(self._cash, 4)
            return True

    def unfreeze(self, money: float) -> float:
        """
        frozen --, capital ++
        """
        if money > self.frozen:
            if money - self.frozen > GCONF.EPSILON:
                GLOG.CRITICAL(
                    f"We cant unfreeze {money}, the max unfreeze is only {self.frozen}"
                )
            else:
                money = self.frozen
                self._frozen -= money
                GLOG.WARN(f"DONE UNFREEZE {money}. CURRENTFROZEN: {self.frozen}")
        else:
            GLOG.WARN(f"TRYING UNFREEZE {money}. CURRENTFROZEN: {self.frozen}")
            self._frozen -= money
            # self._frozen = round(self._frozen, 4)
            GLOG.WARN(f"DONE UNFREEZE {money}. CURRENTFROZEN: {self.frozen}")
        return self.frozen

    def put(self, event):
        """
        Put event to eventengine.
        """
        if self.engine is None:
            GLOG.ERROR(f"Engine not bind. Events can not put back to the engine.")
            return
        self.engine.put(event)

    def add_index(self, index):
        if index.name in self.indexes.keys():
            return
        self.indexes[index.name] = index
        index.bind_portfolio(self)

    def index(self, key: str):
        """
        return the index[key]
        """
        # TODO
        if key in self.indexes.keys():
            return self.indexes[key].value
        else:
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

    def add_strategy(self, strategy: StrategyBase) -> None:
        self.strategies.append(strategy)
        if strategy.portfolio is None:
            strategy.bind_portfolio(self)

    def add_position(self, position: Position):
        code = position.code
        if code not in self.positions.keys():
            self._positions[code] = position
        else:
            self._positions[code].deal(
                DIRECTION_TYPES.LONG, position.cost, position.volume
            )

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

    def on_time_goes_by(self, time: any, *args, **kwargs):
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

    def clean_positions(self) -> None:
        """
        if some position's volome and frozen == 0, remove it from positions of portfolio.
        """
        if len(self.positions.keys()) == 0:
            return
        del_list = []

        for key in self.positions.keys():
            pos = self.get_position(key)
            vol = pos.volume + pos.frozen
            if vol == 0:
                del_list.append(key)
        for code in del_list:
            del self.positions[code]
