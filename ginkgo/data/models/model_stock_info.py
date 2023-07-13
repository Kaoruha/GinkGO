import pandas as pd
from functools import singledispatchmethod
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.data.models.model_base import MBase
from ginkgo.enums import (
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
)
from sqlalchemy import Column, String, Integer, DateTime
from ginkgo.libs.ginkgo_conf import GCONF
from clickhouse_sqlalchemy import engines
from sqlalchemy_utils import ChoiceType
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class MStockInfo(MBase):
    __abstract__ = False
    __tablename__ = "stock_info"

    if GCONF.DBDRIVER == "clickhouse":
        __table_args__ = (engines.MergeTree(order_by=("timestamp",)),)

    code = Column(String(), default="ginkgo_test_code")
    code_name = Column(String(), default="ginkgo_test_name")
    industry = Column(String(), default="ginkgo_test_industry")
    currency = Column(ChoiceType(CURRENCY_TYPES, impl=Integer()), default=1)
    list_date = Column(DateTime)
    delist_date = Column(DateTime)

    def __init__(self, *args, **kwargs) -> None:
        super(MStockInfo, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        code_name: str,
        industry: str,
        currency: CURRENCY_TYPES,
        list_date: str or datetime.datetime,
        delist_date: str or datetime.datetime,
    ) -> None:
        self.code = code
        self.code_name = code_name
        self.industry = industry
        self.currency = currency
        self.list_date = datetime_normalize(list_date)
        self.delist_date = datetime_normalize(delist_date)

    @set.register
    def _(self, df: pd.Series) -> None:
        self.code = df.code
        self.code_name = df.code_name
        self.industry = df.industry
        self.currency = df.currency
        self.list_date = datetime_normalize(df.list_date)
        self.delist_date = datetime_normalize(df.delist_date)
        self.timestamp = datetime_normalize(df.timestamp)
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
