import datetime
from ginkgo.backtest.order import Order
from ginkgo.backtest.position import Position
from ginkgo.backtest.strategies import StrategyBase
from ginkgo.backtest.signal import Signal
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.backtest.sizers import SizerBase
from ginkgo.libs.ginkgo_links import GinkgoSingleLinkedList
from ginkgo import GLOG
from ginkgo.libs import cal_fee


class BasePortfolio(object):
    def __init__(self, *args, **kwargs) -> None:
        self.name: str = "HaloPortfolio"
        self.cash: float = 100000
        self.frozen: float = 0
        self._position: dict = {}
        self._strategies = GinkgoSingleLinkedList()
        self._sizer = None

    @property
    def position(self) -> dict:
        return self._position

    @property
    def strategies(self) -> dict:
        return self._strategies

    @property
    def sizer(self) -> SizerBase:
        return self._sizer

    def set_sizer(self, sizer: SizerBase) -> None:
        self._sizer = sizer

    def add_strategy(self, strategy: StrategyBase) -> None:
        self.strategies.append(strategy)

    def add_position(self, position: Position):
        pass

    def get_position(self, code: str) -> Position:
        raise NotImplemented

    def on_signal(self, code: str) -> Order:
        raise NotImplemented
