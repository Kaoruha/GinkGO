import pandas as pd
import datetime
from functools import singledispatchmethod
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import base_repr, datetime_normalize, gen_uuid4
from ginkgo.backtest.base import Base


class Order(Base):
    def __init__(
        self,
        code: str = "Default Order Code",
        direction: DIRECTION_TYPES = None,
        type: ORDER_TYPES = None,
        volume: int = 0,
        limit_price: float = 0,
        freeze: float = 0,
        transaction_price: float = 0,
        remain: float = 0,
        timestamp: any = None,
        status: ORDERSTATUS_TYPES = ORDERSTATUS_TYPES.SUBMITTED,
        uuid: str = "",
        *args,
        **kwargs
    ) -> None:
        super(Order, self).__init__(*args, **kwargs)
        self.set(
            code,
            direction,
            type,
            volume,
            limit_price,
            freeze,
            transaction_price,
            remain,
            timestamp,
            uuid,
        )
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
        freeze: float,
        transaction_price: float,
        remain: float,
        timestamp: any,
        uuid: str = "",
    ):
        self._code: str = code
        self._direction: DIRECTION_TYPES = direction
        self._type: ORDER_TYPES = type
        self._volume: int = volume
        self._limit_price: float = limit_price
        self._freeze: float = freeze
        self._transaction_price: float = transaction_price
        self._remain: float = remain
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)

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
        self._freeze: float = df.freeze
        self._transaction_price: float = df.transaction_price
        self._remain: float = df.remain
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

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

    @property
    def freeze(self) -> float:
        return self._freeze

    @property
    def transaction_price(self) -> float:
        return self._transaction_price

    @property
    def remain(self) -> float:
        return self._remain

    def __repr__(self) -> str:
        return base_repr(self, Order.__name__, 12, 60)

    def submit(self) -> None:
        self._status = ORDERSTATUS_TYPES.SUBMITTED

    def fill(self) -> None:
        self._status = ORDERSTATUS_TYPES.FILLED

    def cancel(self) -> None:
        self._status = ORDERSTATUS_TYPES.CANCELED
