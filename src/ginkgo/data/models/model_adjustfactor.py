import datetime
import pandas as pd

from decimal import Decimal
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal


class MAdjustfactor(MMysqlBase):
    __abstract__ = False
    __tablename__ = "adjustfactor"

    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now)
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    foreadjustfactor: Mapped[Decimal] = mapped_column(DECIMAL(20, 10), default=0)
    backadjustfactor: Mapped[Decimal] = mapped_column(DECIMAL(20, 10), default=0)
    adjustfactor: Mapped[Decimal] = mapped_column(DECIMAL(20, 10), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        timestamp: Optional[any] = None,
        foreadjustfactor: Optional[Number] = None,
        backadjustfactor: Optional[Number] = None,
        adjustfactor: Optional[Number] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if foreadjustfactor is not None:
            self.foreadjustfactor = to_decimal(foreadjustfactor)
        if backadjustfactor is not None:
            self.backadjustfactor = to_decimal(backadjustfactor)
        if adjustfactor is not None:
            self.adjustfactor = to_decimal(adjustfactor)
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.foreadjustfactor = to_decimal(df["foreadjustfactor"])
        self.backadjustfactor = to_decimal(df["backadjustfactor"])
        self.adjustfactor = to_decimal(df["adjustfactor"])
        self.timestamp = df["timestamp"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
