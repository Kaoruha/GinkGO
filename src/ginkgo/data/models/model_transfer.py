import pandas as pd
import datetime
from typing import Optional

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import Column, String, Integer, DateTime, Boolean, DECIMAL, Enum
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from ...libs import base_repr, datetime_normalize, Number, to_decimal
from .model_mysqlbase import MMysqlBase
from ...enums import SOURCE_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES


class MTransfer(MMysqlBase):
    __abstract__ = False
    __tablename__ = "transfer"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    engine_id: Mapped[str] = mapped_column(String(32), default="")
    direction: Mapped[int] = mapped_column(
        TINYINT, default=-1
    )
    market: Mapped[int] = mapped_column(TINYINT, default=-1)
    money: Mapped[Decimal] = mapped_column(DECIMAL(16, 2), default=0)
    status: Mapped[int] = mapped_column(TINYINT, default=-1)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.now)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        direction: Optional[TRANSFERDIRECTION_TYPES] = None,
        market: Optional[MARKET_TYPES] = None,
        money: Optional[Number] = None,
        status: Optional[TRANSFERSTATUS_TYPES] = None,
        timestamp: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.engine_id = engine_id
        if direction is not None:
            self.direction = TRANSFERDIRECTION_TYPES.validate_input(direction) or -1
        if market is not None:
            self.market = MARKET_TYPES.validate_input(market) or -1
        if money is not None:
            self.money = money if isinstance(money, Decimal) else Decimal(str(money))
        if status is not None:
            self.status = TRANSFERSTATUS_TYPES.validate_input(status) or -1
        if timestamp is not None:
            self.timestamp = timestamp
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df["portfolio_id"]
        self.engine_id = df["engine_id"]
        self.direction = TRANSFERDIRECTION_TYPES.validate_input(df["direction"]) or -1
        self.market = MARKET_TYPES.validate_input(df["market"]) or -1
        self.money = to_decimal(df["money"])
        self.status = TRANSFERSTATUS_TYPES.validate_input(df["status"]) or -1
        self.timestamp = datetime_normalize(df["timestamp"])
        if "source" in df.keys():
            self.source = SOURCE_TYPES.validate_input(df["source"]) or -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
