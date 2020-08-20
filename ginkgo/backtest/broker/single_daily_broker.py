from .base_broker import BaseBroker
from ginkgo.backtest.event import *
from ginkgo.backtest.enums import MarketType
from ginkgo.backtest.event_engine import EventEngine


class SingleDailyBroker(BaseBroker):

    def general_handler(self, event):
        pass

    def market_handlers(self, event: MarketEvent):
        pass

    def signal_handlers(self, event: SignalEvent):
        print(event.date)
        # 从回测引擎获取信号事件
        # 如果是多头信号，判断当前日期是否在信号日期之后
        # 如果当前日期在信号日期之后，则将信号事件转交仓位管理，由仓位管理确定目标持仓，产生多头订单
        # 如果不是则将信号事件推回给引擎
        # 如果是空头信号，判断日期，如果满足第二天之后，交仓位管理，产生空头订单
        print('处理信号')

    def order_handlers(self, event: OrderEvent):
        # 从回测引擎获取订单事件
        # 如果是多头订单，根据价格和购买量，冻结资金，交给撮合类 TODO
        # 撮合类加入滑点、当日Bar等影响因素，产生交易订单
        # 如果是空头订单，交给撮合类
        # 撮合类根据滑点当日Bar等影响因素，产生交易订单
        pass

    def fill_handlers(self, event):
        # 从回测引擎获取交易订单类
        # 根据成交金额与成交量，更新账号现金与持仓
        pass

    def daily_handlers(self, event: MarketEvent):
        data = event.data[1]
        for strategy in self._strategy:
            strategy.data_transfer(data)
