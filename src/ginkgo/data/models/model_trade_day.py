import pandas as pd
import datetime

from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column
from functools import singledispatchmethod

from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES


class MTradeDay(MMysqlBase, ModelConversion):
    __abstract__ = False
    __tablename__ = "trade_day"

    market: Mapped[int] = mapped_column(TINYINT, default=-1)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now)

    def __init__(self, market=None, is_open=True, timestamp=None, source=None, **kwargs):
        """Initialize MTradeDay with automatic enum/int handling"""
        super().__init__(**kwargs)

        # Handle market field - accept both int and enum, validate_input handles both
        if market is not None:
            self.market = MARKET_TYPES.validate_input(market) or MARKET_TYPES.CHINA.value
        else:
            self.market = MARKET_TYPES.CHINA.value

        self.is_open = is_open

        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        else:
            self.timestamp = datetime.datetime.now()

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.TUSHARE.value
        else:
            self.source = SOURCE_TYPES.TUSHARE.value

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(MARKET_TYPES)
    def _(
        self,
        market: MARKET_TYPES,
        timestamp: Optional[any] = None,
        is_open: Optional[bool] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.market = MARKET_TYPES.validate_input(market) or -1
        if is_open is not None:
            self.is_open = is_open
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.market = MARKET_TYPES.validate_input(df["market"]) or -1
        self.is_open = df["is_open"]
        self.timestamp = datetime_normalize(df["timestamp"])
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
