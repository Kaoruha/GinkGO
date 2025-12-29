# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: Model Position Record模型继承定义MPositionRecord持仓记录相关数据结构






import datetime
import pandas as pd
from typing import Union, Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.models.model_backtest_record_base import MBacktestRecordBase
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.enums import SOURCE_TYPES


class MPositionRecord(MClickBase, MBacktestRecordBase):
    __abstract__ = False
    __tablename__ = "position_record"

    portfolio_id: Mapped[str] = mapped_column(String(), default="")
    code: Mapped[str] = mapped_column(String(), default="ginkgo_test_code")
    cost: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    volume: Mapped[int] = mapped_column(Integer, default=0)
    frozen_volume: Mapped[int] = mapped_column(Integer, default=0)
    frozen_money: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    price: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    fee: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    business_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True, comment="业务时间戳")

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        code: Optional[str] = None,
        cost: Optional[Number] = None,
        volume: Optional[int] = None,
        frozen_volume: Optional[int] = None,
        frozen_money: Optional[Number] = None,
        price: Optional[Number] = None,
        fee: Optional[Number] = None,
        source: Optional[SOURCE_TYPES] = None,
        timestamp: any = None,
        business_timestamp: Optional[any] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        if code is not None:
            self.code = str(code)
        if cost is not None:
            self.cost = to_decimal(cost)
        if volume is not None:
            self.volume = int(volume)
        if frozen_volume is not None:
            self.frozen_volume = int(frozen_volume)
        if frozen_money is not None:
            self.frozen_money = to_decimal(frozen_money)
        if price is not None:
            self.price = to_decimal(price)
        if fee is not None:
            self.fee = to_decimal(fee)
        if source is not None:
            self.source = source
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if business_timestamp is not None:
            self.business_timestamp = datetime_normalize(business_timestamp)
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.code = df["code"]
        self.cost = to_decimal(df["cost"])
        self.volume = df["volume"]
        self.frozen_volume = df["frozen_volume"]
        self.frozen_money = df["frozen_money"]
        self.price = df["price"]
        self.fee = df["fee"]

        if "business_timestamp" in df.keys() and pd.notna(df["business_timestamp"]):
            self.business_timestamp = datetime_normalize(df["business_timestamp"])
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
