import pandas as pd
from functools import singledispatchmethod
from clickhouse_sqlalchemy import engines
from sqlalchemy import Column, String, Integer, DECIMAL, Boolean
from sqlalchemy_utils import ChoiceType
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from ginkgo import GCONF
from ginkgo.libs import base_repr, datetime_normalize


class MCodeOnTrade(MClickBase):
    __abstract__ = False
    __tablename__ = "code_on_trade"

    if GCONF.DBDRIVER == "clickhouse":
        __table_args__ = (
            engines.MergeTree(order_by=("timestamp",)),
            {"comment": "Store Code each TradeDay"},
        )

    code = Column(String(), default="ginkgo_test_code")
    code_name = Column(String(), default="ginkgo_test_name")
    market = Column(ChoiceType(MARKET_TYPES, impl=Integer()), default=1)
    trade_status = Column(Boolean(), default=True)

    def __init__(self, *args, **kwargs) -> None:
        super(MCodeOnTrade, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        code_name: str,
        trade_status: bool,
        market: MARKET_TYPES,
        datetime,
    ) -> None:
        self.code = code
        self.code_name = code_name
        self.market = market
        self.trade_status = trade_status
        self.timestamp = datetime_normalize(datetime)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.code_name = df.code_name
        self.market = df.market
        self.trade_status = df.trade_status
        self.timestamp = datetime_normalize(df.timestamp)
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> str:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
