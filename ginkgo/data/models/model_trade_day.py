import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL, Boolean
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_base import MBase
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class MTradeday(MBase):
    __abstract__ = False
    __tablename__ = "Trade_day"

    if GCONF.DBDRIVER == "clickhouse":
        __table_args__ = (
            engines.MergeTree(order_by=("timestamp",)),
            {"comment": "Trade Calendar"},
        )

    market = Column(ChoiceType(MARKET_TYPES, impl=Integer()), default=1)
    is_open = Column(Boolean(), default=True)

    def __init__(self, *args, **kwargs) -> None:
        super(MCodeOnTrade, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        date: str or datetime.datetime,
        is_open: bool,
        market: MARKET_TYPES,
        source: SOURCE_TYPES,
        datetime,
    ) -> None:
        self.timestamp = datetime_normalize(datetime)
        self.is_open = is_open
        self.market = market
        self.set_source(source)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.market = df.market
        self.timestamp = datetime_normalize(df.timestamp)
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
