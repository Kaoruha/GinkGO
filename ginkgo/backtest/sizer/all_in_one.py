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
        date = self._get_trade_date(event=event)
        order = OrderEvent(date=date, deal=deal, code=code)
        if deal == DealType.BUY:
            order.capital = capital
        elif deal == DealType.SELL:
            try:
                order.volume = position[event.code].volumn
            except Exception as e:
                return
        self._engine.put(order)
