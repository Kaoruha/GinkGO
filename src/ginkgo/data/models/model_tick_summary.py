import pandas as pd
import datetime
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from .model_clickbase import MClickBase
from ...libs import datetime_normalize, base_repr, Number, to_decimal
from ...enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class MTickSummary(MClickBase):
    __abstract__ = False
    __tablename__ = "tick_summary"

    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        price: Optional[Number] = None,
        volume: Optional[int] = None,
        timestamp: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if price is not None:
            self.price = to_decimal(price)
        if volume is not None:
            self.volume = volume
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.price = to_decimal(df["price"])
        self.volume = df["volume"]
        self.timestamp = datetime_normalize(df["timestamp"])
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
