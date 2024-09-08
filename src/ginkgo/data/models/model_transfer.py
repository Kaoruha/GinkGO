import pandas as pd
from sqlalchemy import Column, String, Integer, DateTime, Boolean, DECIMAL
from sqlalchemy_utils import ChoiceType
from functools import singledispatchmethod
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, DIRECTION_TYPES, TRANSFERSTATUS_TYPES
from ginkgo.libs.ginkgo_conf import GCONF


class MTransfer(MMysqlBase):
    __abstract__ = False
    __tablename__ = "transfer"

    portfolio_id = Column(String(40), default="")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    market = Column(ChoiceType(MARKET_TYPES, impl=Integer()), default=1)
    money = Column(DECIMAL(20, 10), default=0)
    status = Column(ChoiceType(TRANSFERSTATUS_TYPES, impl=Integer()), default=1)

    def __init__(self, *args, **kwargs) -> None:
        super(MTransfer, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
        pass

    @set.register
    def _(
        self,
        portfolio_id: str,
        direction: DIRECTION_TYPES,
        market: MARKET_TYPES,
        money: float,
        status: TRANSFERSTATUS_TYPES,
        timestamp: any,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.direction = direction
        self.market = market
        self.money = money
        self.status = status
        self.timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.timestamp = datetime_normalize(df.date)
        self.market = df.market
        self.status = TRANSFERSTATUS_TYPES(df["status"])
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
