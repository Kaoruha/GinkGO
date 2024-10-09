import datetime
import pandas as pd

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import String, Integer, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize


class MOrderRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "order_record"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    order_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    direction: Mapped[DIRECTION_TYPES] = mapped_column(Enum(DIRECTION_TYPES), default=DIRECTION_TYPES.LONG)
    type: Mapped[ORDER_TYPES] = mapped_column(Enum(ORDER_TYPES), default=ORDER_TYPES.OTHER)
    status: Mapped[ORDERSTATUS_TYPES] = mapped_column(Enum(ORDERSTATUS_TYPES), default=ORDERSTATUS_TYPES.OTHER)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    limit_price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    frozen: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    transaction_price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    remain: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        order_id: str,
        portfolio_id: str = None,
        code: str = None,
        direction: DIRECTION_TYPES = None,
        type: ORDER_TYPES = None,
        status: ORDERSTATUS_TYPES = None,
        volume: int = None,
        limit_price: float = None,
        frozen: float = None,
        transaction_price: float = None,
        remain: float = None,
        fee: float = None,
        timestamp: any = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.order_id = order_id
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if code is not None:
            self.code = code
        if direction is not None:
            self.direction = direction
        if type is not None:
            self.type = type
        if status is not None:
            self.status = status
        if volume is not None:
            self.volume = volume
        if limit_price is not None:
            self.limit_price = round(limit_price, 3)
        if frozen is not None:
            self.frozen = frozen
        if transaction_price is not None:
            self.transaction_price = round(transaction_price, 3)
        if remain is not None:
            self.remain = remain
        if fee is not None:
            self.fee = fee
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if source is not None:
            self.source = source

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.order_id = df.order_id
        self.portfolio_id = df.portfolio_id
        self.code = df.code
        self.direction = df.direction
        self.type = df.type
        self.status = df.status
        self.volume = df.volume
        self.limit_price = round(df.limit_price, 3)
        self.frozen = df.frozen
        self.transaction_price = round(df.transaction_price, 3)
        self.remain = df.remain
        self.fee = df.fee
        self.timestamp = df.timestamp
        self.portfolio_id = df.portfolio_id
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
