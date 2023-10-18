import pandas as pd
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy_utils import ChoiceType
from functools import singledispatchmethod
from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.enums import (
    SOURCE_TYPES,
    FREQUENCY_TYPES,
    CURRENCY_TYPES,
)
from ginkgo.libs.ginkgo_conf import GCONF
from ginkgo.libs import datetime_normalize, base_repr


class MStockInfo(MClickBase):
    __abstract__ = False
    __tablename__ = "stock_info"

    code = Column(String(), default="ginkgo_test_code")
    code_name = Column(String(), default="ginkgo_test_name")
    industry = Column(String(), default="ginkgo_test_industry")
    currency = Column(ChoiceType(CURRENCY_TYPES, impl=Integer()), default=1)
    list_date = Column(DateTime)
    delist_date = Column(DateTime)

    def __init__(self, *args, **kwargs) -> None:
        super(MStockInfo, self).__init__(*args, **kwargs)

    @singledispatchmethod
    def set(self) -> None:
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
