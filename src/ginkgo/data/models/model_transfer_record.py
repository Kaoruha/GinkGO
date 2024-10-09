import pandas as pd
import datetime

from decimal import Decimal
from functools import singledispatchmethod
from sqlalchemy import DateTime, String, DECIMAL, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES


class MTransferRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "transfer_record"

    portfolio_id: Mapped[str] = mapped_column(String(32), default="")
    direction: Mapped[TRANSFERDIRECTION_TYPES] = mapped_column(
        Enum(TRANSFERDIRECTION_TYPES), default=TRANSFERDIRECTION_TYPES.IN
    )
    market: Mapped[MARKET_TYPES] = mapped_column(Enum(MARKET_TYPES), default=MARKET_TYPES.CHINA)
    money: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), default=0)
    status: Mapped[TRANSFERSTATUS_TYPES] = mapped_column(
        Enum(TRANSFERSTATUS_TYPES), default=TRANSFERSTATUS_TYPES.FILLED
    )  # FILLED or CANCELED

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        portfolio_id: str,
        timestamp: any = None,
        direction: TRANSFERDIRECTION_TYPES = None,
        market: MARKET_TYPES = None,
        money: float = None,
        status: TRANSFERSTATUS_TYPES = None,
        source: SOURCE_TYPES = None,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        if timestamp is not None:
            self.timestamp = datetime_normalize(timestamp)
        if direction is not None:
            self.direction = direction
        if market is not None:
            self.market = market
        if money is not None:
            self.money = money
        if status is not None:
            self.status = status
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.portfolio_id = df.portfolio_id
        self.timestamp = df.timestamp
        self.direction = df.direction
        self.market = df.market
        self.money = df.money
        self.status = df.status
        if "source" in df.keys():
            self.source = df.source
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
