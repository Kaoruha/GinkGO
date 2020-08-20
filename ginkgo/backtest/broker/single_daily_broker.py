from .base_broker import BaseBroker
from ginkgo.backtest.event import *
from ginkgo.libs.enums import MarketType


class SingleDailyBroker(BaseBroker):
    def __init__(self, name: str, *, stamp_tax: float = .0015, fee: float = .00025, init_capital: int = 100000):
        self.name = name
        self._stamp_tax = stamp_tax  # 设置印花税，默认千1.5
        self._fee = fee  # 设置交易税,默认万2.5
        self._capital = init_capital  # 设置初始资金，默认100K
        self._freeze = 0
        self._strategy = []
        self._sizer = None
        self._risk = []
        self.position = []  # 存放Position
        self.trades = []  # 'code': ['date', 'price', 'amount', 'order_id', 'trade_id']
        self.market_type = MarketType.Stock_CN  # 以后会支持港股美股日股等乱七八糟的市场

    def general_handler(self, event):
        pass

    def market_handlers(self, event: MarketEvent):
        pass

    def signal_handlers(self, event: SignalEvent):
        self.count += 1
        print(self.count)

    def order_handlers(self, event: OrderEvent):
        pass

    def fill_handlers(self, event):
        pass

    def daily_handlers(self, event: DailyEvent):
        data = event.data[1]
        for strategy in self._strategy:
            strategy.data_transfer(data)
