import time
import datetime
from rich.console import Console
from typing import Dict

from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.bar import Bar
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.position import Position
from ginkgo.backtest.events import (
    EventOrderSubmitted,
    EventOrderFilled,
    EventSignalGeneration,
    EventPriceUpdate,
)

from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    RECORDSTAGE_TYPES,
)
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MOrder

from ginkgo.libs import GinkgoSingleLinkedList, datetime_normalize
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_pretty import base_repr

from ginkgo.notifier.ginkgo_notifier import GNOTIFIER

console = Console()


class PortfolioLive(BasePortfolio):
    """
    Portfolio for live system.
    """

    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, *args, **kwargs):
        super(PortfolioLive, self).__init__(*args, **kwargs)

    def reset_positions(self, *args, **kwargs) -> Dict[str, Position]:
        """
        Recover Positions from Order Records.
        Args:
            None
        Returns:
            Dict of Positions
        """
        # 1. Remove position data in db.
        result_pos = GDATA.remove_positions(backtest_id=self.uuid)
        # TODO
        # 2. Get Records from db.
        order_df = GDATA.get_orderrecord_df_pagination(portfolio_id=self.uuid)
        print(order_df)
        # 3. Recal positions
        l = []
        pos = []
        for code in order_df["code"].unique():
            temp_df = order_df[order_df["code"] == code]
            temp_df = temp_df.sort_values(by="timestamp", ascending=True)
            p = Position(code=code)
            p.set_backtest_id(self.uuid)
            for i, r in temp_df.iterrows():
                if r.direction == DIRECTION_TYPES.SHORT:
                    p.freeze(r.volume)
                p.deal(r.direction, r.transaction_price, r.volume)
            if p.volume <= 0:
                continue
            pos.append(p)
            self._positions[code] = p
        # 4. Store in db.
        self.record_positions()

        return self.positions

    def get_position(self, code: str) -> Position:
        if code in self.positions.keys():
            return self.positions[code]
        return None

    def cal_signals(self, time: any) -> list:
        """
        Calculate signals on specific time.
        Args:
            time[any]: any format of time
        Returns:
            List of Signal
        """
        # TODO
        return

    def cal_suggestions(self, time: any = None) -> list:
        """
        Calculate Suggestions on specific day.
        Calculate Signals on specific day.
        Args:
            time[any]: any format of time
        Returns:
            List of Suggestions(same as Order)
        """
        # TODO Try get from db, if nothing, try generate.
        now = datetime.datetime.now()
        time = datetime_normalize(time) if time else now
        self.on_time_goes_by(time)  # TODO seems no need update time in live mode
        if self._engine_put is None:
            return
        if self.selector is None:
            return
        # Del signals and suggestions(orders) at time in db
        # TODO
        # Get Interested list of code from selector at time
        codes = self.selector.pick(time)
        suggestions = []
        for code in codes:
            for i in self.strategies:
                signal = i.cal(code, time)
                if signal is None:
                    continue
                order = self.sizer.cal(signal)
                if order is None:
                    continue
                order_adjusted = self.risk_manager.cal(order)
                if order_adjusted is None:
                    continue

                if order_adjusted.volume == 0:
                    continue
                suggestions.append(order_adjusted)
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
                    time,
                    self.engine_id,
                )
                GDATA.add(mo)

    def on_time_goes_by(self, time: any, *args, **kwargs):
        """
        Go next time.
        Args:
            time[any]: time
        Returns:
            None
        """
        # Time goes
        super(PortfolioLive, self).on_time_goes_by(time, *args, **kwargs)

    def on_signal(self, event: EventSignalGeneration):
        """
        Dealing with the signal coming.
        1. Get a signal
        2. After sizer and risk manager
        3.1. Drop the signal
        3.2. Put order to event engine
        """
        # TODO
        return
        self.log("INFO", f"{self.name} got a {event.direction} signal about {event.code}  --> {event.direction}.")
        # Check Everything.
        if not self.is_all_set():
            return

        # 1. Transfer signal to sizer
        order = self.sizer.cal(event.value)
        # 2. Get the order return
        if order is None:
            return

        # 3. Transfer the order to risk_manager
        if self.risk_manager is not None:
            order_adjusted = self.risk_manager.cal(order)
        else:
            order_adjusted = order

        # 4. Get the adjusted order, if so put eventorder to engine
        if order_adjusted is None:
            return

        if order_adjusted.volume == 0:
            return

        # 5. Create order, stored into db, Here is also suggestions.
        import pdb

        pdb.set_trace()
        event = EventOrderSubmitted(order_adjusted)
        self.put(event)
        GNOTIFIER.beep()

    def on_price_update(self, event: EventPriceUpdate):
        """
        Dealing with new price info.
        """
        # TODO
        return
        # Check Everything.
        if not self.is_all_set():
            return

        # 1. Update position price
        if event.code in self.positions:
            self.positions[event.code].on_price_update(event.close)

        for strategy in self.strategies:
            # 3. Get signal return, if so put eventsignal to engine
            signal = strategy.value.cal(event.value)
            return
            if signal:
                e = EventSignalGeneration(signal)
                e.set_source(SOURCE_TYPES.PORTFOLIO)
                GDATA.add_signal(
                    self.uuid,
                    self.now,
                    e.code,
                    e.direction,
                    f"{strategy.value.name} gen.",
                )
                self.put(e)
        self.update_worth()
        self.update_profit()

    def on_order_filled(self, event: EventOrderFilled):
        # TODO
        return
        sele.log("INFO", "Got An Order Filled...")
        if not event.order_status == ORDERSTATUS_TYPES.FILLED:
            self.log(
                "CRITICAL",
                f"On Order Filled only handle the FILLEDORDER, cant handle a {event.order_status} one. Check the Code",
            )
            return
        self.log("INFO", "Got An Order Filled Done")

    def update_worth(self):
        pass

    def update_profit(self):
        pass

    # def __repr__(self) -> str:
    #     return base_repr(self, PortfolioLive.__name__, 24, 60)
