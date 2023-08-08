import datetime
import pandas as pd
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.order import Order
from ginkgo.backtest.position import Position
from ginkgo.backtest.strategies import StrategyBase
from ginkgo.backtest.engines.base_engine import BaseEngine
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.sizers import BaseSizer
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
        self._now = None
        self.indexes: dict = {}
        self._engine = None

    def is_all_set(self) -> bool:
        r = True
        if self.engine is None:
            GLOG.CRITICAL(f"Engine not bind. Events can not put back to the engine.")
            r = False
        if self.sizer is None:
            GLOG.CRITICAL(
                f"Portfolio Sizer not set. Can not handle the signal. Please set the sizer first."
            )
            r = False
        if self.risk_manager is None:
            GLOG.CRITICAL(
                f"Portfolio RiskManager not set. Can not handle the signal. Please set the risk_manage first."
            )
            r = False
        if len(self.strategies) == 0:
            GLOG.WARN(f"No strategy register. Just for test.")
        return r

    def bind_engine(self, engine: BaseEngine):
        if engine:
            self._engine = engine

    def freeze(self, money: float) -> bool:
        if money >= self.cash:
            return False
        else:
            self.frozen += money
            self.cash -= money
            return True

    @property
    def engine(self):
        return self._engine

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
    def sizer(self) -> BaseSizer:
        return self._sizer

    @property
    def risk_manager(self) -> BaseRiskManagement:
        return self._risk_manager

    @property
    def now(self) -> datetime.datetime:
        return self._now

    def bind_risk(self, risk: BaseRiskManagement):
        self._risk_manager = risk

    def bind_sizer(self, sizer: BaseSizer) -> None:
        self._sizer = sizer
        self.sizer.bind_portfolio(self)

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
        time = datetime_normalize(time)
        if time is None:
            print("Format not support, can not update time")
            return
        if self._now is None:
            self._now = time
        else:
            if time < self.now:
                print("We can not go back such as a time traveller")
                return
            elif time == self.now:
                print("time not goes on")
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
