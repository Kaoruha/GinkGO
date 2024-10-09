import pandas as pd
import numpy
from functools import singledispatchmethod

from ginkgo.backtest.base import Base
from ginkgo.libs import base_repr
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.data.models import MPosition


class Position(Base):
    """
    Holding Position Class.
    """

    def __init__(
        self,
        portfolio_id: str = "",
        code: str = "",
        cost: float = 0.0,
        volume: int = 0,
        price: float = 0,
        frozen: int = 0,
        fee: float = 0,
        *args,
        **kwargs,
    ):
        super(Position, self).__init__(*args, **kwargs)
        self._portfolio_id = portfolio_id
        self._code = code
        self._cost = cost
        self._volume = volume
        self._frozen = frozen
        self._price = price
        self._fee = fee
        self._profit = 0
        self._worth = 0
        self.update_worth()
        self.update_profit()

    @singledispatchmethod
    def set(self, *args, **kwargs) -> None:
        pass

    @set.register
    def _(self, portfolio_id: str, code: str, cost: float, volume: int, fee: float, *args, **kwargs) -> None:
        """
        Data reset.
        return: none
        """
        self._portfolio_id = portfolio_id
        code = str(code)
        price = float(price)
        cost = float(cost)
        volume = int(volume)
        self._code = code
        self._price = price
        self._cost = cost
        self._volume = volume

    @set.register
    def _(self, df: pd.DataFrame, *args, **kwargs):
        self._portfolio_id = df["portfolio_id"]
        self._code = df["code"]
        self._cost = float(df["cost"])
        self._volume = int(df["volume"])
        self._frozen = int(df["frozen"])
        self._fee = float(df["fee"])
        self._profit = float(df["profit"])

    @set.register
    def _(self, model: MPosition, *args, **kwargs):
        self._portfolio_id = model.portfolio_id
        self._code = model.code
        self._cost = model.cost
        self._volume = model.volume
        self._frozen = model.frozen
        self._fee = model.fee
        self._profit = model.profit

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
    def worth(self, *args, **kwargs) -> float:
        """
        The worth of Position.
        """
        return self._worth

    def update_worth(self, *args, **kwargs) -> None:
        w = (self.volume + self.frozen) * self.price
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
        if not isinstance(self._price, (float, int)):
            GLOG.CRITICAL(f"Price is not a float/int: {self._price}")
            return 0
        return self._price

    @property
    def cost(self, *args, **kwargs) -> float:
        """
        Average Cost.
        """
        return float(self._cost)

    @property
    def frozen(self, *args, **kwargs) -> float:
        """
        Frozen amount of position.
        """
        if self._frozen < 0:
            GLOG.CRITICAL(f"Frozen is less than 0: {self._frozen}")
        if not isinstance(self._frozen, (int, numpy.int64)):
            GLOG.CRITICAL(f"Frozen is not a int: {self._frozen}")
            return 0
        return self._frozen

    def freeze(self, volume: int, *args, **kwargs) -> int:
        """
        Freeze Position.
        """
        volume = int(volume)
        if volume > self.volume:
            GLOG.CRITICAL(f"POS {self.code} just has {self.volume} cant afford {volume}, please check your code")
            return 0

        self._volume -= volume
        self._frozen += volume
        GLOG.INFO(f"POS {self.code} freezed {volume}. Final volume:{self.volume} frozen: {self.frozen}")
        return volume

    def unfreeze(self, volume: int, *args, **kwargs) -> int:
        """
        Unfreeze Position.
        """
        volume = int(volume)

        if volume > self.frozen:
            GLOG.CRITICAL(f"POS {self.code} just freezed {self.frozen} cant afford {volume}.")
            return

        self._frozen -= volume
        self._volume += volume
        GLOG.INFO(f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen: {self.frozen}")
        return self.volume

    @property
    def fee(self, *args, **kwargs) -> float:
        """
        Sum of fee.
        """
        if self._fee < 0:
            GLOG.CRITICAL(f"Fee is less than 0: {self._fee}")
        if not isinstance(self._fee, (float, int)):
            GLOG.CRITICAL(f"Fee is not a float/int: {self._fee}")
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
        self._profit = (self.volume + self.frozen) * (self.price - self.cost) - self.fee

    def _bought(self, price: float, volume: int, *args, **kwargs) -> int:
        """
        Deal with long trade.
        return: volume of position.
        """
        volume = int(volume)
        price = float(price)
        if price < 0 or volume < 0:
            GLOG.ERROR(f"Illegal price:{price} or volume:{volume}")
            return

        old_price = self.cost
        old_volume = self.volume
        self._volume += volume
        if self.volume == 0:
            GLOG.ERROR("Should not have 0 volume after BUY.")
            return
        else:
            self._cost = (old_price * old_volume + price * volume) / self.volume
            self._cost = round(self._cost, 4)
        self.on_price_update(price)

        # Check cost
        if self._cost < 0:
            GLOG.CRITICAL(f"Cost is less than 0: {self._cost}")
            return

        if not isinstance(self._cost, (float, int)):
            GLOG.CRITICAL(f"Cost is not a float/int: {self._cost}")
            return
        GLOG.DEBUG(
            f"POS {self.code} add {volume} at {price}. Final price: {price}, volume: {self.volume}, frozen: {self.frozen}"
        )
        return self.volume

    def _sold(self, price: float, volume: int, *args, **kwargs) -> int:
        """
        Deal with short trade.
        return: volume of position.
        """
        if price <= 0:
            GLOG.CRITICAL(f"Illegal price: {price} at SOLD.")
            return
        if volume <= 0:
            GLOG.CRITICAL(f"Illegal volume: {volume} at SOLD.")
            return
        GLOG.WARN(f"Position --")
        volume = int(volume)
        price = float(price)
        if volume > self.frozen:
            GLOG.CRITICAL(f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code")
            return
        self._frozen -= volume
        self.on_price_update(price)
        GLOG.DEBUG(f"POS {self.code} sold {volume}. Final volume:{self.volume}  frozen:{self.frozen}")
        return self.volume

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int, *args, **kwargs) -> None:
        """
        Dealing with successful Trade.
        """
        if direction == DIRECTION_TYPES.LONG:
            self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            self._sold(price, volume)
        self.update_profit()
        self.update_worth()

    def on_price_update(self, price: float, *args, **kwargs) -> float:
        """
        Dealing with price update
        return: latest price of position
        """
        if not isinstance(price, float):
            GLOG.CRITICAL(f"Illegal price: {price} at on_price_update")
            return
        self._price = price
        self.update_profit()
        self.update_worth()
        return self.price

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)
