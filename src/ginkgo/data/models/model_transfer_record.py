import pandas as pd
from sqlalchemy import Column, String, Integer, DateTime, Boolean, DECIMAL
from sqlalchemy_utils import ChoiceType
from functools import singledispatchmethod


from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, DIRECTION_TYPES
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.libs.ginkgo_conf import GCONF


class MTransferRecord(MClickBase):
    __abstract__ = False
    __tablename__ = "transfer_record"

    portfolio_id = Column(String(), default="")
    direction = Column(ChoiceType(DIRECTION_TYPES, impl=Integer()), default=1)
    market = Column(ChoiceType(MARKET_TYPES, impl=Integer()), default=1)
    money = Column(DECIMAL(20, 10), default=0)

    def __init__(self, *args, **kwargs) -> None:
        super(MTransferRecord, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        portfolio_id: str,
        direction: DIRECTION_TYPES,
        market: MARKET_TYPES,
        money: float,
        timestamp: any,
        *args,
        **kwargs,
    ) -> None:
        self.portfolio_id = portfolio_id
        self.direction = direction
        self.market = market
        self.money = money
        self.timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.timestamp = datetime_normalize(df.date)
        self.market = df.market
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
