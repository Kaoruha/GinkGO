import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod
from decimal import Decimal

from ..core.base import Base
from ...libs import base_repr, pretty_repr, datetime_normalize, Number, to_decimal
from ...enums import FREQUENCY_TYPES


class Bar(Base):
    """
    Bar Container. Store OHLC, code, time and other info.
    """

    def __init__(
        self,
        code: str = "defaultcode",
        open: Number = 0,
        high: Number = 0,
        low: Number = 0,
        close: Number = 0,
        volume: int = 0,
        amount: Number = 0,
        frequency: FREQUENCY_TYPES = FREQUENCY_TYPES.DAY,
        timestamp: any = "1990-01-01",
        *args,
        **kwargs
    ) -> None:
        super(Bar, self).__init__(*args, **kwargs)
        self.set(code, open, high, low, close, volume, amount, frequency, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        """
        1. code, open, high, low, close, volume, frequency, timestamp
        2. dataframe
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        code: str,
        open: Number,
        high: Number,
        low: Number,
        close: Number,
        volume: int,
        amount: Number,
        frequency: FREQUENCY_TYPES,
        timestamp: any,
    ) -> None:
        """
        Bar data set from params.

        Args:
            code(str): Code
            open(Number): price at open
            high(Number): the highest price in this period
            low(Number): the lowest price in this period
            close(Number): price at close
            volume(int): sum of the volume in this period
            amount(Number): xx
            frequency(enum): Day or Min5
            timestamp(any): timestamp
        Returns:
            None
        """
        self._code = code
        self._open = to_decimal(open)
        self._high = to_decimal(high)
        self._low = to_decimal(low)
        self._close = to_decimal(close)
        self._frequency = frequency
        self._volume = volume
        self._amount = to_decimal(amount)
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
        self._code = df["code"]
        self._open = to_decimal(df["open"])
        self._high = to_decimal(df["high"])
        self._low = to_decimal(df["low"])
        self._close = to_decimal(df["close"])
        self._frequency = df["frequency"]
        self._volume = df["volume"]
        self._amount = to_decimal(df["amount"])
        self._timestamp = datetime_normalize(df["timestamp"])

    @property
    def code(self) -> str:
        """
        The Code of the Bar.
        """
        return self._code

    @property
    def open(self) -> Decimal:
        """
        Open price
        """
        return self._open

    @property
    def high(self) -> Decimal:
        """
        The highest price.
        """
        return self._high

    @property
    def low(self) -> Decimal:
        """
        The lowest price.
        """
        return self._low

    @property
    def close(self) -> Decimal:
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
    def amount(self) -> int:
        """
        Turnover
        """
        return self._amount

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
    def chg(self) -> Decimal:
        """
        Calculate the price change (close - open).

        Returns:
            Decimal: The price change.
        """
        r = self._close - self._open
        r = round(r, 4)
        return Decimal(str(r))

    @property
    def amplitude(self) -> Decimal:
        """
        Calculate the price amplitude (high - low).

        Returns:
            Decimal: The price amplitude.
        """
        r = self._high - self._low
        r = round(r, 4)
        return Decimal(str(r))

    def __repr__(self) -> str:
        return base_repr(self, Bar.__name__, 12, 60)
