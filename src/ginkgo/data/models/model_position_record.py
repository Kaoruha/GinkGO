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
    engine_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    volume: Mapped[int] = mapped_column(Integer, default=0)
    frozen_volume: Mapped[int] = mapped_column(Integer, default=0)
    frozen_money: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        timestamp: Optional[any] = None,
        code: Optional[str] = None,
        volume: Optional[int] = None,
        frozen_volume: Optional[int] = None,
        frozen_money: Optional[int] = None,
        cost: Optional[Number] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = str(portfolio_id)
        self.engine_id = str(engine_id)
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if code is not None:
            self.code = str(code)
        if volume is not None:
            self.volume = int(volume)
        if frozen_volume is not None:
            self.frozen_volume = int(frozen_volume)
        if frozen_money is not None:
            self.frozen_money = int(frozen_money)
        if cost is not None:
            self.cost = to_decimal(cost)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.code = df["code"]
        self.volume = df["volume"]
        self.frozen_volume = df["frozen_volume"]
        self.frozen_money = df["frozen_money"]
        self.cost = to_decimal(df["cost"])
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
