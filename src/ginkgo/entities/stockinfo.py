# Upstream: Data Services (StockinfoService同步股票信息)、Strategies (查询股票基础信息)
# Downstream: ValueObject (提供 to_dataframe/_convert_*)、MARKET_TYPES/CURRENCY_TYPES (枚举)
# Role: StockInfo股票基础信息值对象继承ValueObject定义代码/名称/行业/市场/上市日期等核心属性；uuid 自留






import pandas as pd
import datetime

from ginkgo.entities.value_object import ValueObject
from ginkgo.enums import CURRENCY_TYPES, MARKET_TYPES, SOURCE_TYPES
from functools import singledispatchmethod
from ginkgo.libs import datetime_normalize, base_repr


class StockInfo(ValueObject):
    def __init__(
        self,
        code: str = "",
        code_name: str = "",
        industry: str = "",
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        currency: CURRENCY_TYPES = CURRENCY_TYPES.CNY,
        list_date: any = "1990-01-01",
        delist_date: any = "2099-12-31",
        uuid: str = "",
        *args,
        **kwargs,
    ):
        # VO 无身份机器：uuid 自留，不传 component_type
        self._uuid = uuid
        super().__init__()

        # 严格参数验证 - 与Signal和Position保持一致，要求核心业务参数
        if not code:
            raise ValueError("code cannot be empty.")
        if not isinstance(code, str):
            raise TypeError(f"code must be str, got {type(code)}")

        if not code_name:
            raise ValueError("code_name cannot be empty.")
        if not isinstance(code_name, str):
            raise TypeError(f"code_name must be str, got {type(code_name)}")

        if industry and not isinstance(industry, str):
            raise TypeError(f"industry must be str, got {type(industry)}")
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")
        if not isinstance(currency, CURRENCY_TYPES):
            raise TypeError(f"currency must be CURRENCY_TYPES enum, got {type(currency)}")

        # 时间戳验证和标准化
        normalized_list_date = datetime_normalize(list_date)
        if normalized_list_date is None:
            raise ValueError(f"Invalid list_date format: {list_date}")

        normalized_delist_date = datetime_normalize(delist_date)
        if normalized_delist_date is None:
            raise ValueError(f"Invalid delist_date format: {delist_date}")

        # 设置属性
        self._code = code
        self._code_name = code_name
        self._industry = industry
        self._market = market
        self._currency = currency
        self._list_date = normalized_list_date
        self._delist_date = normalized_delist_date

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        code: str,
        code_name: str,
        industry: str,
        market: MARKET_TYPES,
        currency: CURRENCY_TYPES,
        list_date: any,
        delist_date: any,
        *args,
        **kwargs,
    ) -> None:
        # 严格参数验证
        if not isinstance(code, str):
            raise TypeError(f"code must be str, got {type(code)}")
        if not isinstance(code_name, str):
            raise TypeError(f"code_name must be str, got {type(code_name)}")
        if not isinstance(industry, str):
            raise TypeError(f"industry must be str, got {type(industry)}")
        if not isinstance(market, MARKET_TYPES):
            raise TypeError(f"market must be MARKET_TYPES enum, got {type(market)}")
        if not isinstance(currency, CURRENCY_TYPES):
            raise TypeError(f"currency must be CURRENCY_TYPES enum, got {type(currency)}")

        # 时间戳验证和标准化
        normalized_list_date = datetime_normalize(list_date)
        if normalized_list_date is None:
            raise ValueError(f"Invalid list_date format: {list_date}")

        normalized_delist_date = datetime_normalize(delist_date)
        if normalized_delist_date is None:
            raise ValueError(f"Invalid delist_date format: {delist_date}")

        self._code = code
        self._code_name = code_name
        self._industry = industry
        self._market = market
        self._currency = currency
        self._list_date = normalized_list_date
        self._delist_date = normalized_delist_date

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"code", "code_name", "industry", "market", "currency", "list_date", "delist_date"}
        # 检查 Series 是否包含所有必需字段
        if not required_fields.issubset(df.index):
            missing_fields = required_fields - set(df.index)
            raise ValueError(f"Missing required fields in Series: {missing_fields}")

        self._code = df["code"]
        self._code_name = df["code_name"]
        self._industry = df["industry"]
        self._market = df["market"]
        self._currency = df["currency"]
        self._list_date = datetime_normalize(df["list_date"])
        self._delist_date = datetime_normalize(df["delist_date"])

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs) -> None:
        required_fields = {"code", "code_name", "industry", "market", "currency", "list_date", "delist_date"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        # 假设DataFrame只有一行数据，取第一行
        row = df.iloc[0] if len(df) > 0 else df.iloc[0]

        self._code = row["code"]
        self._code_name = row["code_name"]
        self._industry = row["industry"]
        self._market = row["market"]
        self._currency = row["currency"]
        self._list_date = datetime_normalize(row["list_date"])
        self._delist_date = datetime_normalize(row["delist_date"])

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def symbol(self) -> str:
        """Alias for code. 金融行业标准术语。"""
        return self._code

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
    def market(self) -> MARKET_TYPES:
        return self._market

    @property
    def currency(self) -> CURRENCY_TYPES:
        return self._currency

    @property
    def list_date(self):
        return self._list_date

    @property
    def delist_date(self):
        return self._delist_date

    def __repr__(self) -> str:
        return base_repr(self, StockInfo.__name__, 20, 60)
