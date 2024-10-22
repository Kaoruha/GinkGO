import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import Column, String, DateTime, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES, CURRENCY_TYPES, MARKET_TYPES
from ginkgo.libs import datetime_normalize, base_repr


class MStockInfo(MMysqlBase):
    __abstract__ = False
    __tablename__ = "stock_info"

    code: Mapped[str] = mapped_column(String(32), default="ginkgo_test_code")
    code_name: Mapped[str] = mapped_column(String(32), default="ginkgo_test_name")
    industry: Mapped[str] = mapped_column(String(32), default="ginkgo_test_industry")
    currency: Mapped[CURRENCY_TYPES] = mapped_column(Enum(CURRENCY_TYPES), default=CURRENCY_TYPES.CNY)
    market: Mapped[MARKET_TYPES] = mapped_column(Enum(MARKET_TYPES), default=MARKET_TYPES.CHINA)
    list_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    delist_date: Mapped[datetime.datetime] = mapped_column(DateTime)

    @singledispatchmethod
    def update(self, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @update.register(str)
    def _(
        self,
        code: str,
        code_name: Optional[str] = None,
        industry: Optional[str] = None,
        currency: Optional[CURRENCY_TYPES] = None,
        market: Optional[MARKET_TYPES] = None,
        list_date: Optional[any] = None,
        delist_date: Optional[any] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        self.code = code
        if code_name is not None:
            self.code_name = code_name
        if industry is not None:
            self.industry = industry
        if currency is not None:
            self.currency = currency
        if market is not None:
            self.market = market
        if list_date is not None:
            self.list_date = datetime_normalize(list_date)
        if delist_date is not None:
            self.delist_date = datetime_normalize(delist_date)
        if source is not None:
            self.source = source
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.code_name = df["code_name"]
        self.industry = df["industry"]
        self.currency = df["currency"]
        self.market = df["market"]
        self.list_date = datetime_normalize(df["list_date"])
        self.delist_date = datetime_normalize(df["delist_date"])
        if "source" in df.keys():
            self.source = df["source"]
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)
