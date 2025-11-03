import datetime
import pandas as pd
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import String, Integer, DECIMAL, Enum, DateTime
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal


class MOrder(MMysqlBase, MBacktestRecordBase):
    __abstract__ = False
    __tablename__ = "order"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    direction: Mapped[int] = mapped_column(TINYINT, default=-1)
    order_type: Mapped[int] = mapped_column(TINYINT, default=-1)
    status: Mapped[int] = mapped_column(TINYINT, default=-1)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    limit_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    frozen: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    transaction_price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    transaction_volume: Mapped[int] = mapped_column(Integer, default=0)
    remain: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now)

    def __init__(self,
                 portfolio_id=None, engine_id=None, run_id=None,
                 uuid=None, code=None, direction=None, order_type=None, status=None,
                 volume=None, limit_price=None, frozen=None, transaction_price=None,
                 transaction_volume=None, remain=None, fee=None, timestamp=None,
                 source=None, **kwargs):
        """Initialize MOrder with automatic enum/int handling"""
        super().__init__(**kwargs)

        # 关联信息
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        # 基本属性
        if uuid is not None:
            self.uuid = uuid
        if code is not None:
            self.code = code

        # 枚举类型 - 自动转换
        if direction is not None:
            self.direction = DIRECTION_TYPES.validate_input(direction) or DIRECTION_TYPES.LONG.value
        if order_type is not None:
            self.order_type = ORDER_TYPES.validate_input(order_type) or ORDER_TYPES.LIMITORDER.value
        if status is not None:
            self.status = ORDERSTATUS_TYPES.validate_input(status) or ORDERSTATUS_TYPES.NEW.value

        # 数值属性
        if volume is not None:
            self.volume = volume
        if limit_price is not None:
            self.limit_price = to_decimal(limit_price)
        if frozen is not None:
            self.frozen = to_decimal(frozen)
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
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.TUSHARE.value

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        run_id: str = "",  # 新增run_id参数
        uuid: Optional[str] = None,
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
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        self.run_id = run_id  # 新增run_id字段赋值
        if uuid is not None:
            self.uuid = uuid
        if code is not None:
            self.code = code
        if direction is not None:
            self.direction = DIRECTION_TYPES.validate_input(direction) or -1
        if order_type is not None:
            self.order_type = ORDER_TYPES.validate_input(order_type) or -1
        if status is not None:
            self.status = ORDERSTATUS_TYPES.validate_input(status) or -1
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
            self.source = SOURCE_TYPES.validate_input(source) or -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.direction = DIRECTION_TYPES.validate_input(df["direction"]) or -1
        self.order_type = ORDER_TYPES.validate_input(df["order_type"]) or -1
        self.status = ORDERSTATUS_TYPES.validate_input(df["status"]) or -1
        self.volume = df["volume"]
        self.limit_price = to_decimal(df["limit_price"])
        self.frozen = df["frozen"]
        self.transaction_price = to_decimal(df["transaction_price"])
        self.transaction_volume = df["transaction_volume"]
        self.remain = to_decimal(df["remain"])
        self.fee = to_decimal(df["fee"])
        self.timestamp = datetime_normalize(df["timestamp"])
        self.uuid = df["uuid"]
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 20, 60)
