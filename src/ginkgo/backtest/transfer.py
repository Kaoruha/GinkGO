import datetime
import pandas as pd
from functools import singledispatchmethod
from decimal import Decimal

from ginkgo.backtest.base import Base
from ginkgo.libs import base_repr
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, DIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, TRANSFERDIRECTION_TYPES
from ginkgo.libs import datetime_normalize, Number


class Transfer(Base):
    """
    Holding Position Class.
    """

    def __init__(
        self,
        uuid: str = "",
        portfolio_id: str = "test_portfolio",
        engine_id: str = "",
        direction: TRANSFERDIRECTION_TYPES = TRANSFERDIRECTION_TYPES.IN,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        money: Number = 1000,
        status: TRANSFERSTATUS_TYPES = TRANSFERSTATUS_TYPES.NEW,
        timestamp: any = datetime.datetime.now(),
        *args,
        **kwargs,
    ):
        super(Transfer, self).__init__(*args, **kwargs)
        self.set_uuid(uuid)
        self.set(portfolio_id, engine_id, direction, market, money, status, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        direction: TRANSFERDIRECTION_TYPES,
        market: MARKET_TYPES,
        money: Number,
        status: TRANSFERSTATUS_TYPES,
        timestamp: any,
        *args,
        **kwargs,
    ) -> None:
        # 参数校验
        if not isinstance(portfolio_id, str):
            raise ValueError("portfolio_id must be a string.")
        if not isinstance(engine_id, str):
            raise ValueError("engine_id must be a string.")
        if not isinstance(direction, TRANSFERDIRECTION_TYPES):
            raise ValueError("direction must be a valid TRANSFERDIRECTION_TYPES enum.")
        if not isinstance(market, MARKET_TYPES):
            raise ValueError("market must be a valid MARKET_TYPES enum.")
        if not isinstance(money, Number) or money < 0:
            raise ValueError("money must be a non-negative number.")
        if not isinstance(status, TRANSFERSTATUS_TYPES):
            raise ValueError("status must be a valid TRANSFERSTATUS_TYPES enum.")
        if not isinstance(timestamp, (str, datetime.datetime)):
            raise ValueError("timestamp must be a string or datetime object.")

        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._direction = direction
        self._market = market
        self._money = money
        self._status = status
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        required_fields = {"portfolio_id", "direction", "market", "money", "timestamp"}
        # 检查 DataFrame 是否包含所有必需字段
        if not required_fields.issubset(df.columns):
            missing_fields = required_fields - set(df.columns)
            raise ValueError(f"Missing required fields in DataFrame: {missing_fields}")

        self._portfolio_id = df.portfolio_id
        self._engine_id = df["engine_id"]
        self._direction = df.direction
        self._market = df.market
        self._money = df.money
        if "status" in df.keys():
            self._status = TRANSFERSTATUS_TYPES(df["status"])
        self._timestamp = datetime_normalize(df.timestamp)

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def engine_id(self, *args, **kwargs) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def direction(self) -> TRANSFERDIRECTION_TYPES:
        return self._direction

    @property
    def market(self) -> MARKET_TYPES:
        return self._market

    @property
    def money(self) -> Decimal:
        return Decimal(str(self._money))

    @property
    def status(self) -> TRANSFERSTATUS_TYPES:
        return self._status

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __repr__(self) -> str:
        return base_repr(self, Transfer.__name__, 20, 60)
