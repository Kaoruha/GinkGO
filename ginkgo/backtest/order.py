import pandas as pd
import datetime
from functools import singledispatchmethod
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.libs import gen_uuid4
from ginkgo.backtest.base import Base


class Order(Base):
    def __init__(self, *args, **kwargs) -> None:
        super(Order, self).__init__(*args, **kwargs)
        self._status = ORDERSTATUS_TYPES.NEW

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        type: ORDER_TYPES,
        volume: int,
        limit_price: float,
        timestamp: str or datetime.datetime,
        uuid: str = "",
    ):
        self._code: str = code
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)
        self._direction: DIRECTION_TYPES = direction
        self._type: ORDER_TYPES = type
        self._volume: int = volume
        self._limit_price: float = limit_price

        if len(uuid) > 0:
            self._uuid: str = uuid
        else:
            self._uuid = gen_uuid4()

    @set.register
    def _(self, df: pd.Series):
        """
        Set from dataframe
        """
        self._code: str = df.code
        self._timestamp: datetime.datetime = df.timestamp
        self._uuid: str = df.uuid
        self._direction: DIRECTION_TYPES = DIRECTION_TYPES(df.direction)
        self._type: ORDER_TYPES = ORDER_TYPES(df["type"])
        self._volume: int = df.volume
        self._limit_price: float = df.limit_price
        self._status = ORDERSTATUS_TYPES(df.status)

    @property
    def code(self) -> str:
        return self._code

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def uuid(self) -> str:
        return self._uuid

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @property
    def type(self) -> ORDER_TYPES:
        return self._type

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def status(self) -> ORDERSTATUS_TYPES:
        return self._status

    @property
    def limit_price(self) -> float:
        if self.type == ORDER_TYPES.MARKETORDER:
            return None
        elif self.type == ORDER_TYPES.LIMITORDER:
            return self._limit_price

    def __repr__(self) -> str:
        return base_repr(self, Order.__name__, 12, 60)

    def submit(self) -> None:
        self._status = ORDERSTATUS_TYPES.SUBMITTED

    def fill(self) -> None:
        self._status = ORDERSTATUS_TYPES.FILLED

    def cancel(self) -> None:
        self._status = ORDERSTATUS_TYPES.CANCELED
