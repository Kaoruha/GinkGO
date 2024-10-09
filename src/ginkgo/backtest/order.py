from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.data.models import MOrder

import pandas as pd
import datetime
import uuid
from functools import singledispatchmethod

from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.backtest.base import Base
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)


class Order(Base):
    """
    Order Class
    """

    def __init__(
        self,
        code: str = "Default Order Code",
        direction: DIRECTION_TYPES = None,
        type: ORDER_TYPES = None,
        status: ORDERSTATUS_TYPES = ORDERSTATUS_TYPES.NEW,
        volume: int = 0,
        limit_price: float = 0,
        frozen: float = 0,
        transaction_price: float = 0,
        remain: float = 0,
        fee: float = 0,
        timestamp: any = None,
        uuid: str = "",
        portfolio_id: str = "",
        *args,
        **kwargs
    ) -> None:
        super(Order, self).__init__(*args, **kwargs)
        self.set(
            code,
            direction,
            type,
            status,
            volume,
            limit_price,
            frozen,
            transaction_price,
            remain,
            fee,
            timestamp,
            uuid,
            portfolio_id,
        )

    @singledispatchmethod
    def set(self) -> None:
        """
        Support set from params or dataframe.
        1. From parmas
        2. From dataframe
        code,direction,type,volume,limit_price,frozen,transaction_price,remain,timestamp,uuid
        """
        pass

    @singledispatchmethod
    def _(self, model: "MOrder") -> None:
        self._code = model.code
        self._direction = model.direction
        self._type = model.type
        self._status = model.status
        self._volume = model.volume
        self._limit_price = model.limit_price
        self._frozen = model.frozen
        self._transaction_price = model.transaction_price
        self._remain = model.remain
        self._fee = model.fee
        self._timestamp = model.fee
        self.uuid = model.uuid
        self._portfolio_id = model.portfolio_id

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
        fee: float,
        timestamp: any,
        id: str,
        portfolio_id: str,
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
        self._fee: float = fee
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)

        if len(id) > 0:
            self._uuid: str = id
        else:
            self._uuid = uuid.uuid4().hex

        self._portfolio_id = portfolio_id

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
        self._fee: float = df.fee
        self._timestamp: datetime.datetime = df.timestamp
        self._uuid: str = df.uuid
        self._portfolio_id: str = df.portfolio_id
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value) -> None:
        self._code = value

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value) -> None:
        self._timestamp = value

    @property
    def uuid(self) -> str:
        return self._uuid

    @uuid.setter
    def uuid(self, value) -> None:
        self._uuid = uuid

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @direction.setter
    def direction(self, value) -> None:
        self._direction = value

    @property
    def type(self) -> ORDER_TYPES:
        return self._type

    @type.setter
    def type(self, value) -> None:
        self._type = value

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = value

    @property
    def status(self) -> ORDERSTATUS_TYPES:
        return self._status

    @property
    def limit_price(self) -> float:
        return self._limit_price

    @limit_price.setter
    def limit_price(self, value) -> None:
        self._limit_price = value

    @property
    def frozen(self) -> float:
        return self._frozen

    @frozen.setter
    def frozen(self, value) -> None:
        self._frozen = value

    @property
    def transaction_price(self) -> float:
        return self._transaction_price

    @transaction_price.setter
    def transaction_price(self, value) -> None:
        self._transaction_price = value

    @property
    def remain(self) -> float:
        return self._remain

    @remain.setter
    def remain(self, value) -> None:
        self._remain = value

    @property
    def fee(self) -> float:
        return self._fee

    @fee.setter
    def fee(self, value) -> None:
        self._fee = value

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> None:
        self._portfolio_id = value

    def submit(self) -> None:
        # TODO check the order status
        self._status = ORDERSTATUS_TYPES.SUBMITTED

    def fill(self) -> None:
        # TODO check the order status
        self._status = ORDERSTATUS_TYPES.FILLED

    def cancel(self) -> None:
        # TODO check the order status
        self._status = ORDERSTATUS_TYPES.CANCELED

    def __repr__(self) -> str:
        return base_repr(self, Order.__name__, 20, 60)
