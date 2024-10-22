import datetime
import pandas as pd
from typing import Union, Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES


class MPositionRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "position_record"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    volume: Mapped[int] = mapped_column(Integer, default=0)
    frozen: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        timestamp: Optional[any] = None,
        code: Optional[str] = None,
        volume: Optional[int] = None,
        frozen: Optional[int] = None,
        cost: Optional[Number] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = str(portfolio_id)
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if code is not None:
            self.code = str(code)
        if volume is not None:
            self.volume = int(volume)
        if frozen is not None:
            self.frozen = int(frozen)
        if cost is not None:
            self.cost = to_decimal(cost)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.code = df["code"]
        self.volume = df["volume"]
        self.frozen = df["frozen"]
        self.cost = to_decimal(df["cost"])
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
