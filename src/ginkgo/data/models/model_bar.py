import datetime
import pandas as pd

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Enum
from sqlalchemy import String, Integer, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES


class MBar(MClickBase):
    __abstract__ = False
    __tablename__ = "bar"

    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    open: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    high: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    low: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    close: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    frequency: Mapped[FREQUENCY_TYPES] = mapped_column(Enum(FREQUENCY_TYPES), default=FREQUENCY_TYPES.DAY)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        open: float = None,
        high: float = None,
        low: float = None,
        close: float = None,
        volume: int = None,
        frequency: FREQUENCY_TYPES = None,
        timestamp: any = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if open is not None:
            self.open = round(open, 3)
        if high is not None:
            self.high = round(high, 3)
        if low is not None:
            self.low = round(low, 3)
        if close is not None:
            self.close = round(close, 3)
        if volume is not None:
            self.volume = int(volume)
        if frequency is not None:
            self.frequency = frequency
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.open = df.open
        self.high = df.high
        self.low = df.low
        self.close = df.close
        self.volume = df.volume
        self.timestamp = df.timestamp
        self.frequency = df.frequency

        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
