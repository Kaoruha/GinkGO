import datetime
from .base_sizer import BaseSizer
from ginkgo.backtest.event import SignalEvent, OrderEvent
from ginkgo.backtest.enums import DealType
from ginkgo.data.data_portal import data_portal


class AllInOne(BaseSizer):
    def get_signal(self, event: SignalEvent, capital: float, position):
        self.hold_pct = capital / self._init_capital
        deal = event.deal
        code = event.code
        current_price = event.current_price
        date = self._get_trade_date(event=event)
        
        if deal == DealType.BUY:
            if capital >= current_price * 200:
                order = OrderEvent(date=date, deal=deal,capital=capital, code=code)
                self._engine.put(order)
        elif deal == DealType.SELL:
            if event.code in position:
                # 如果持有股票，则全部卖出
                volume = position[event.code].volume
                order = OrderEvent(date=date, deal=deal,volume=volume, code=code)
                self._engine.put(order)
        
