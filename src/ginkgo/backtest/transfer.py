import datetime
import pandas as pd
from functools import singledispatchmethod

from ginkgo.backtest.base import Base
from ginkgo.libs import base_repr
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, DIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES
from ginkgo.libs import datetime_normalize


class Transfer(Base):
    """
    Holding Position Class.
    """

    def __init__(
        self,
        uuid: str = "",
        portfolio_id: str = "test_portfolio",
        direction: DIRECTION_TYPES = DIRECTION_TYPES.LONG,
        market: MARKET_TYPES = MARKET_TYPES.CHINA,
        money: float = 1000,
        status: TRANSFERSTATUS_TYPES = TRANSFERSTATUS_TYPES.NEW,
        timestamp: any = datetime.datetime.now(),
        *args,
        **kwargs
    ):
        super(Transfer, self).__init__(*args, **kwargs)
        self.set_uuid(uuid)
        self.set(portfolio_id, direction, market, money, status, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        portfolio_id: str,
        direction: DIRECTION_TYPES,
        market: MARKET_TYPES,
        money: float,
        status: TRANSFERSTATUS_TYPES,
        timestamp: any,
    ) -> None:
        self._portfolio_id = portfolio_id
        self._direction = direction
        self._market = market
        self._money = money
        self._status = status
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series) -> None:
        self._portfolio_id = df.portfolio_id
        self._direction = df.direction
        self._market = df.market
        self._money = df.money
        self._timestamp = datetime_normalize(df.timestamp)

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @property
    def market(self) -> MARKET_TYPES:
        return self._market

    @property
    def money(self) -> float:
        return self._money

    @property
    def status(self) -> TRANSFERSTATUS_TYPES:
        return self._status

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __repr__(self) -> str:
        return base_repr(self, Transfer.__name__, 20, 60)
