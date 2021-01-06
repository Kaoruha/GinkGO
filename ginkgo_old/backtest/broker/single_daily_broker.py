"""
低频日交易数据经纪人

模拟的是每日收盘获得信息
收盘后根据策略产生交易信号
第二天开盘尝试成交
"""

from .base_broker import BaseBroker
from ginkgo.backtest.events import *
import queue
from ginkgo.backtest.enums import MarketType, InfoType
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.postion import Position


class SingleDailyBroker(BaseBroker):
    """
    低频日交易数据经纪人类

    :param BaseBroker: [description]
    :type BaseBroker: [type]
    """
    def __init__(self,
                 name: str,
                 engine: EventEngine,
                 *,
                 stamp_tax_rate: float = .0015,
                 fee_rate: float = .00025,
                 init_capital: int = 100000):
        BaseBroker.__init__(self,
                            name=name,
                            engine=engine,
                            stamp_tax_rate=stamp_tax_rate,
                            fee_rate=fee_rate,
                            init_capital=init_capital)
        self.current_date = ''
        self.current_price = 0
        self.stand_by_order = queue.Queue() # 待处理订单

    def general_handler(self, event):
        pass

    def market_handlers(self, event: MarketEvent):
        """
        市场事件处理函数

        市场事件目前分为价格信息以及消息信息，
        此处只处理价格信息。

        :param event: 获得的新的日交易数据
        :type event: MarketEvent
        """
        # 检查市场事件的类型，此处只处理日交易数据
        if event.info_type is not InfoType.DailyPrice:
            return
        data = event.data[1]
        self.current_price = data['close']
        self.current_date = data['date']

        # 将待办订单重新推回引擎
        while True:
            try:
                order = self.stand_by_order.get(block=False)
                self._engine.put(order)
            except queue.Empty:
                break
        print(f'\r{self.current_date}.', end='')
        # 将新获取的价格信息传递给每个策略
        for strategy in self._strategies:
            position = self.position[
                data.code] if data.code in self.position else None
            strategy.data_transfer(data, position=position)

    def signal_handlers(self, event: SignalEvent):
        """
        信号事件处理函数
        
        从回测引擎获取到的信号事件，
        将转交给仓位管理策略，
        由仓位管理策略来确定目标持仓，产生订单。

        :param event: 由引擎传递过来的信号事件
        :type event: SignalEvent
        """
        self._sizer.get_signal(event=event,
                              capital=self._capital,
                              position=self.position)

    def order_handlers(self, event: OrderEvent):
        """
        订单事件处理函数

        如果当前日期与下单事件的日期相同，则把订单事件交给撮合类，尝试成交
        发出下单前需要冻结，买入冻结资金，卖出冻结持仓。
        """
        # 如果当前日期为预计交易日期，则尝试撮合配对，否则将下单事件存放在一个队列里，下一个周期重新推回引擎
        if self.current_date == event.date:
            try:
                # 获取当前代理持仓中，预计交易的股票代码的交易信息
                position = self.position[event.code]
            except Exception as e:
                # print(e)
                position = None
            if event.deal == DealType.BUY:
                # 当下单事件为多头事件时
                # 1、冻结资金
                self._freeze += event.ready_capital
                self._capital -= event.ready_capital

                # 2、尝试成交
                self._matcher.try_match(event=event, position=position)
            elif event.deal == DealType.SELL:
                # 冻结股票
                if position is None:
                    print(f'当前未持有{event.code}股票')
                    return
                if position.volume < event.target_volume:
                    position.ready_to_sell(target_volume=position.target_volume)
                else:
                    position.ready_to_sell(target_volume=event.target_volume)
                self._matcher.try_match(event=event, position=position)

        else:
            # 如果订单日期与当前日期不符合，则把订单事件存放在待办订单，待下次信息事件更新时，重新推回引擎
            self.stand_by_order.put(event)

    def fill_handlers(self, event: FillEvent):
        """
        成交事件处理函数
        """
        self.trade_history.append(event)
        self._capital += event.remain
        self._capital = round(self._capital, 2)

        # 统计该次交易税费
        self.fee += event.fee
        if event.done:
            # 交易成功的处理
            if event.deal == DealType.BUY:
                # 如果是买入事件则增加持仓
                if event.code in self.position:
                    # 如果持有该股票，增加持仓
                    self.position[event.code].buy(price=event.price,
                                                  volume=event.volume)
                else:
                    # 如果未持有该股票，建仓
                    new_position = Position(code=event.code,
                                            price=event.price,
                                            volume=event.volume)
                    self.position[event.code] = new_position

            elif event.deal == DealType.SELL:
                # 如果是卖出事件则减少持仓
                self.position[event.code].sell(volume=event.volume)
                if self.position[event.code].volume + self.position[event.code].freeze == 0:
                    del self.position[event.code]
        else:
            # 交易失败的处理
            if event.deal == DealType.BUY:
                # 解锁冻结资金
                self._freeze -= event.remain
                self._capital += event.remain
            elif event.deal == DealType.SELL:
                # 解锁冻结股票
                self.position[event.code].volume += event.volume
                self.position[event.code].freeze -= event.volume

        # 从回测引擎获取交易订单类
        # 根据成交金额与成交量，更新账号现金与持仓
        dealdir = '买入' if event.deal == DealType.BUY else '卖出'
        total = self.position[event.code].volume + self.position[
            event.code].freeze if event.code in self.position else 0

        result = '成交' if event.done else '失败'
        profit = (total * self.current_price + self._capital -
                  self._init_capital) / self._init_capital * 100
        print('{} Price:{}  Volume:{}  Result:{}  Profit:{}%  Fee:{}  Source:{}'.
            format(dealdir, round(event.price, 2), event.volume, result,
                   round(profit, 2), round(self.fee, 2), event.source))