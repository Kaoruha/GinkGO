import datetime
import pandas as pd

from decimal import Decimal
from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import Enum
from sqlalchemy import String, Integer, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import types, engines

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES


class MBar(MClickBase):
    __abstract__ = False
    __tablename__ = "bar"

    # ClickHouse优化配置：按代码+时间排序
    __table_args__ = (
        engines.MergeTree(
            order_by=("code", "timestamp")
        ),
        {"extend_existing": True},
    )

    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    open: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    high: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    low: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    close: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    frequency: Mapped[int] = mapped_column(types.Int8, default=-1)

    def __init__(self, **kwargs):
        # 处理枚举类型转换
        if 'frequency' in kwargs and kwargs['frequency'] is not None:
            kwargs['frequency'] = FREQUENCY_TYPES.validate_input(kwargs['frequency']) or -1
        if 'source' in kwargs and kwargs['source'] is not None:
            kwargs['source'] = SOURCE_TYPES.validate_input(kwargs['source']) or -1

        # 调用父类构造函数
        super().__init__(**kwargs)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        open: Optional[Number] = None,
        high: Optional[Number] = None,
        low: Optional[Number] = None,
        close: Optional[Number] = None,
        volume: Optional[int] = None,
        amount: Optional[Number] = None,
        frequency: Optional[FREQUENCY_TYPES] = None,
        timestamp: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if open is not None:
            self.open = to_decimal(open)
        if high is not None:
            self.high = to_decimal(high)
        if low is not None:
            self.low = to_decimal(low)
        if close is not None:
            self.close = to_decimal(close)
        if volume is not None:
            self.volume = int(volume)
        if amount is not None:
            self.amount = to_decimal(amount)
        if frequency is not None:
            self.frequency = FREQUENCY_TYPES.validate_input(frequency) or -1
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.open = to_decimal(df["open"])
        self.high = to_decimal(df["high"])
        self.low = to_decimal(df["low"])
        self.close = to_decimal(df["close"])
        self.volume = df["volume"]
        self.amount = to_decimal(df["amount"])
        self.timestamp = datetime_normalize(df["timestamp"])
        self.frequency = FREQUENCY_TYPES.validate_input(df["frequency"]) or -1

        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
