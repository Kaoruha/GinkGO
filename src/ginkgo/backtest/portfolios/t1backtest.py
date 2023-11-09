"""
The `Portfolio` class is responsible for managing the positions and capital for the system.(Backtest and Live)

- Initializing the portfolio with an initial capital amount and a set of securities to track.

- Keeping track of the current positions and cash balance for the portfolio.

- Executing trades based on signals generated by the Strategy.

- Generating reports and metrics related to the performance of the portfolio. The reports also contain charts.
"""
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.bar import Bar
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.events import (
    EventOrderSubmitted,
    EventOrderFilled,
    EventSignalGeneration,
    EventPriceUpdate,
    EventOrderCanceled,
    EventNextPhase,
)
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MOrder
from ginkgo.libs import GinkgoSingleLinkedList, datetime_normalize
from ginkgo.backtest.signal import Signal
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    RECRODSTAGE_TYPES,
)
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.backtest.position import Position
from rich.console import Console
import time

console = Console()


class PortfolioT1Backtest(BasePortfolio):
    __abstract__ = False

    def __init__(self, *args, **kwargs):
        super(PortfolioT1Backtest, self).__init__(*args, **kwargs)
        self._signals = GinkgoSingleLinkedList()
        self._orders = GinkgoSingleLinkedList()
        # Records

        self.reset_phase_check()

    def try_go_next_phase(self) -> None:
        print("===================")
        print(f"Data: {self.now}")
        print(f"Today will get : {self._count_of_price_should_come_now} PRICE.")
        print(f"PriceGet: {self._price_get_count}")
        print(f"PriceGenSignal: {self._price_gen_signal_count}")
        print(f"PricePassed: {self._price_passed_count}")
        print(f"LastDay Signal: {self._lastday_signal_count}")
        print(f"SignalGet: {self._signal_get_count}")
        print(f"SignalGenOrder: {self._signal_gen_order_count}")
        print(f"SignalPassed: {self._signal_passed_count}")
        print(f"SignalTomorrow: {self._signal_tomorrow_count}")
        print(f"OrderSend: {self._order_send_count}")
        print(f"OrderFilled: {self._order_filled_count}")
        print(f"OrderCanceled: {self._order_canceled_count}")
        if self._should_go_next_phase > 0:
            print(self._should_go_next_phase)
            console.print(f"[green]YES[/green]")
            self.put(EventNextPhase())
        else:
            console.print(f"[red]NO[/red]")

        print(self)
        print("===================")

    @property
    def _should_go_next_phase(self) -> int:
        """
        # 1. Have no interested Targets. GO NEXT PHASE
        # 2. Feeder got no PRICE. GO NEXT PHASE
        # 3. Got PRICE but no SIGNAL generated. GO NEXT PHASE
        # 4. Got SIGNAL but no ORDER generated. GO NEXT PHASE
        # 5. Gen ORDER but no ORDER sended. GO NEXT PHASE
        # 6. Send ORDERs and Got Equal Filled and Canceled ORDER. GO NEXT PHASE
        """
        # 1
        if len(self.selector.pick()) == 0:
            return 1
        # 2
        elif (
            self._count_of_price_should_come_now == 0
            and self._lastday_signal_count == 0
        ):
            return 2
        # 3
        elif (
            self._price_get_count > 0
            and self._price_get_count == self._count_of_price_should_come_now
            and self._price_gen_signal_count == 0
            and self._lastday_signal_count == 0
        ):
            return 3
        # 4
        elif (
            self._signal_get_count > 0
            and self._signal_get_count
            == self._price_gen_signal_count + self._lastday_signal_count
            and self._price_get_count == self._count_of_price_should_come_now
            and self._price_gen_signal_count + self._lastday_signal_count
            == self._signal_get_count
            and self._signal_get_count
            - self._signal_passed_count
            - self._signal_tomorrow_count
            == self._signal_gen_order_count
            and self._signal_gen_order_count == 0
        ):
            return 4
        # 5
        elif (
            self._price_get_count == self._count_of_price_should_come_now
            and self._signal_gen_order_count > 0
            and self._order_send_count == 0
        ):
            return 5
        # 6
        elif (
            self._price_get_count == self._count_of_price_should_come_now
            and self._order_send_count > 0
            and self._order_send_count
            - self._order_filled_count
            - self._order_canceled_count
            == 0
        ):
            return 6
        return 0

    @property
    def _count_of_price_should_come_now(self) -> int:
        r = self.engine.datafeeder.get_count_of_price(self.now, self.interested)
        return r

    def reset_phase_check(self) -> None:
        """
        Reset all records every new frame.
        """
        # Records
        self._feeder_get_no_data_today = False
        self._price_get_count = 0
        self._price_gen_signal_count = 0
        self._price_passed_count = 0
        self._lastday_signal_count = 0
        self._signal_get_count = 0
        self._signal_gen_order_count = 0
        self._signal_passed_count = 0
        self._signal_tomorrow_count = 0
        self._order_send_count = 0
        self._order_filled_count = 0
        self._order_canceled_count = 0

    @property
    def signals(self):
        return self._signals

    @property
    def orders(self):
        return self._orders

    def get_position(self, code: str):
        if code in self.positions.keys():
            return self.positions[code]
        return None

    def on_time_goes_by(self, time: any, *args, **kwargs):
        """
        Go next frame.
        """
        # Time goes
        super(PortfolioT1Backtest, self).on_time_goes_by(time, *args, **kwargs)
        self.reset_phase_check()

        # Put old SIGNALs to engine
        if len(self.signals) == 0:
            self.try_go_next_phase()
            return

        for signal in self.signals:
            self._lastday_signal_count += 1
            e = EventSignalGeneration(signal.value)
            self.put(e)
        self._signals = GinkgoSingleLinkedList()
        self.try_go_next_phase()

    def on_signal(self, event: EventSignalGeneration):
        """
        Dealing with the signal coming.
        1. get a signal
        2. after sizer and risk manager
        3.1 drop the signal
        3.2 put order to event engine
        """
        self.record(RECRODSTAGE_TYPES.SIGNALGENERATION)
        self._signal_get_count += 1  # Record
        GLOG.INFO(
            f"{self.name} got a {event.direction} signal about {event.code}  --> {event.direction}."
        )
        # Check Everything.
        if not self.is_all_set():
            self.try_go_next_phase()
            return

        if event.timestamp > self.now:
            GLOG.WARN(
                f"Current time is {self.now.strftime('%Y-%m-%d %H:%M:%S')}, The EventSignal generated at {event.timestamp}, Can not handle the future infomation."
            )
            self._signal_passed_count += 1
            self.try_go_next_phase()
            return

        # T+1, Order will send after 1 day that signal comes.
        if event.timestamp == self.now:
            GLOG.INFO(
                f"T+1 Portfolio can not send the order generated from the signal today {event.timestamp}, we will send the order tomorrow"
            )
            self.signals.append(event.value)
            self._signal_tomorrow_count += 1
            self.try_go_next_phase()
            return

        # if the signal from past , and the stock has no price today, put it back to to_send signals.
        if not self.engine.datafeeder.is_code_on_market(event.code, self.now):
            self.signals.append(event.value)
            self._signal_tomorrow_count += 1
            self.try_go_next_phase()
            return

        # 1. Transfer signal to sizer
        order = self.sizer.cal(event.value)
        # 2. Get the order return
        if order is None:
            self._signal_passed_count += 1
            self.try_go_next_phase()
            return

        # 3. Transfer the order to risk_manager
        order_adjusted = self.risk_manager.cal(order)

        # 4. Get the adjusted order, if so put eventorder to engine
        if order_adjusted is None:
            self._signal_passed_count += 1
            self.try_go_next_phase()
            return

        if (
            order_adjusted.direction == DIRECTION_TYPES.SHORT
            and order_adjusted.volume == 0
        ):
            self._signal_passed_count += 1
            self.try_go_next_phase()
            return

        # 5. Create order, stored into db
        mo = MOrder()
        if order_adjusted.direction == DIRECTION_TYPES.LONG:
            GLOG.WARN("Got a LONG ORDER")
            freeze_ok = self.freeze(order_adjusted.frozen)
            GLOG.WARN("Got a LONG ORDER  After freeze")
            if not freeze_ok:
                self._signal_passed_count += 1
                self.try_go_next_phase()
                return
            mo.set(
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
                order_adjusted.uuid,
            )
            GDATA.add(mo)
            GDATA.commit()
            self._signal_gen_order_count += 1

            # 6. Create Event
            e = EventOrderSubmitted(mo.uuid)
            GLOG.INFO("Gen an Event Order Submitted...")
            self.put(e)
            self.record(RECRODSTAGE_TYPES.ORDERSEND)
            self._order_send_count += 1  # Record
            GLOG.WARN(f"Send : {self._order_send_count}")

        elif order_adjusted.direction == DIRECTION_TYPES.SHORT:
            GLOG.WARN("Got a SHORT ORDER")
            pos = self.get_position(order_adjusted.code)
            volume_freezed = pos.freeze(order_adjusted.volume)
            GLOG.WARN("Got a SHORT ORDER Done..")
            mo.set(
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
                order_adjusted.uuid,
            )
            GLOG.WARN("Send a Short ORDER.")
            GDATA.add(mo)
            GDATA.commit()
            self._signal_gen_order_count += 1
            e = EventOrderSubmitted(mo.uuid)
            # 6. Create Event
            self.put(e)
            self.record(RECRODSTAGE_TYPES.ORDERSEND)
            self.orders.append(order_adjusted.uuid)  # Seems not work.
            self._order_send_count += 1  # Record

            GLOG.WARN(f"Send : {self._order_send_count}")
        self.try_go_next_phase()

    def on_price_update(self, event: EventPriceUpdate):
        self._price_get_count += 1  # Record

        # Check Everything.
        if not self.is_all_set():
            self.try_go_next_phase()
            return

        # 0 Time check
        if event.timestamp > self.now:
            GLOG.WARN(
                f"Current time is {self.now.strftime('%Y-%m-%d %H:%M:%S')}, The EventPriceUpdate generated at {event.timestamp}, Can not handle the future infomation."
            )
            self._price_passed_count += 1
            self.try_go_next_phase()
            return

        # 1. Update position price
        if event.code in self.positions:
            self.positions[event.code].on_price_update(event.close)

        # 2. Transfer price to each strategy
        if len(self.strategies) <= 0:
            self._price_passed_count += 1
            self.try_go_next_phase()
            return

        # GLOG.INFO(f"Under {len(self.strategies)} Strategies Calculating... {self.now}")
        for strategy in self.strategies:
            # 3. Get signal return, if so put eventsignal to engine
            signal = strategy.value.cal(event.value)
            if signal:
                e = EventSignalGeneration(signal)
                e.set_source(SOURCE_TYPES.PORTFOLIO)
                self.put(e)
                self._price_gen_signal_count += 1  # Record
        # GLOG.INFO(f"Strategies Calculating Complete. {self.now}")
        self.try_go_next_phase()

    def on_order_filled(self, event: EventOrderFilled):
        GLOG.INFO("Got An Order Filled...")
        if not event.order_status == ORDERSTATUS_TYPES.FILLED:
            GLOG.CRITICAL(
                f"On Order Filled only handle the FILLEDORDER, cant handle a {event.order_status} one. Check the Code"
            )
            self.try_go_next_phase()
            return
        self.record(RECRODSTAGE_TYPES.ORDERFILLED)
        if event.direction == DIRECTION_TYPES.LONG:
            GLOG.WARN("DEALING with LONG FILLED ORDER")
            print(event.value)
            self.unfreeze(event.frozen)
            self.add_found(event.remain)
            self.add_fee(event.fee)
            p = Position(
                code=event.code, price=event.transaction_price, volume=event.volume
            )
            self.add_position(p)
            GLOG.WARN("Fill a LONG ORDER DONE")
        elif event.direction == DIRECTION_TYPES.SHORT:
            GLOG.WARN("DEALING with SHORT FILLED ORDER")
            self.add_found(event.remain)
            self.add_fee(event.fee)
            self.positions[event.code].deal(
                DIRECTION_TYPES.SHORT, event.transaction_price, event.volume
            )
            self.clean_positions()
            GLOG.WARN("Fill a SHORT ORDER DONE")
        GLOG.INFO("Got An Order Filled Done")
        self._order_filled_count += 1  # Record
        self.try_go_next_phase()

    def on_order_canceled(self, event: EventOrderCanceled):
        GLOG.WARN(
            f"Filled: {self._order_filled_count}  Canceled: {self._order_canceled_count}"
        )
        # TODO LONG SHORT
        GLOG.WARN("Dealing with CANCELED ORDER.")
        self.record(RECRODSTAGE_TYPES.ORDERCANCELED)
        if event.direction == DIRECTION_TYPES.LONG:
            GLOG.WARN("START UNFREEZE LONG.")
            self.unfreeze(event.frozen)
            self.add_found(event.frozen)
            GLOG.WARN("DONE UNFREEZE LONG.")
        elif event.direction == DIRECTION_TYPES.SHORT:
            GLOG.WARN("START UNFREEZE SHOTR.")
            code = event.code
            pos = self.positions[code]
            pos.unfreeze(event.volume)
            GLOG.WARN("DONE UNFREEZE SHORT.")
        self._order_canceled_count += 1  # Record
        self.try_go_next_phase()

    def __repr__(self) -> str:
        return base_repr(self, PortfolioT1Backtest.__name__, 24, 60)
