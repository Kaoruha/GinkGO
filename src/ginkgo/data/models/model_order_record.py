import datetime
import pandas as pd
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal


class MOrderRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "order_record"

    order_id: Mapped[str] = mapped_column(String(32), default="")
    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    engine_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    direction: Mapped[DIRECTION_TYPES] = mapped_column(Enum(DIRECTION_TYPES), default=DIRECTION_TYPES.LONG)
    order_type: Mapped[ORDER_TYPES] = mapped_column(Enum(ORDER_TYPES), default=ORDER_TYPES.OTHER)
    status: Mapped[ORDERSTATUS_TYPES] = mapped_column(Enum(ORDERSTATUS_TYPES), default=ORDERSTATUS_TYPES.OTHER)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    limit_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    frozen: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    transaction_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    transaction_volume: Mapped[int] = mapped_column(Integer, default=0)
    remain: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        order_id: str,
        portfolio_id: str,
        engine_id: str,
        code: Optional[str] = None,
        direction: Optional[DIRECTION_TYPES] = None,
        order_type: Optional[ORDER_TYPES] = None,
        status: Optional[ORDERSTATUS_TYPES] = None,
        volume: Optional[int] = None,
        limit_price: Optional[Number] = None,
        frozen: Optional[int] = None,
        transaction_price: Optional[Number] = None,
        transaction_volume: Optional[int] = None,
        remain: Optional[Number] = None,
        fee: Optional[Number] = None,
        timestamp: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.order_id = order_id
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        if code is not None:
            self.code = code
        if direction is not None:
            self.direction = direction
        if order_type is not None:
            self.order_type = order_type
        if status is not None:
            self.status = status
        if volume is not None:
            self.volume = volume
        if limit_price is not None:
            self.limit_price = to_decimal(limit_price)
        if frozen is not None:
            self.frozen = frozen
        if transaction_price is not None:
            self.transaction_price = to_decimal(transaction_price)
        if transaction_volume is not None:
            self.transaction_volume = transaction_volume
        if remain is not None:
            self.remain = to_decimal(remain)
        if fee is not None:
            self.fee = to_decimal(fee)
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.order_id = df["order_id"]
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.code = df["code"]
        self.direction = df["direction"]
        self.order_type = df["order_type"]
        self.status = df["status"]
        self.volume = df["volume"]
        self.limit_price = to_decimal(df["limit_price"])
        self.frozen = df["frozen"]
        self.transaction_price = to_decimal(df["transaction_price"])
        self.transaction_volume = df["transaction_volume"]
        self.remain = to_decimal(df["remain"])
        self.fee = to_decimal(df["fee"])
        self.timestamp = datetime_normalize(df["timestamp"])
        self.portfolio_id = df["portfolio_id"]
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
