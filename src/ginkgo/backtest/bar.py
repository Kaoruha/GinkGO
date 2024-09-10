import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod

from ginkgo.backtest.base import Base
from ginkgo.libs import base_repr, pretty_repr, datetime_normalize
from ginkgo.enums import FREQUENCY_TYPES


class Bar(Base):
    """
    Bar Container. Store OHLC, code, time and other info.
    """

    def __init__(
        self,
        code: str = "defaultcode",
        open: float = 0,
        high: float = 0,
        low: float = 0,
        close: float = 0,
        volume: int = 0,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        timestamp: any = "1990-01-01",
        *args,
        **kwargs
    ) -> None:
        super(Bar, self).__init__(*args, **kwargs)
        self.set(code, open, high, low, cloase, frequency, volume, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        """
        1. code, open, high, low, close, volume, frequency, timestamp
        2. dataframe
        """
        pass

    @set.register
    def _(
        self,
        code: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        timestamp: any,
    ) -> None:
        """
        Bar data set from params.

        Args:
            code(str): Code
            open(float): price at open
            high(float): the highest price in this period
            low(float): the lowest price in this period
            close(float): price at close
            volume(int): sum of the volume in this period
            frequency(enum): Day or Min5
            timestamp(any): timestamp
        Returns:
            None
        """
        self._code = code
        self._open = open
        self._high = high
        self._low = low
        self._close = close
        self._frequency = frequency
        self._volume = volume
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series):
        """
        Bar set from DataFrame.

        Args:
            df(DataFrame): pandas dataframe, contains code, open, high, low, close, frequency, volume, timestamp
        Returns:
            None
        """
        self._code = df.code
        self._open = df.open
        self._high = df.high
        self._low = df.low
        self._close = df.close
        self._frequency = df.frequency
        self._volume = df.volume
        self._timestamp = datetime_normalize(df.timestamp)

    @property
    def code(self) -> str:
        """
        The Code of the Bar.
        """
        return self._code

    @property
    def open(self) -> float:
        """
        Open price
        """
        return self._open

    @property
    def high(self) -> float:
        """
        The highest price.
        """
        return self._high

    @property
    def low(self) -> float:
        """
        The lowest price.
        """
        return self._low

    @property
    def close(self) -> float:
        """
        Close price.
        """
        return self._close

    @property
    def volume(self) -> int:
        """
        Turnover
        """
        return self._volume

    @property
    def frequency(self) -> FREQUENCY_TYPES:
        """
        Tag for Frequency.
        Day, 5Min, 1Min
        """
        return self._frequency

    @property
    def timestamp(self) -> datetime.datetime:
        """
        Time
        """
        return self._timestamp

    @property
    def chg(self) -> float:
        """
        Change percent.
        """
        r = self._close - self._open
        r = round(r, 2)
        return r

    @property
    def amplitude(self) -> float:
        """
        The bigest wave.
        """
        r = self._high - self._low
        r = round(r, 2)
        return r

    def __repr__(self) -> str:
        return base_repr(self, Bar.__name__, 12, 60)
