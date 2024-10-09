import pandas as pd
import datetime

from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.backtest.order import Order
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MSignal(MClickBase):
    __abstract__ = False
    __tablename__ = "signal"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    direction: Mapped[str] = mapped_column(Enum(DIRECTION_TYPES), default=DIRECTION_TYPES.LONG)
    reason: Mapped[str] = mapped_column(String(255), default="")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        timestamp: any = None,
        code: str = None,
        direction: DIRECTION_TYPES = None,
        reason: str = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if code is not None:
            self.code = code
        if direction is not None:
            self.direction = direction
        if reason is not None:
            self.reason = reason
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.timestamp = datetime_normalize(df["timestamp"])
        self.code = df["code"]
        self.direction = df["direction"]
        self.reason = df["reason"]

        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
