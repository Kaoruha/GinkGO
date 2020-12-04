import datetime
from .base_sizer import BaseSizer
from ginkgo.backtest.events import SignalEvent, OrderEvent
from ginkgo.backtest.enums import DealType


class AllInOne(BaseSizer):
    """
    AllIn 策略

    所有资金全买一只股票，主要用来测试引擎流程

    :param BaseSizer: [description]
    :type BaseSizer: [type]
    """
    def __init__(self):
        BaseSizer.__init__(self)
        self.hold_pct = 0

    def get_signal(self, event: SignalEvent, capital: float, position):
        self.hold_pct = capital / self._init_capital
        source = event.source # 信号事件的来源，在信号事件产生的时候生成
        deal = event.deal # 信号的交易方向，是买入信号还是卖出信号
        code = event.code # 信号事件指向的股票代码
        current_price = event.current_price # 产生信号时该股票的收盘价格
        date = self._get_trade_date(event=event) # 信号产生时的下一个交易日日期

        if deal == DealType.BUY:
            # 如果手持资金能买两手，则将全部资金下单购买
            if capital >= current_price * 200:
                order = OrderEvent(date=date,
                                   deal=deal,
                                   source=source,
                                   ready_capital=capital,
                                   code=code)
                self._engine.put(order)
        elif deal == DealType.SELL:
            if event.code in position and position[event.code].volume > 0:
                # 如果持有股票，则全部卖出
                target_volume = position[event.code].volume
                order = OrderEvent(date=date,
                                   deal=deal,
                                   source=source,
                                   target_volume=target_volume,
                                   code=code)
                self._engine.put(order)
