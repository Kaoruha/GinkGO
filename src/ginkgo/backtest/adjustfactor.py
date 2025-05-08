import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod
from decimal import Decimal

from ginkgo.backtest.base import Base
from ginkgo.libs import base_repr, pretty_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import FREQUENCY_TYPES


class Adjustfactor(Base):
    """
    Bar Container. Store OHLC, code, time and other info.
    """

    def __init__(
        self,
        code: str = "defaultcode",
        timestamp: any = "1990-01-01",
        fore_adjustfactor: Number = 0,
        back_adjustfactor: Number = 0,
        adjustfactor: Number = 0,
        *args,
        **kwargs
    ) -> None:
        super(Adjustfactor, self).__init__(*args, **kwargs)
        self.set(code, timestamp, fore_adjustfactor, back_adjustfactor, adjustfactor)

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
        timestamp: any,
        fore_adjustfactor: Number = 0,
        back_adjustfactor: Number = 0,
        adjustfactor: Number = 0,
        *args,
        **kwargs
    ) -> None:
        self._code = code
        self._timestamp = datetime_normalize(timestamp)
        self._fore_adjustfactor = to_decimal(fore_adjustfactor)
        self._back_adjustfactor = to_decimal(back_adjustfactor)
        self._adjustfactor = to_decimal(adjustfactor)

    @set.register
    def _(self, df: pd.Series):
        self._code = df.code
        self._timestamp = datetime_normalize(df["timestamp"])
        self._fore_adjustfactor = to_decimal(df["fore_adjustfactor"])
        self._back_adjustfactor = to_decimal(df["back_adjustfactor"])
        self._adjustfactor = to_decimal(df["adjustfactor"])

    @property
    def code(self) -> str:
        """
        The Code of the Bar.
        """
        return self._code

    @property
    def timestamp(self) -> datetime.datetime:
        """
        Time
        """
        return self._timestamp

    @property
    def fore_adjustfactor(self) -> Decimal:
        return self._fore_adjustfactor

    @property
    def back_adjustfactor(self) -> Decimal:
        return self._back_adjustfactor

    @property
    def adjustfactor(self) -> Decimal:
        return self._adjustfactor

    def __repr__(self) -> str:
        return base_repr(self, Adjustactor.__name__, 12, 60)
