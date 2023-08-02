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
        status: ORDERSTATUS_TYPES = ORDERSTATUS_TYPES.SUBMITTED,
        volume: int = 0,
        limit_price: float = 0,
        frozen: float = 0,
        transaction_price: float = 0,
        remain: float = 0,
        timestamp: any = None,
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
            frozen,
            transaction_price,
            remain,
            timestamp,
            uuid,
        )
        self._status = ORDERSTATUS_TYPES.NEW

    @singledispatchmethod
    def set(self) -> None:
        """
        Support transfer the params or dataframe
        code,direction,type,volume,limit_price,frozen,transaction_price,remain,timestamp,uuid
        """
        pass

    @set.register
    def _(
        self,
        code: str,
        direction: DIRECTION_TYPES,
        type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        volume: int,
        limit_price: float,
        frozen: float,
        transaction_price: float,
        remain: float,
        timestamp: any,
        uuid: str = "",
    ):
        self._code: str = code
        self._direction: DIRECTION_TYPES = direction
        self._type: ORDER_TYPES = type
        self._status = status
        self._volume: int = volume
        self._limit_price: float = limit_price
        self._frozen: float = frozen
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
        self._direction: DIRECTION_TYPES = DIRECTION_TYPES(df.direction)
        self._type: ORDER_TYPES = ORDER_TYPES(df["type"])
        self._status: ORDERSTATUS_TYPES = ORDERSTATUS_TYPES(df["status"])
        self._volume: int = df.volume
        self._limit_price: float = df.limit_price
        self._status = ORDERSTATUS_TYPES(df.status)
        self._frozen: float = df.frozen
        self._transaction_price: float = df.transaction_price
        self._remain: float = df.remain
        self._timestamp: datetime.datetime = df.timestamp
        self._uuid: str = df.uuid
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
        return self._limit_price

    @property
    def frozen(self) -> float:
        return self._frozen

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
