from .base_broker import BaseBroker
from ginkgo.backtest.event import *
import queue
from ginkgo.backtest.enums import MarketType
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.postion import Position


class SingleDailyBroker(BaseBroker):
    def __init__(self,
                 name: str,
                 engine: EventEngine,
                 *,
                 stamp_tax: float = .0015,
                 fee: float = .00025,
                 init_capital: int = 100000):
        BaseBroker.__init__(self,
                            name=name,
                            engine=engine,
                            stamp_tax=stamp_tax,
                            fee=fee,
                            init_capital=init_capital)
        self.current_date = ''
        self.stand_by_order = queue.Queue()
        self.trade_history = []

    def general_handler(self, event):
        pass

    def market_handlers(self, event: MarketEvent):
        pass

    def signal_handlers(self, event: SignalEvent):
        # 从回测引擎获取信号事件
        # 将信号事件转交仓位管理，由仓位管理确定目标持仓，产生订单
        self.sizer.get_signal(event=event,
                              capital=self._capital,
                              position=self.position)

    def order_handlers(self, event: OrderEvent):
        # 从回测引擎获取订单事件
        # 如果当前日期与订单与订单日期相同，则把订单事件交给撮合类，尝试成交
        # TODO 发出下单前需要冻结，买入冻结资金，卖出冻结持仓。Position持仓类需要加上freeze
        if self.current_date == event.date:
            try:
                position = self.position[event.code]
            except Exception as e:
                print(e)
                position = None
            if event.deal == DealType.BUY:
                self._matcher.try_match(event=event, position=position)
                # 同时冻结资金
                self._freeze += event.capital
                self._capital -= event.capital
            elif event.deal == DealType.SELL:
                self._matcher.try_match(event=event, position=position)
        else:
            # 如果订单日期与当前日期不符合，则把订单事件存放在待办订单，待下次信息事件更新时，重新推回引擎
            self.stand_by_order.put(event)

    def fill_handlers(self, event: FillEvent):
        self.trade_history.append(event)
        self._capital += event.remain
        self._capital = round(self._capital,2)
        self._freeze = 0
        if event.deal == DealType.BUY:
            # 增加持仓
            if event.code in self.position:
                self.position[event.code].buy(price=event.price,
                                              volume=event.volume)
            else:
                new_position = Position(code=event.code,
                                        price=event.price,
                                        volume=event.volume)
                self.position[event.code] = new_position

            pos = self.position[event.code]
            dealdir = '买入' if event.deal == DealType.BUY else '卖出'
        elif event.deal == DealType.SELL:
            # 减少持仓
            self.position[event.code].sell(volume=event.volume)
            if self.position[event.code] == 0:
                del self.position[event.code]
        # 从回测引擎获取交易订单类
        # 根据成交金额与成交量，更新账号现金与持仓
        pos = self.position[event.code]
        dealdir = '买入' if event.deal == DealType.BUY else '卖出'
        print(
            f'日期：{self.current_date}  {pos.code} {dealdir} 成交价：{event.price}  成交量：{event.volume}  当前资产：{pos.volume*pos.price+self._capital}'
        )

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
        print(f'\rToday is  {self.current_date}.', end='')
        # 将新获取等成交信息传递给每个策略
        for strategy in self._strategy:
            strategy.data_transfer(data)