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
from ginkgo import GLOG


class BasePortfolio(object):
    def __init__(self, *args, **kwargs) -> None:
        self.name: str = "HaloPortfolio"
        self.cash: float = 100000
        self.frozen: float = 0
        self._position: dict = {}
        self._strategies = GinkgoSingleLinkedList()
        self._sizer = None
        self._risk_manager = None
        self._selector = None
        self._now = None
        self.indexes: dict = {}
        self._engine = None
        self._interested = GinkgoSingleLinkedList()

    @property
    def interested(self) -> GinkgoSingleLinkedList():
        return self._interested

    def is_all_set(self) -> bool:
        r = True
        if self.engine is None:
            GLOG.CRITICAL(f"Engine not bind. Events can not put back to the ENGINE.")
            r = False
        if self.sizer is None:
            GLOG.CRITICAL(
                f"Portfolio Sizer not set. Can not handle the signal. Please set the SIZER first."
            )
            r = False
        if self.risk_manager is None:
            GLOG.CRITICAL(
                f"Portfolio RiskManager not set. Can not Adjust the order. Please set the RISKMANAGER first."
            )
            r = False
        if self.selector is None:
            GLOG.CRITICAL(
                f"Portfolio Selector not set. Can not pick the code. Please set the SELECTOR first."
            )
            r = False
        if len(self.strategies) == 0:
            GLOG.WARN(f"No strategy register. Just for test.")
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

    @property
    def sizer(self) -> BaseSizer:
        return self._sizer

    def freeze(self, money: float) -> bool:
        if money >= self.cash:
            return False
        else:
            self.frozen += money
            self.cash -= money
            return True

    def put(self, event):
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
        return self.indexes[key].value

    @property
    def position(self) -> dict:
        return self._position

    @property
    def strategies(self) -> dict:
        return self._strategies

    @property
    def now(self) -> datetime.datetime:
        return self._now

    def add_strategy(self, strategy: StrategyBase) -> None:
        # TODO Remove the duplicated one
        self.strategies.append(strategy)

    def add_position(self, position: Position):
        code = position.code
        if code not in self.position.keys():
            self._position[code] = position
        else:
            self._position[code].deal(
                DIRECTION_TYPES.LONG, position.cost, position.volume
            )

    def on_time_goes_by(self, time: any, *args, **kwargs):
        if not self.is_all_set():
            return
        self._interested = self.selector.pick()
        time = datetime_normalize(time)
        if time is None:
            print("Format not support, can not update time")
            return
        if self._now is None:
            self._now = time
        else:
            if time < self.now:
                GLOG.ERROR("We can not go back such as a TIME TRAVALER.")
                return
            elif time == self.now:
                GLOG.WARN("The time not goes on.")
                return
            else:
                # Go next frame
                self._now = time

    def get_position(self, code: str) -> Position:
        raise NotImplemented

    def on_price_update(self, price: Bar) -> Position:
        raise NotImplemented

    def on_signal(self, code: str) -> Order:
        raise NotImplemented
