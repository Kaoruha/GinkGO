import datetime
import pandas as pd

from decimal import Decimal
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import String, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import engines

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal


class MAdjustfactor(MClickBase, ModelConversion):
    __abstract__ = False
    __tablename__ = "adjustfactor"
    
    # ClickHouse优化配置：按代码+时间排序
    __table_args__ = (
        engines.MergeTree(
            order_by=("code", "timestamp")
        ),
        {"extend_existing": True},
    )

    code: Mapped[str] = mapped_column(String(), nullable=False, comment="股票代码")
    foreadjustfactor: Mapped[Decimal] = mapped_column(DECIMAL(16, 6), nullable=False, comment="前复权因子")
    backadjustfactor: Mapped[Decimal] = mapped_column(DECIMAL(16, 6), nullable=False, comment="后复权因子")
    adjustfactor: Mapped[Decimal] = mapped_column(DECIMAL(16, 6), nullable=False, comment="复权因子")

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

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df.code
        self.foreadjustfactor = to_decimal(df["foreadjustfactor"])
        self.backadjustfactor = to_decimal(df["backadjustfactor"])
        self.adjustfactor = to_decimal(df["adjustfactor"])
        self.timestamp = df["timestamp"]
        if "source" in df.keys():
            self.source = df["source"]

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 46)
