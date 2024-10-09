import datetime
import pandas as pd

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.enums import SOURCE_TYPES


class MPositionRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "position_record"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    volume: Mapped[str] = mapped_column(Integer, default=0)
    cost: Mapped[str] = mapped_column(DECIMAL(10, 2), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        timestamp: any = None,
        code: str = None,
        volume: int = None,
        cost: float = None,
        source: SOURCE_TYPES = None,
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
        if cost is not None:
            self.cost = float(cost)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.code = df["code"]
        self.volume = df["volume"]
        self.cost = df["cost"]
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
