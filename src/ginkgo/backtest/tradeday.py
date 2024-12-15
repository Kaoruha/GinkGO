import datetime
import pandas as pd
from functools import singledispatchmethod

from ginkgo.backtest.base import Base
from ginkgo.enums import MARKET_TYPES
from ginkgo.libs import datetime_normalize


class TradeDay(Base):
    def __init__(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        is_open: bool = True,
        timestamp: any = "1990-01-01",
        *args,
        **kwargs
    ):
        super(TradeDay, self).__init__(*args, **kwargs)
        self._market = market
        self._is_open = is_open
        self._timestamp = datetime_normalize(timestamp)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(self, market: MARKET_TYPES, is_open: bool, timestamp: any) -> None:
        self._market = market
        self._is_open = is_open
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.DataFrame) -> None:
        self._market = df["market"]
        self._is_open = df["is_open"]
        self._timestamp = datetime_normalize(df["timestamp"])

    @property
    def market(self) -> MARKET_TYPES:
        return self._market

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp
