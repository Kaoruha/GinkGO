import datetime
import pandas as pd
from ginkgo.libs import datetime_normalize
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import PRICEINFO_TYPES, DIRECTION_TYPES
from ginkgo.backtest.backtest_base import BacktestBase


class MatchMakingBase(BacktestBase):
    def __init__(self, *args, **kwargs):
        super(MatchMakingBase, self).__init__(*args, **kwargs)
        self.set_name("HaloMatchmaking")
        self._price = pd.DataFrame()
        self._order_book = []
        self._commission_rate = 0.0003
        self._commission_min = 5
        self._engine = None

    @property
    def engine(self):
        return self._engine

    def bind_engine(self, engine):
        self._engine = engine
        if engine.matchmaking is None:
            engine.bind_matchmaking(self)

    @property
    def commision_rate(self) -> float:
        return self._commission_rate

    @property
    def commision_min(self) -> float:
        return self._commission_min

    @property
    def order_book(self) -> list:
        return self._order_book

    @property
    def price(self) -> pd.DataFrame:
        return self._price

    def on_price_update(self, event: EventPriceUpdate, *args, **kwargs):
        # TODO Check the source
        time = None
        try:
            time = event.timestamp
        except Exception as e:
            pass

        # Update Current Time
        if time is None:
            GLOG.ERROR(f"Price Event has no time. It is illegal")
            return

        if time < self.now:
            GLOG.ERROR(
                f"Current Time is {self.now} the price come from past {event.timestamp}"
            )
            import pdb

            pdb.set_trace()
            return

        elif time > self.now:
            GLOG.ERROR(
                f"Current Time is {self.now} the price come from future {event.timestamp}"
            )
            return

        # One Frame just accept one line a code
        if self._price.shape[0] > 0:
            q = self._price[self._price.code == event.code]
            if q.shape[0] > 1:
                GLOG.ERROR(
                    f"Got 2 lines with {event.code} at this frame. Something Wrong."
                )
                return
            elif q.shape[0] == 1:
                GLOG.WARN(
                    f"{event.code} already in line at this frame. Drop this price event."
                )
                return

        # Deal with the tick
        ptype = event.price_type
        if ptype == PRICEINFO_TYPES.TICK:
            GLOG.WARN("MatchMaking not support tick info income now.")
            return
        # Deal with the bar
        elif ptype == PRICEINFO_TYPES.BAR:
            self._price = pd.concat([self._price, event.to_dataframe()], axis=0)
            self._price = self._price.reset_index(drop=True)

    def on_stock_order(self, *args, **kwargs):
        # If sim, run try_match
        # If live, send the order to broker
        raise NotImplemented

    def query_order(self, *args, **kwargs):
        # if sim, return the info in self.price
        # if live, ask the remote the order status
        raise NotImplemented

    def cal_fee(self, volume: float, is_long: bool, *args, **kwargs):
        if volume < 0:
            return 0
        # 印花税，仅卖出时收
        stamp_tax = volume * 0.001 if not is_long else 0
        # 过户费，买卖均收
        transfer_fees = 0.00001 * volume
        # 代收规费0.00687%，买卖均收
        collection_fees = 0.0000687 * volume
        # 佣金，买卖均收
        commission = self.commision_rate * volume
        commission = (
            commission if commission > self.commision_min else self.commision_min
        )

        return stamp_tax + transfer_fees + collection_fees + commission

    def on_time_goes_by(self, time: any, *args, **kwargs):
        super(MatchMakingBase, self).on_time_goes_by(time, *args, **kwargs)
        self._price = pd.DataFrame()
        self._order_book = []
