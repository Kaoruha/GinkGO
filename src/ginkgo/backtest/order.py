import pandas as pd
import datetime
import uuid
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
        self._code: str = code
        self._direction: DIRECTION_TYPES = direction
        self._order_type: ORDER_TYPES = order_type
        self._status = status
        self._volume: int = volume
        self._limit_price: float = limit_price
        self._frozen: float = frozen
        self._transaction_price: float = transaction_price
        self._transaction_volume: float = transaction_volume
        self._remain: float = remain
        self._fee: float = fee
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)

        if len(order_id) > 0:
            self._uuid: str = order_id
        else:
            self._uuid = uuid.uuid4().hex

        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
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
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        status: ORDERSTATUS_TYPES,
        volume: int,
        limit_price: float,
        frozen: float,
        transaction_price: float,
        transaction_volume: int,
        remain: float,
        fee: float,
        timestamp: any,
        order_id: str,
        portfolio_id: str,
        engine_id: str,
    ):
        if not isinstance(code, str):
            raise ValueError("Code must be a string.")
        if not isinstance(direction, DIRECTION_TYPES):
            raise ValueError("Direction must be a valid DIRECTION_TYPES enum.")
        if not isinstance(order_type, ORDER_TYPES):
            raise ValueError("Type must be a valid ORDER_TYPES enum.")
        if not isinstance(status, ORDERSTATUS_TYPES):
            raise ValueError("Status must be a valid ORDERSTATUS_TYPES enum.")
        if not isinstance(volume, int) or volume < 0:
            raise ValueError("Volume must be a non-negative integer.")
        if not isinstance(limit_price, (int, float)) or limit_price < 0:
            raise ValueError("Limit price must be a non-negative number.")
        if not isinstance(frozen, (int, float, Decimal)) or frozen < 0:
            raise ValueError(f"Frozen must be a non-negative number. {frozen} not valid. {type(frozen)}")
        if not isinstance(transaction_price, (int, float, Decimal)) or transaction_price < 0:
            raise ValueError(
                f"Transaction price must be a non-negative number. {transaction_price} not valid. {type(transaction_price)}"
            )
        if not isinstance(transaction_volume, int) or transaction_volume < 0:
            raise ValueError(
                f"Transaction volume must be a non-negative integer. {transaction_volume} not valid. {type(transaction_volume)}"
            )
        if not isinstance(remain, (int, float, Decimal)) or remain < 0:
            raise ValueError(f"Remain must be a non-negative number. {remain} not valid. {type(remain)}")
        if not isinstance(fee, (int, float, Decimal)) or fee < 0:
            raise ValueError(f"Fee must be a non-negative number. {fee} not valid. {type(fee)}")
        if not isinstance(order_id, str):
            raise ValueError("Order ID must be a string.")
        if not isinstance(portfolio_id, str):
            raise ValueError("Portfolio ID must be a string.")
        if not isinstance(engine_id, str):
            raise ValueError("Portfolio ID must be a string.")

        self._code: str = code
        self._direction: DIRECTION_TYPES = direction
        self._order_type: ORDER_TYPES = order_type
        self._status = status
        self._volume: int = volume
        self._limit_price: float = limit_price
        self._frozen: float = frozen
        self._transaction_price: float = transaction_price
        self._transaction_volume: float = transaction_volume
        self._remain: float = remain
        self._fee: float = fee
        self._timestamp: datetime.datetime = datetime_normalize(timestamp)

        if len(order_id) > 0:
            self._uuid: str = order_id
        else:
            self._uuid = uuid.uuid4().hex

        self._portfolio_id = portfolio_id
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
    def engine_id(self, *args, **kwargs) -> str:
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
