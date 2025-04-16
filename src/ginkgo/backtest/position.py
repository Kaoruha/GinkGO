import pandas as pd
import numpy
from typing import List, Optional, Union
from functools import singledispatchmethod
from decimal import Decimal
from ginkgo.libs import base_repr, Number, to_decimal, GLOG
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.backtest.base import Base


class Position(Base):
    """
    Holding Position Class.
    """

    def __init__(
        self,
        portfolio_id: str = "",
        engine_id: str = "",
        code: str = "",
        cost: Union[float, Decimal] = 0.0,
        volume: int = 0,
        frozen_volume: int = 0,
        price: Union[float, Decimal] = 0.0,
        frozen: int = 0,
        fee: Union[float, Decimal] = 0.0,
        uuid: str = "",
        *args,
        **kwargs,
    ):
        super(Position, self).__init__(uuid, *args, **kwargs)
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._code = code
        self._cost = cost if isinstance(cost, Decimal) else Decimal(str(cost))
        self._volume = volume
        self._frozen_volume = frozen_volume
        self._frozen_money = frozen
        self._price = price if isinstance(price, Decimal) else Decimal(str(price))
        self._fee = fee if isinstance(fee, Decimal) else Decimal(str(fee))
        self._uuid = uuid
        self._profit = 0
        self._worth = 0
        self.update_worth()
        self.update_profit()

    @singledispatchmethod
    def set(self, obj, *args, **kwargs) -> None:
        raise NotImplementedError("Unsupported type")

    @set.register
    def _(
        self,
        portfolio_id: str,
        engine_id: str,
        code: str,
        cost: Union[float, Decimal],
        volume: int,
        frozen_volume: int,
        fee: Union[float, Decimal],
        uuid: Optional[str] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Data reset.
        return: none
        """
        self._portfolio_id = portfolio_id
        self._engine_id = engine_id
        self._code = code
        self._price = price if isinstance(price, Decimal) else Decimal(str(price))
        self._cost = cost if isinstance(cost, Decimal) else Decimal(str(cost))
        self._volume = volume
        self._frozen_volume = frozen_volume
        if uuid is not None:
            self._uuid = uuid

    @set.register
    def _(self, df: pd.Series, *args, **kwargs):
        self._portfolio_id = df["portfolio_id"]
        self._engine_id = df["engine_id"]
        self._code = df["code"]
        self._cost = df["cost"] if isinstance(df["cost"], Decimal) else Decimal(str(df["cost"]))
        self._volume = int(df["volume"])
        self._frozen_volume = int(df["frozen_volume"])
        self._frozen_money = int(df["frozen_money"])
        self._fee = df["fee"] if isinstance(df["fee"], Decimal) else Decimal(str(df["fee"]))
        self._profit = float(df["profit"])
        self._uuid = df["uuid"]

    @property
    def portfolio_id(self, *args, **kwargs) -> str:
        return self._portfolio_id

    def set_portfolio_id(self, value: str, *args, **kwargs) -> str:
        """
        Backtest ID update.

        Args:
            value(str): new backtest id
        Returns:
            current backtest id
        """
        self._portfolio_id = value
        return self._portfolio_id

    @property
    def engine_id(self, *args, **kwargs) -> str:
        return self._engine_id

    @engine_id.setter
    def engine_id(self, value) -> None:
        self._engine_id = value

    @property
    def volume(self, *args, **kwargs) -> int:
        """
        The Amount of position.
        """
        if self._volume < 0:
            GLOG.CRITICAL(f"Volume is less than 0: {self._volume}")
            return 0
        if not isinstance(self._volume, (int, numpy.int64)):
            GLOG.CRITICAL(f"Volume is not a int: {self._volume}")
            return 0
        return self._volume

    @property
    def frozen_money(self, *args, **kwargs) -> int:
        if self._frozen_money < 0:
            GLOG.CRITICAL(f"Frozen money is less than 0: {self._frozen_money}")
            return 0
        return self._frozen_money

    @property
    def worth(self, *args, **kwargs) -> float:
        """
        The worth of Position.
        """
        return self._worth

    def update_worth(self, *args, **kwargs) -> None:
        w = (self.volume + self.frozen_volume) * self.price
        self._worth = round(w, 2)

    @property
    def code(self, *args, **kwargs) -> str:
        """
        Position Code.
        """
        return self._code

    @property
    def price(self, *args, **kwargs) -> float:
        """
        Current Price.
        """
        if self._price < 0:
            GLOG.CRITICAL(f"Price is less than 0: {self._price}")
        if not isinstance(self._price, Decimal):
            GLOG.CRITICAL(f"Price is not a DECIMAL: {self._price}")
            return 0
        return self._price

    @property
    def cost(self, *args, **kwargs) -> float:
        """
        Average Cost.
        """
        return self._cost

    @property
    def frozen_volume(self, *args, **kwargs) -> float:
        """
        Frozen amount of position.
        """
        if self._frozen_volume < 0:
            GLOG.CRITICAL(f"Frozen is less than 0: {self._frozen_volume}")
        if not isinstance(self._frozen_volume, (int, numpy.int64)):
            GLOG.CRITICAL(f"Frozen is not a int: {self._frozen_volume}")
            return 0
        return self._frozen_volume

    def freeze(self, volume: int, *args, **kwargs) -> bool:
        """
        Freeze Position.
        Args:
            volume (int): Amount to freeze.
        Returns:
            bool: Success or failure.
        """
        if volume <= 0:
            GLOG.CRITICAL(f"Invalid freeze volume: {volume}")
            return False
        volume = int(volume)
        if volume > self.volume:
            GLOG.CRITICAL(f"Insufficient volume to freeze: {volume}, available: {self.volume}")
            return False

        self._volume -= volume
        self._frozen_volume += volume
        GLOG.INFO(f"Freezed {volume} units. Remaining: {self.volume}, Frozen: {self.frozen_volume}")
        return True

    def unfreeze(self, volume: int, *args, **kwargs) -> int:
        """
        Unfreeze Position.
        """
        volume = int(volume)

        if volume > self.frozen_volume:
            GLOG.CRITICAL(f"POS {self.code} just freezed {self.frozen} cant afford {volume}.")
            return

        self._frozen_volume -= volume
        self._volume += volume
        GLOG.INFO(f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen_volume: {self.frozen_volume}")
        return self.volume

    @property
    def fee(self, *args, **kwargs) -> float:
        """
        Sum of fee.
        """
        if self._fee < 0:
            GLOG.CRITICAL(f"Fee is less than 0: {self._fee}")
        if not isinstance(self._price, Decimal):
            GLOG.CRITICAL(f"Fee is not a DECIMAL: {self._fee}")
            return 0
        return self._fee

    def add_fee(self, fee: float, *args, **kwargs) -> float:
        if fee < 0:
            GLOG.CRITICAL(f"Can not add fee less than 0.")
            return
        self._fee += fee
        return self.fee

    @property
    def profit(self, *args, **kwargs) -> float:
        """
        Current Profit of the position.
        """
        return self._profit

    def update_profit(self, *args, **kwargs) -> None:
        """
        Update Profit. Call after Trade Done or Price Update.
        """
        self._profit = (self.volume + self.frozen_volume) * (self.price - self.cost) - self.fee

    def _bought(self, price: Number, volume: int, *args, **kwargs) -> bool:
        """
        Handle a long trade.

        Args:
            price (Number): The price at which the position is bought.
            volume (int): The volume of the position to be added.

        Returns:
            bool: Whether the operation was successful.
        """
        try:
            volume = int(volume)
            price = to_decimal(price)
            if price <= 0 or volume <= 0:
                raise ValueError(f"Invalid price: {price} or volume: {volume}")
        except Exception as e:
            GLOG.ERROR(f"Invalid input - price: {price}, volume: {volume}, error: {e}")
            return False
        finally:
            pass

        try:
            prev_price = self.cost
            prev_volume = self.volume
            self._volume += volume
            self._cost = (prev_price * prev_volume + price * volume) / self.volume
            self.on_price_update(price)
            # Check cost
            if self._cost < 0:
                GLOG.CRITICAL(f"Cost is less than 0: {self._cost}")
                return
            if not isinstance(self._cost, Decimal):
                GLOG.CRITICAL(f"Cost is not a DECIMAL: {self._cost}")
                return
            GLOG.DEBUG(f"POS {self.code} added {volume} at ${price}. Final price: ${self._cost}, ")
            GLOG.DEBUG(f"volume: {self.volume}, cost: ${self.cost}, frozen: {self.frozen_volume}")
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            pass

    def _sold(self, price: float, volume: int, *args, **kwargs) -> bool:
        """
        Handle a short trade.

        Args:
            price (float): The price at which the position is sold.
            volume (int): The volume of the position to be reduced.

        Returns:
            bool: Whether the operation was successful.
        """
        # 参数校验
        try:
            volume = int(volume)
            price = float(price)
            if price <= 0 or volume <= 0:
                raise ValueError(f"Invalid price: {price} or volume: {volume}")
        except Exception as e:
            GLOG.error(f"Invalid input - price: {price}, volume: {volume}, error: {e}")
            return False
        finally:
            pass

        if volume > self.frozen_volume:
            GLOG.CRITICAL(f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code")
            return False

        # 执行卖出逻辑
        try:
            self._frozen_volume -= volume
            self.on_price_update(price)
            # 日志记录
            GLOG.DEBUG(
                f"POS {self.code} sold {volume} at ${price}. "
                f"Final price: ${self._cost}, volume: {self.volume}, "
                f"cost: ${self.cost}, frozen: {self.frozen_volume}"
            )
            return True
        except Exception as e:
            import pdb

            pdb.set_trace()
            GLOG.ERROR(f"Error during sell operation - price: {price}, volume: {volume}, error: {e}")
        finally:
            pass

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int, *args, **kwargs) -> None:
        """
        Handles successful trade execution.

        Args:
            direction (DIRECTION_TYPES): Trade direction (LONG or SHORT).
            price (float): Execution price.
            volume (int): Execution volume.

        Example:
            position.deal(DIRECTION_TYPES.LONG, 100.5, 50)
        """
        if direction == DIRECTION_TYPES.LONG:
            self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            self._sold(price, volume)
        self.update_profit()
        self.update_worth()

    def on_price_update(self, price: Union[float, int, Decimal], *args, **kwargs) -> Decimal:
        """
        Dealing with price update
        return: latest price of position
        """
        self._price = price if isinstance(price, Decimal) else Decimal(str(price))
        self.update_profit()
        self.update_worth()
        return self._price

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)
