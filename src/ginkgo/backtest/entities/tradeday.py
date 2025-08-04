import datetime
import pandas as pd
from functools import singledispatchmethod

from ..core.base import Base
from ...enums import MARKET_TYPES
from ...libs import datetime_normalize


class TradeDay(Base):
    def __init__(
        self,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        is_open: bool = True,
        timestamp: any = "1990-01-01",
        *args,
        **kwargs,
    ):
        super(TradeDay, self).__init__(*args, **kwargs)
        self.set(market, is_open, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(self, market: MARKET_TYPES, is_open: bool, timestamp: any, *args, **kwargs) -> None:
        if not isinstance(market, MARKET_TYPES):
            raise ValueError("Market must be a valid MARKET_TYPES enum.")
        if not isinstance(is_open, bool):
            raise ValueError("is_open must be a boolean.")
        if not isinstance(timestamp, (str, datetime.datetime)):
            raise ValueError("Timestamp must be a string or datetime object.")
        self._market = market
        self._is_open = is_open
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        # 定义必需的字段
        required_fields = {"market", "is_open", "timestamp"}
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")
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

    def __repr__(self) -> str:
        return f"TradeDay(market={self._market}, is_open={self._is_open}, timestamp={self._timestamp})"
