from .base_broker import BaseBroker
from ginkgo.backtest.event import *
import queue
from ginkgo.backtest.enums import MarketType
from ginkgo.backtest.event_engine import EventEngine


class SingleDailyBroker(BaseBroker):
    def __init__(self, name: str, engine: EventEngine, *, stamp_tax: float = .0015, fee: float = .00025,
                 init_capital: int = 100000):
        BaseBroker.__init__(self, name=name, engine=engine, stamp_tax=stamp_tax, fee=fee, init_capital=init_capital)
        self.current_date = ''
        self.stand_by_order = queue.Queue()
        self.trade_history = []

    def general_handler(self, event):
        pass

    def market_handlers(self, event: MarketEvent):
        pass

    def signal_handlers(self, event: SignalEvent):
        # 从回测引擎获取信号事件
        print(f'信号产生日期是{event.date}')
        # 将信号事件转交仓位管理，由仓位管理确定目标持仓，产生订单
        self.sizer.get_signal(event=event, capital=self._capital, position=self.position)
        pass

    def order_handlers(self, event: OrderEvent):
        # 从回测引擎获取订单事件
        # 如果当前日期与订单与订单日期相同，则把订单事件交给撮合类，尝试成交
        if self.current_date == event.date:
            try:
                position = self.position[event.code]
            except:
                position = None
            self._matcher.try_match(event=event, position=position)
            # 同时冻结资金
            self._freeze += event.capital
            self._capital -= event.capital
        else:
            # 如果订单日期与当前日期不符合，则把订单事件存放在待办订单，待下次信息事件更新时，重新推回引擎
            self.stand_by_order.put(event)

    def fill_handlers(self, event: FillEvent):
        self.trade_history.append(event)
        self._capital += event.remain
        self._freeze = 0
        if event.deal == DealType.BUY:
            # 增加持仓
            pass
        elif event.deal == DealType.SELL:
            # 减少持仓
            self.position[event.code].sell(volumn=event.volume)
            if self.position[event.code] == 0:
                del self.position[event.code]
            pass
        # 从回测引擎获取交易订单类
        # 根据成交金额与成交量，更新账号现金与持仓
        pass

    def daily_handlers(self, event: MarketEvent):
        # 获得新的日交易数据
        data = event.data[1]
        self.current_date = data['date']

        # 将待办订单重新推回引擎
        while True:
            try:
                order = self.stand_by_order.get(block=False)
                self._engine.put(order)
            except queue.Empty:
                break
        # print(f'\rToday is  {self.current_date}.', end='')
        print(f'Today is  {self.current_date}.')
        for strategy in self._strategy:
            strategy.data_transfer(data)
