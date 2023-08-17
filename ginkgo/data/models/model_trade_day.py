import pandas as pd
from functools import singledispatchmethod
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType
from ginkgo import GCONF


class MTradeDay(MClickBase):
    __abstract__ = False
    __tablename__ = "trade_day"

    market = Column(ChoiceType(MARKET_TYPES, impl=Integer()), default=1)
    is_open = Column(Boolean(), default=True)

    def __init__(self, *args, **kwargs) -> None:
        super(MTradeDay, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        market: MARKET_TYPES,
        is_open: bool,
        date: str or datetime.datetime,
    ) -> None:
        self.market = market
        self.is_open = is_open
        self.timestamp = datetime_normalize(date)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.timestamp = datetime_normalize(df.date)
        self.market = df.market
        self.is_open = df.is_open
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
