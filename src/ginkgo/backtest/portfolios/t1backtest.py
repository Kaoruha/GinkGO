"""
The `Portfolio` class is responsible for managing the positions and capital for the system.(Backtest and Live)

- Initializing the portfolio with an initial capital amount and a set of securities to track.

- Keeping track of the current positions and cash balance for the portfolio.

- Executing trades based on signals generated by the Strategy.

- Generating reports and metrics related to the performance of the portfolio. The reports also contain charts.
"""

import time
from rich.console import Console


from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.position import Position
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.events import (
    EventOrderSubmitted,
    EventOrderFilled,
    EventSignalGeneration,
    EventPriceUpdate,
    EventOrderCanceled,
)

from ginkgo.libs import GinkgoSingleLinkedList, datetime_normalize, GLOG, base_repr
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.data.models import MOrder
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    RECORDSTAGE_TYPES,
)


console = Console()


class PortfolioT1Backtest(BasePortfolio):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, *args, **kwargs):
        super(PortfolioT1Backtest, self).__init__(*args, **kwargs)
        self._signals = []
        self._orders = []

    @property
    def signals(self):
        return self._signals

    @property
    def orders(self):
        return self._orders

    def get_position(self, code: str) -> Position:
        """
        Get Position object from portfolio.
        Args:
            code(str): code
        Returns:
            return POSITION if it exsist else return NONE
        """
        if code in self.positions.keys():
            return self.positions[code]
        return None

    def on_time_goes_by(self, time: any, *args, **kwargs) -> None:
        """
        Go next frame.
        Args:
            time(any): new time
        Return:
            None
        """
        # Go next TimePhase
        super(PortfolioT1Backtest, self).on_time_goes_by(time, *args, **kwargs)
        self.update_worth()
        self.update_profit()

        # Put old SIGNALs to engine
        # What a new fucking day
        for signal in self.signals:
            import pdb

            pdb.set_trace()
            e = EventSignalGeneration(signal)
            self.put(e)

        # Reset past signals
        self._signals = []
        print(self)

    def on_signal(self, event: EventSignalGeneration):
        """
        Dealing with the signal coming.
        1. get a signal
        2. after sizer and risk manager
        3.1 drop the signal
        3.2 put order to event engine
        """
        print(event)
        import pdb

        pdb.set_trace()
        GLOG.INFO(f"{self.name} got a {event.direction} signal about {event.code}  --> {event.direction}.")
        # Check Feature Message.
        if self.is_event_from_future(event):
            return

        # Check Everything.
        if not self.is_all_set():
            return

        # T+1, Order will send after 1 day that signal comes.
        if event.timestamp == self.now:
            GLOG.INFO(
                f"T+1 Portfolio can not send the order generated from the signal today {event.timestamp}, we will send the order tomorrow"
            )
            self.signals.append(event)
            return

        # if the signal from past , and the stock has no price today, put it back to to_send signals.
        # if not self.engine.datafeeder.is_code_on_market(event.code, self.now):
        #     # There is no price data about code today, delay the signal
        #     self.signals.append(event.value)
        #     return

        # 1. Transfer signal to sizer
        order = self.sizer.cal(event.value)
        # 2. Get the order return
        if order is None:
            return
        GLOG.INFO(f"Gen an ORDER by sizer.")

        # 3. Transfer the order to risk_manager
        order_adjusted = self.risk_manager.cal(order)

        # 4. Get the adjusted order, if so put eventorder to engine
        if order_adjusted is None:
            return
        GLOG.INFO(f"Gen an ORDER_ADJUSTED by risk.")

        # Prevent Doing Zero Volume Order
        if order_adjusted.volume == 0:
            return

        # 5. Create order, stored into db
        if order_adjusted.direction == DIRECTION_TYPES.LONG:
            GLOG.WARN("Got a LONG ORDER")
            freeze_ok = self.freeze(order_adjusted.frozen)
            GLOG.WARN("Got a LONG ORDER  After freeze")
            if not freeze_ok:
                return
            mo = MOrder()
            mo.set(
                order_adjusted.uuid,
                order_adjusted.code,
                order_adjusted.direction,
                order_adjusted.type,
                order_adjusted.status,
                order_adjusted.volume,
                order_adjusted.limit_price,
                order_adjusted.frozen,
                order_adjusted.transaction_price,
                order_adjusted.remain,
                order_adjusted.fee,
                self.now,
                self.engine_id,
            )
            GDATA.add(mo)

            # 6. Create Event
            e = EventOrderSubmitted(order_adjusted.uuid)
            GNOTIFIER.beep()
            GLOG.INFO("Gen an Event Order Submitted...")
            self.put(e)

        elif order_adjusted.direction == DIRECTION_TYPES.SHORT:
            GLOG.WARN("Got a SHORT SIGNAL")
            pos = self.get_position(order_adjusted.code)
            volume_freezed = pos.freeze(order_adjusted.volume)
            GLOG.WARN("Got a SHORT ORDER Done..")
            mo = MOrder()
            mo.set(
                order_adjusted.uuid,
                order_adjusted.code,
                order_adjusted.direction,
                order_adjusted.type,
                order_adjusted.status,
                volume_freezed,
                order_adjusted.limit_price,
                order_adjusted.frozen,
                order_adjusted.transaction_price,
                order_adjusted.remain,
                order_adjusted.fee,
                self.now,
                self.engine_id,
            )
            GDATA.add(mo)
            e = EventOrderSubmitted(order_adjusted.uuid)
            GNOTIFIER.beep()
            # 6. Create Event
            self.put(e)
            GLOG.WARN("Send a Short ORDER.")
            self.orders.append(order_adjusted.uuid)  # Seems not work.

    def on_price_update(self, event: EventPriceUpdate):
        # Check Everything.
        # TODO
        return

        if not self.is_all_set():
            return

        # 0 Time check
        if self.is_event_from_future(event):
            return

        # 1. Update position price
        if event.code in self.positions:
            self.positions[event.code].on_price_update(event.close)

        # 2. Transfer price to each strategy
        if len(self.strategies) == 0:
            return

        # GLOG.INFO(f"Under {len(self.strategies)} Strategies Calculating... {self.now}")
        for strategy in self.strategies:
            # 3. Get signal return, if so put eventsignal to engine
            signal = strategy.value.cal(event.code)
            if signal:
                e = EventSignalGeneration(signal)
                e.set_source(SOURCE_TYPES.PORTFOLIO)
                GDATA.add_signal(
                    self.backtest_id,
                    self.now,
                    e.code,
                    e.direction,
                    f"{strategy.value.name} gen.",
                )
                self.put(e)
        # GLOG.INFO(f"Strategies Calculating Complete. {self.now}")
        self.update_worth()
        self.update_profit()

    def on_order_filled(self, event: EventOrderFilled):
        GLOG.INFO("Got An Order Filled...")
        import pdb

        pdb.set_trace()
        if self.is_event_from_future(event):
            return

        if not event.order_status == ORDERSTATUS_TYPES.FILLED:
            GLOG.CRITICAL(
                f"On Order Filled only handle the FILLEDORDER, cant handle a {event.order_status} one. Check the Code"
            )
            return
        if event.direction == DIRECTION_TYPES.LONG:
            GLOG.WARN("DEALING with LONG FILLED ORDER")
            # print(event.value)
            self.unfreeze(event.frozen)
            self.add_cash(event.remain)
            self.add_fee(event.fee)
            p = Position(code=event.code, price=event.transaction_price, volume=event.volume)
            p.set_backtest_id(self.backtest_id)
            self.add_position(p)
            GLOG.WARN("Fill a LONG ORDER DONE")
        elif event.direction == DIRECTION_TYPES.SHORT:
            GLOG.WARN("DEALING with SHORT FILLED ORDER")
            self.add_cash(event.remain)
            self.add_fee(event.fee)
            self.positions[event.code].deal(DIRECTION_TYPES.SHORT, event.transaction_price, event.volume)
            self.clean_positions()
            GLOG.WARN("Fill a SHORT ORDER DONE")
        GLOG.INFO("Got An Order Filled Done")
        self.update_worth()
        self.update_profit()
        print(event)
        print(self)

    def on_order_canceled(self, event: EventOrderCanceled):
        GLOG.WARN("Dealing with CANCELED ORDER.")
        import pdb

        pdb.set_trace()
        if self.is_event_from_future(event):
            return
        if event.direction == DIRECTION_TYPES.LONG:
            GLOG.WARN("START UNFREEZE LONG.")
            self.unfreeze(event.frozen)
            self.add_cash(event.frozen)
            GLOG.WARN("DONE UNFREEZE LONG.")
        elif event.direction == DIRECTION_TYPES.SHORT:
            GLOG.WARN("START UNFREEZE SHOTR.")
            code = event.code
            pos = self.positions[code]
            pos.unfreeze(event.volume)
            GLOG.WARN("DONE UNFREEZE SHORT.")
        self.update_worth()
        self.update_profit()

    def __repr__(self) -> str:
        return base_repr(self, PortfolioT1Backtest.__name__, 24, 70)
