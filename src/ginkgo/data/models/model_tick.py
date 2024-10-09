import pandas as pd
import datetime

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import datetime_normalize, base_repr
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class MTick(MClickBase):
    __abstract__ = True
    __tablename__ = "tick"

    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    price: Mapped[str] = mapped_column(DECIMAL(10, 2), default=0)
    volume: Mapped[str] = mapped_column(Integer, default=0)
    direction: Mapped[str] = mapped_column(Enum(TICKDIRECTION_TYPES), default=TICKDIRECTION_TYPES.OTHER)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        price: float = None,
        volume: int = None,
        direction: TICKDIRECTION_TYPES = None,
        timestamp: any = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if price is not None:
            self.price = round(price, 3)
        if volume is not None:
            self.volume = volume
        if direction is not None:
            self.direction = direction
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.price = df.price
        self.volume = df.volume
        self.direction = df.direction
        self.timestamp = datetime_normalize(df.timestamp)
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
