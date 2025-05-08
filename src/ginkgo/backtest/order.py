import pandas as pd
import datetime
import uuid
from typing import Optional
from decimal import Decimal
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
        order_type: ORDER_TYPES = None,
        status: ORDERSTATUS_TYPES = ORDERSTATUS_TYPES.NEW,
        volume: int = 0,
        limit_price: float = 0,
        frozen: float = 0,
        transaction_price: float = 0,
        transaction_volume: int = 0,
        remain: float = 0,
        fee: float = 0,
        timestamp: any = None,
        order_id: str = "",
        portfolio_id: str = "",
        engine_id: str = "",
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the Order instance.

        Args:
            code (str, optional): Code of the order. Defaults to "Default Order Code".
            direction (DIRECTION_TYPES, optional): Direction of the order. Defaults to None.
            order_type (ORDER_TYPES, optional): Type of the order. Defaults to None.
            status (ORDERSTATUS_TYPES, optional): Status of the order. Defaults to ORDERSTATUS_TYPES.NEW.
            volume (int, optional): Volume of the order. Defaults to 0.
            limit_price (float, optional): Limit price of the order. Defaults to 0.
            frozen (float, optional): Frozen amount of the order. Defaults to 0.
            transaction_price (float, optional): Transaction price of the order. Defaults to 0.
            transaction_volume (int, optional): Transaction volume of the order. Defaults to 0.
            remain (float, optional): Remaining amount of the order. Defaults to 0.
            fee (float, optional): Fee of the order. Defaults to 0.
            timestamp (any, optional): Timestamp of the order. Defaults to None.
            order_id (str, optional): UUID of the order. Defaults to "".
            portfolio_id (str, optional): Portfolio ID of the order. Defaults to "".
        """
        self.set(
            code,
            direction=direction,
            order_type=order_type,
            status=status,
            volume=volume,
            limit_price=limit_price,
            frozen=frozen,
            transaction_price=transaction_price,
            transaction_volume=transaction_volume,
            remain=remain,
            fee=fee,
            timestamp=timestamp,
            order_id=order_id,
            portfolio_id=portfolio_id,
            engine_id=engine_id,
        )
        self.set_source(SOURCE_TYPES.OTHER)

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        """
        Support set from params or dataframe.
            1. From parmas
            2. From dataframe
            code,direction,type,volume,limit_price,frozen,transaction_price,remain,timestamp,uuid
        """
        raise NotImplementedError("Unsupported input type for `set` method.")

    @set.register
    def _(
        self,
        code: str,
        direction: Optional[DIRECTION_TYPES] = None,
        order_type: Optional[ORDER_TYPES] = None,
        status: Optional[ORDERSTATUS_TYPES] = None,
        volume: Optional[int] = None,
        limit_price: Optional[float] = None,
        frozen: Optional[float] = None,
        transaction_price: Optional[float] = None,
        transaction_volume: Optional[int] = None,
        remain: Optional[float] = None,
        fee: Optional[float] = None,
        timestamp: Optional[any] = None,
        order_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
    ):
        self._code: str = code

        if direction is not None:
            self._direction: DIRECTION_TYPES = direction

        if order_type is not None:
            self._order_type: ORDER_TYPES = order_type

        if status is not None:
            self._status = status

        if volume is not None:
            self._volume: int = volume

        if limit_price is not None:
            self._limit_price: float = limit_price

        if frozen is not None:
            self._frozen: float = frozen

        if transaction_price is not None:
            self._transaction_price: float = transaction_price

        if transaction_volume is not None:
            self._transaction_volume: float = transaction_volume

        if remain is not None:
            self._remain: float = remain

        if fee is not None:
            self._fee: float = fee

        if timestamp is not None:
            self._timestamp: datetime.datetime = datetime_normalize(timestamp)

        if order_id is not None:
            if len(order_id) > 0:
                self._uuid: str = order_id
            else:
                self._uuid = uuid.uuid4().hex

        if portfolio_id is not None:
            self._portfolio_id = portfolio_id

        if engine_id is not None:
            self._engine_id = engine_id

    @set.register
    def _(self, df: pd.Series):
        """
        Set from dataframe
        """
        self._code: str = df["code"]
        self._direction: DIRECTION_TYPES = DIRECTION_TYPES(df["direction"])
        self._order_type: ORDER_TYPES = ORDER_TYPES(df["order_type"])
        self._status: ORDERSTATUS_TYPES = ORDERSTATUS_TYPES(df["status"])
        self._volume: int = df["volume"]
        self._limit_price: float = df["limit_price"]
        self._frozen: float = df["frozen"]
        self._transaction_price: float = df["transaction_price"]
        self._transaction_volume: int = df["transaction_volume"]
        self._remain: float = df["remain"]
        self._fee: float = df["fee"]
        self._timestamp: datetime.datetime = df["timestamp"]
        self._uuid: str = df["uuid"]
        self._portfolio_id: str = df["portfolio_id"]
        self._engine_id: str = df["engine_id"]
        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df["source"]))

    @property
    def code(self) -> str:
        """
        Get the code of the order.

        Returns:
            str: The code.
        """
        return self._code

    @code.setter
    def code(self, value) -> None:
        """
        Set the code of the order.

        Args:
            value (str): The code to set.
        """
        self._code = value

    @property
    def timestamp(self) -> datetime.datetime:
        """
        Get the timestamp of the order.

        Returns:
            datetime.datetime: The timestamp.
        """
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value) -> None:
        """
        Set the timestamp of the order.

        Args:
            value (datetime.datetime): The timestamp to set.
        """
        self._timestamp = value

    @property
    def direction(self) -> DIRECTION_TYPES:
        return self._direction

    @direction.setter
    def direction(self, value) -> None:
        self._direction = value

    @property
    def order_type(self) -> ORDER_TYPES:
        return self._order_type

    @order_type.setter
    def order_type(self, value) -> None:
        self._order_type = value

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
    def transaction_volume(self) -> float:
        return self._transaction_volume

    @transaction_volume.setter
    def transaction_volume(self, value) -> None:
        self._transaction_volume = value

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
    def order_id(self) -> str:
        return self._uuid

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value) -> None:
        self._portfolio_id = value

    @property
    def engine_id(self) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

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
