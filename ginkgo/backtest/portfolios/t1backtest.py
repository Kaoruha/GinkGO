"""
The `Portfolio` class is responsible for managing the positions and capital for the system.(Backtest and Live)

- Initializing the portfolio with an initial capital amount and a set of securities to track.

- Keeping track of the current positions and cash balance for the portfolio.

- Executing trades based on signals generated by the Strategy.

- Generating reports and metrics related to the performance of the portfolio. The reports also contain charts.
"""
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.bar import Bar
from ginkgo import GLOG
from ginkgo.backtest.events import (
    EventOrderSubmitted,
    EventSignalGeneration,
    EventPriceUpdate,
)
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MOrder
from ginkgo.libs import GinkgoSingleLinkedList, datetime_normalize
from ginkgo.backtest.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs.ginkgo_pretty import base_repr


class PortfolioT1Backtest(BasePortfolio):
    def __init__(self, *args, **kwargs):
        super(PortfolioT1Backtest, self).__init__(*args, **kwargs)
        self._signals = GinkgoSingleLinkedList()
        self._orders = GinkgoSingleLinkedList()

    @property
    def signals(self):
        return self._signals

    @property
    def orders(self):
        return self._orders

    def get_position(self, code: str):
        if code in self.position.keys():
            return self.position[code]
        return None

    def on_time_goes_by(self, time: any, *args, **kwargs):
        # Time goes
        super(PortfolioT1Backtest, self).on_time_goes_by(time, *args, **kwargs)
        # Put old signals to engine

        if len(self.signals) == 0:
            return

        for signal in self.signals:
            e = EventSignalGeneration(signal.value)
            self.engine.put(e)
        self._signals = GinkgoSingleLinkedList()

    def on_signal(self, event: EventSignalGeneration):
        GLOG.CRITICAL(f"{self.name} got a signal about {event.code}.")
        # Check Everything.
        if not self.is_all_set():
            return

        if event.timestamp > self.now:
            GLOG.WARN(
                f"Current time is {self.now.strftime('%Y-%m-%d %H:%M:%S')}, The EventSignal generated at {event.timestamp}, Can not handle the future infomation."
            )
            return

        # T+1, Order will send after 1 day that signal comes.
        if event.timestamp == self.now:
            GLOG.INFO(
                f"T+1 Portfolio can not send the order generated from the signal today {event.timestamp}, we will send the order tomorrow"
            )
            self.signals.append(event.value)
            return

        # 1. Transfer signal to sizer
        order = self.sizer.cal(event.value)
        # 2. Get the order return
        if order is None:
            return
        # # 3. Transfer the order to risk_manager
        # if self.risk_manager is None:
        #     GLOG.ERROR(
        #         f"Portfolio RiskManager not set. Can not handle the order. Please set the RiskManager first."
        #     )
        #     return
        # order_adjusted = self.risk_manager.cal(order)
        # # 4. Get the adjusted order, if so put eventorder to engine
        # if order_adjusted is None:
        #     return
        # # 5. Create order, stored into db
        # mo = MOrder()
        # if order_adjusted.direction == DIRECTION_TYPES.LONG:
        #     freeze_ok = self.freeze(order_adjusted.frozen)
        #     if not freeze_ok:
        #         return
        #     mo.set(
        #         order_adjusted.code,
        #         order_adjusted.direction,
        #         order_adjusted.type,
        #         order_adjusted.status,
        #         order_adjusted.volume,
        #         order_adjusted.limit_price,
        #         order_adjusted.frozen,
        #         order_adjusted.transaction_price,
        #         order_adjusted.remain,
        #         order_adjusted.fee,
        #         self.now,
        #         order_adjusted.uuid,
        #     )
        #     GDATA.add(mo)
        #     e = EventOrderSubmitted(mo.uuid)
        #     # 6. Create Event
        #     self.engine.put(e)
        # elif order_adjusted.direction == DIRECTION_TYPES.SHORT:
        #     pos: Position = self.get_position(order_adjusted.code)
        #     volume_freezed = pos.freeze(order_adjusted.volume)
        #     mo.set(
        #         order_adjusted.code,
        #         order_adjusted.direction,
        #         order_adjusted.type,
        #         order_adjusted.status,
        #         volume_freezed,
        #         order_adjusted.limit_price,
        #         order_adjusted.frozen,
        #         order_adjusted.transaction_price,
        #         order_adjusted.remain,
        #         order_adjusted.fee,
        #         self.now,
        #         order_adjusted.uuid,
        #     )
        #     GDATA.add(mo)
        #     e = EventOrderSubmitted(mo.uuid)
        #     # 6. Create Event
        #     self.engine.put(e)
        # self.orders.append(order_adjusted.uuid)

    def on_price_update(self, event: EventPriceUpdate):
        # Check Everything.
        if not self.is_all_set():
            return
        # 0 Time check
        if event.timestamp > self.now:
            GLOG.WARN(
                f"Current time is {self.now.strftime('%Y-%m-%d %H:%M:%S')}, The EventPriceUpdate generated at {event.timestamp}, Can not handle the future infomation."
            )
            return
        # 1. Update position price
        if event.code in self.position:
            self.position[event.code].on_price_update(event.close)
        # 2. Transfer price to each strategy
        if len(self.strategies) <= 0:
            return

        for strategy in self.strategies:
            # 3. Get signal return, if so put eventsignal to engine
            signal = strategy.value.cal(event.value)
            if signal:
                e = EventSignalGeneration(signal)
                e.set_source(SOURCE_TYPES.PORTFOLIO)
                self.engine.put(e)

    def __repr__(self) -> str:
        return base_repr(self, PortfolioT1Backtest.__name__, 12, 60)
