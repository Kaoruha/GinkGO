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
        raise NotImplementedError("Unsupported input type for `set` method.")

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
        **kwargs,
    ) -> None:
        if not isinstance(code, str):
            raise ValueError("Code must be a string.")
        if not isinstance(code_name, str):
            raise ValueError("Code name must be a string.")
        if not isinstance(industry, str):
            raise ValueError("Industry must be a string.")
        if not isinstance(currency, CURRENCY_TYPES):
            raise ValueError("Currency must be a valid CURRENCY_TYPES enum.")
        if not isinstance(list_date, (str, datetime.datetime)):
            raise ValueError("List date must be a string or datetime object.")
        if not isinstance(delist_date, (str, datetime.datetime)):
            raise ValueError("Delist date must be a string or datetime object.")

        self._code = code
        self._code_name = code_name
        self._industry = industry
        self._currency = currency
        self._list_date = datetime_normalize(list_date)
        self._delist_date = datetime_normalize(delist_date)

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs):
        # TODO Dataframe>? or Serie
        """
        Set stock data from a pandas DataFrame.

        Args:
            df (pd.DataFrame): DataFrame containing stock data.

        Raises:
            ValueError: If required fields are missing in the DataFrame.
        """
        required_fields = {"code", "code_name", "industry", "currency", "list_date", "delist_date"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")
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
