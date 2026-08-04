# Upstream: StockinfoService (同步股票基础信息)、Data Services (查询股票元数据)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、CURRENCY_TYPES/MARKET_TYPES (枚举类型验证)
# Role: MStockInfo股票信息MySQL模型继承MMysqlBase定义核心字段






import pandas as pd
import datetime

from typing import Optional
from functools import singledispatchmethod
from sqlalchemy import Column, String, DateTime, Integer, Enum
from sqlalchemy.dialects.mysql import TINYINT
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
    currency: Mapped[int] = mapped_column(TINYINT, default=-1, info={"enum": CURRENCY_TYPES})
    market: Mapped[int] = mapped_column(TINYINT, default=-1, info={"enum": MARKET_TYPES})
    list_date: Mapped[datetime.datetime] = mapped_column(DateTime)
    delist_date: Mapped[datetime.datetime] = mapped_column(DateTime)

    def __init__(self, code=None, code_name=None, industry=None, currency=None,
                 market=None, list_date=None, delist_date=None, source=None, **kwargs):
        """Initialize MStockInfo with automatic enum/int handling"""
        super().__init__(**kwargs)

        self.code = code or "ginkgo_test_code"
        self.code_name = code_name or "ginkgo_test_name"
        self.industry = industry or "ginkgo_test_industry"

        # Handle currency and market - accept both int and enum
        if currency is not None:
            validated = CURRENCY_TYPES.validate_input(currency)
            self.currency = validated if validated is not None else CURRENCY_TYPES.CNY.value
        else:
            self.currency = CURRENCY_TYPES.CNY.value

        if market is not None:
            validated = MARKET_TYPES.validate_input(market)
            self.market = validated if validated is not None else MARKET_TYPES.CHINA.value
        else:
            self.market = MARKET_TYPES.CHINA.value

        if list_date is not None:
            self.list_date = datetime_normalize(list_date)
        else:
            self.list_date = datetime.datetime.now()

        if delist_date is not None:
            self.delist_date = datetime_normalize(delist_date)
        else:
            self.delist_date = datetime.datetime(2099, 12, 31)

        # ADR-029 Task 3 fix round 1：原 `or TUSHARE.value` 同款 falsy 吞 0 bug
        # (OTHER=0 → 0 or 7 = 7 静默改写为 TUSHARE)，与 update() 一并修。
        if source is not None:
            validated = SOURCE_TYPES.validate_input(source)
            self.source = validated if validated is not None else SOURCE_TYPES.TUSHARE.value
        else:
            self.source = SOURCE_TYPES.TUSHARE.value

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
            validated = CURRENCY_TYPES.validate_input(currency)
            self.currency = validated if validated is not None else -1
        if market is not None:
            validated = MARKET_TYPES.validate_input(market)
            self.market = validated if validated is not None else -1
        if list_date is not None:
            self.list_date = datetime_normalize(list_date)
        if delist_date is not None:
            self.delist_date = datetime_normalize(delist_date)
        if source is not None:
            validated = SOURCE_TYPES.validate_input(source)
            self.source = validated if validated is not None else -1
        self.update_at = datetime.datetime.now()

    @update.register(pd.Series)
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self.code = df["code"]
        self.code_name = df["code_name"]
        self.industry = df["industry"]
        validated = CURRENCY_TYPES.validate_input(df["currency"])
        self.currency = validated if validated is not None else -1
        validated = MARKET_TYPES.validate_input(df["market"])
        self.market = validated if validated is not None else -1
        self.list_date = datetime_normalize(df["list_date"])
        self.delist_date = datetime_normalize(df["delist_date"])
        if "source" in df.keys():
            validated = SOURCE_TYPES.validate_input(df["source"])
            self.source = validated if validated is not None else -1
        self.update_at = datetime.datetime.now()

    def __repr__(self) -> None:
        return base_repr(self, "DB" + self.__tablename__.capitalize(), 12, 46)

