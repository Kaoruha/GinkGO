import pandas as pd

from ginkgo.backtest.base import Base
from ginkgo.enums import CURRENCY_TYPES
from functools import singledispatchmethod
from ginkgo.libs import datetime_normalize


class StockInfo(Base):
    def __init__(self):
        pass

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
        list_date: any,
        edlist_date: any,
        *args,
        **kwargs
    ) -> None:
        self._code = code
        self._code_name = code_name
        self._industry = industry
        self._currency = currency
        self._list_date = datetime_normalize(list_date)
        self._delist_date = datetime_normalize(delist_date)

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs):
        self._code = df.code
        self._code_name = df.code_name
        self._industry = df.industry
        self._currency = CURRENCY_TYPES(df.currency)
        self._list_date = datetime_normalize(df.list_date)
        self._delist_date = datetime_normalize(df.delist_date)

    @property
    def code(self) -> str:
        return self._code

    @property
    def code_name(self) -> str:
        return self._code_name

    @property
    def industry(self) -> str:
        return self._industry

    @property
    def currency(self) -> CURRENCY_TYPES:
        return self._currency

    @property
    def list_date(self):
        return self._list_date

    @property
    def delist_date(self):
        return self._delist_date
