from typing import TYPE_CHECKING, Dict, List


import datetime
import time
import pandas as pd

from decimal import Decimal


from ginkgo.libs import datetime_normalize
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import PRICEINFO_TYPES, DIRECTION_TYPES
from ginkgo.backtest.backtest_base import BacktestBase
from ginkgo.backtest.engines.base_engine import BaseEngine


class MatchMakingBase(BacktestBase):
    def __init__(self, *args, **kwargs):
        super(MatchMakingBase, self).__init__(*args, **kwargs)
        self.set_name("HaloMatchmaking")
        self._price_cache = pd.DataFrame()
        self._order_book: Dict[str, List] = {}
        self._commission_rate = Decimal("0.0003")
        self._commission_min = 5
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            GLOG.ERROR(f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

    @property
    def price_cache(self) -> pd.DataFrame:
        return self._price_cache

    @property
    def commision_rate(self) -> float:
        """
        Rate of commision.
        """
        return self._commission_rate

    @property
    def commision_min(self) -> float:
        """
        The minimal of commission.
        """
        return self._commission_min

    @property
    def order_book(self) -> list:
        """
        List of order, waiting for match.
        """
        return self._order_book

    def on_order_received(self, *args, **kwargs):
        # If sim, run try_match
        # If live, send the order to broker
        raise NotImplemented("Function on_stock_order() must be implemented in class.")

    def cal_fee(self, volume: int, is_long: bool, *args, **kwargs) -> Decimal:
        """
        Calculate fee.
        Args:
            volume(int): volume of trade
            is_long(bool): direction of trade, True -> Long, False -> Short
        Returns:
            Fee
        """
        if volume <= 0:
            GLOG.ERROR(f"Volume should be greater than 0, {volume} is illegal.")
            return 0
        # 印花税，仅卖出时收
        stamp_tax = volume * Decimal("0.001") if not is_long else 0
        # 过户费，买卖均收
        transfer_fees = Decimal("0.00001") * volume
        # 代收规费0.00687%，买卖均收
        collection_fees = Decimal("0.0000687") * volume
        # 佣金，买卖均收
        commission = self.commision_rate * volume
        commission = commission if commission > self.commision_min else self.commision_min

        res = stamp_tax + transfer_fees + collection_fees + commission
        res = round(res, 2)
        return res

    def on_time_goes_by(self, time: any, *args, **kwargs) -> None:
        """
        Time elapses.
        Args:
            time(any): new time
        Returns:
            None
        """
        super(MatchMakingBase, self).on_time_goes_by(time, *args, **kwargs)
        # Clear the price cached and order_book
        self._price_cache = pd.DataFrame()
        self._order_book = {}
