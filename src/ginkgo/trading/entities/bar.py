import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod
from decimal import Decimal

from ginkgo.trading.core.base import Base
from ginkgo.libs import base_repr, pretty_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import FREQUENCY_TYPES, COMPONENT_TYPES


class Bar(Base):
    """
    Bar Container. Store OHLC, code, time and other info.
    """

    def __init__(
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
        uuid: str = "",
        *args,
        **kwargs
    ) -> None:
        super(Bar, self).__init__(uuid=uuid, component_type=COMPONENT_TYPES.BAR, *args, **kwargs)
        self.set(code, open, high, low, close, volume, amount, frequency, timestamp)

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
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
        self._volume = int(volume)
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
        self._volume = int(df["volume"])
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
    def amount(self) -> Decimal:
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

    @property
    def pct_chg(self) -> Decimal:
        """
        Calculate the percentage change ((close - open) / open * 100).

        Returns:
            Decimal: The percentage change.
        """
        if self._open == 0:
            return Decimal('0')
        r = (self._close - self._open) / self._open * 100
        r = round(r, 4)
        return Decimal(str(r))

    @property
    def middle_price(self) -> Decimal:
        """
        Calculate the middle price ((high + low) / 2).

        Returns:
            Decimal: The middle price.
        """
        r = (self._high + self._low) / 2
        r = round(r, 4)
        return Decimal(str(r))

    @property
    def typical_price(self) -> Decimal:
        """
        Calculate the typical price ((high + low + close) / 3).

        Returns:
            Decimal: The typical price.
        """
        r = (self._high + self._low + self._close) / 3
        r = round(r, 4)
        return Decimal(str(r))

    @property
    def weighted_price(self) -> Decimal:
        """
        Calculate the weighted price ((high + low + 2*close) / 4).

        Returns:
            Decimal: The weighted price.
        """
        r = (self._high + self._low + 2 * self._close) / 4
        r = round(r, 4)
        return Decimal(str(r))

    def to_model(self):
        """
        Convert Bar entity to MBar database model.

        Returns:
            MBar: Database model instance
        """
        from ginkgo.data.models.model_bar import MBar

        model = MBar()
        model.update(
            self._code,  # code作为第一个位置参数
            open=self._open,
            high=self._high,
            low=self._low,
            close=self._close,
            volume=self._volume,
            amount=self._amount,
            frequency=self._frequency,
            timestamp=self._timestamp
        )
        return model

    @classmethod
    def from_model(cls, model):
        """
        Create Bar entity from MBar database model.

        Args:
            model (MBar): Database model instance

        Returns:
            Bar: Bar entity instance

        Raises:
            TypeError: If model is not an MBar instance
        """
        from ginkgo.data.models.model_bar import MBar
        from ginkgo.enums import FREQUENCY_TYPES

        # Validate model type
        if not isinstance(model, MBar):
            raise TypeError(f"Expected MBar instance, got {type(model).__name__}")

        # Convert frequency from int back to enum
        frequency = FREQUENCY_TYPES.from_int(model.frequency) or FREQUENCY_TYPES.DAY

        return cls(
            code=model.code,
            open=model.open,
            high=model.high,
            low=model.low,
            close=model.close,
            volume=model.volume,
            amount=model.amount,
            frequency=frequency,
            timestamp=model.timestamp
        )

    def __repr__(self) -> str:
        return base_repr(self, Bar.__name__, 12, 60)
