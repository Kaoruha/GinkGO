import numpy

from ginkgo.backtest.base import Base
from ginkgo.libs import base_repr
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import DIRECTION_TYPES


class Position(Base):
    """
    Holding Position Class.
    """

    def __init__(self, code="", price=0.0, volume=0, *args, **kwargs):
        super(Position, self).__init__(*args, **kwargs)
        self._code = code
        self._price = price
        self._cost = price
        self._volume = volume
        self._frozen = 0
        self._fee = 0
        self._profit = 0
        self._worth = 0
        self._backtest_id = ""

    def set(
        self,
        code: str,
        price: float,
        cost: float,
        volume: int,
        frozen: float,
        fee: float,
        profit: float,
    ):
        self._code = code
        self._price = price
        self._cost = cost
        self._volume = volume
        self._frozen = frozen
        self._fee = fee
        self._profit = profit

    @property
    def backtest_id(self) -> str:
        return self._backtest_id

    def set_backtest_id(self, value: str) -> str:
        """
        Backtest ID update.

        Args:
            value(str): new backtest id
        Returns:
            current backtest id
        """
        self._backtest_id = value
        return self.backtest_id

    @property
    def volume(self) -> int:
        """
        The Amount of position.
        """
        if self._volume < 0:
            GLOG.CRITICAL(f"Volume is less than 0: {self._volume}")
            import pdb

            pdb.set_trace()
            return 0
        if not isinstance(self._volume, (int, numpy.int64)):
            GLOG.CRITICAL(f"Volume is not a int: {self._volume}")
            import pdb

            pdb.set_trace()
            return 0
        return self._volume

    @property
    def worth(self) -> float:
        """
        The worth of Position.
        """
        return self._worth

    def update_worth(self) -> None:
        w = (self.volume + self.frozen) * self.price
        self._worth = round(w, 2)

    @property
    def code(self) -> str:
        """
        Position Code.
        """
        return self._code

    @property
    def price(self) -> float:
        """
        Current Price.
        """
        if self._price < 0:
            GLOG.CRITICAL(f"Price is less than 0: {self._price}")
            import pdb

            pdb.set_trace()
            return 0
        if not isinstance(self._price, (float, int)):
            GLOG.CRITICAL(f"Price is not a float/int: {self._price}")
            import pdb

            pdb.set_trace()
            return 0
        return self._price

    @property
    def cost(self) -> float:
        """
        Average Cost.
        """
        return self._cost

    @property
    def frozen(self) -> float:
        """
        Frozen amount of position.
        """
        if self._frozen < 0:
            GLOG.CRITICAL(f"Frozen is less than 0: {self._frozen}")
            import pdb

            pdb.set_trace()
            return 0
        if not isinstance(self._frozen, (int, numpy.int64)):
            GLOG.CRITICAL(f"Frozen is not a int: {self._frozen}")
            import pdb

            pdb.set_trace()
            return 0
        return self._frozen

    def freeze(self, volume: int) -> int:
        """
        Freeze Position.
        """
        volume = int(volume)
        if volume > self.volume:
            GLOG.CRITICAL(
                f"POS {self.code} just has {self.volume} cant afford {volume}, please check your code"
            )
            import pdb

            pdb.set_trace()
            return self.volume

        self._volume -= volume
        self._frozen += volume
        GLOG.INFO(
            f"POS {self.code} freezed {volume}. Final volume:{self.volume} frozen: {self.frozen}"
        )
        return self.volume

    def unfreeze(self, volume: int) -> int:
        """
        Unfreeze Position.
        """
        volume = int(volume)

        if volume > self.frozen:
            GLOG.CRITICAL(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}."
            )
            import pdb

            pdb.set_trace()
            return

        self._frozen -= volume
        self._volume += volume
        GLOG.INFO(
            f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen: {self.frozen}"
        )
        return self.volume

    @property
    def fee(self) -> float:
        """
        Sum of fee.
        """
        if self._fee < 0:
            GLOG.CRITICAL(f"Fee is less than 0: {self._fee}")
            import pdb

            pdb.set_trace()
            return 0
        if not isinstance(self._fee, (float, int)):
            GLOG.CRITICAL(f"Fee is not a float/int: {self._fee}")
            import pdb

            pdb.set_trace()
            return 0
        return self._fee

    def add_fee(self, fee: float) -> float:
        if fee < 0:
            GLOG.CRITICAL(f"Can not add fee less than 0.")
            return
        self._fee += fee
        return self.fee

    @property
    def profit(self) -> float:
        """
        Current Profit of the position.
        """
        return self._profit

    def update_profit(self) -> None:
        """
        Update Profit. Call after Trade Done or Price Update.
        """
        self._profit = (self.volume + self.frozen) * (self.price - self.cost) - self.fee

    def _bought(self, price: float, volume: int) -> int:
        """
        Deal with long trade.
        return: volume of position.
        """
        GLOG.WARN(f"Position ++")
        volume = int(volume)
        price = float(price)
        if price < 0 or volume < 0:
            GLOG.ERROR(f"Illegal price:{price} or volume:{volume}")
            import pdb

            pdb.set_trace()
            return

        old_price = self.cost
        old_volume = self.volume
        self._volume += volume
        if self.volume == 0:
            GLOG.ERROR("Should not have 0 volume after BUY.")
            import pdb

            pdb.set_trace()
            return
        else:
            self._cost = (old_price * old_volume + price * volume) / self.volume
            self._cost = round(self._cost, 4)
        self.on_price_update(price)

        # Check cost
        if self._cost < 0:
            GLOG.CRITICAL(f"Cost is less than 0: {self._cost}")
            import pdb

            pdb.set_trace()
            return

        if not isinstance(self._cost, (float, int)):
            GLOG.CRITICAL(f"Cost is not a float/int: {self._cost}")
            import pdb

            pdb.set_trace()
            return
        GLOG.DEBUG(
            f"POS {self.code} add {volume} at {price}. Final price: {price}, volume: {self.volume}, frozen: {self.frozen}"
        )
        GLOG.WARN(f"Position ++ DONE")
        return self.volume

    def _sold(self, price: float, volume: int) -> int:
        """
        Deal with short trade.
        return: volume of position.
        """
        if price <= 0:
            GLOG.CRITICAL(f"Illegal price: {price} at SOLD.")
            import pdb

            pdb.set_trace()
            return
        if volume <= 0:
            GLOG.CRITICAL(f"Illegal volume: {volume} at SOLD.")
            import pdb

            pdb.set_trace()
            return
        GLOG.WARN(f"Position --")
        volume = int(volume)
        price = float(price)
        if volume > self.frozen:
            GLOG.CRITICAL(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code"
            )
            import pdb

            pdb.set_trace()
            return
        self._frozen -= volume
        self.on_price_update(price)
        GLOG.DEBUG(
            f"POS {self.code} sold {volume}. Final volume:{self.volume}  frozen:{self.frozen}"
        )
        return self.volume

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int) -> None:
        """
        Dealing with successful Trade.
        """
        if direction == DIRECTION_TYPES.LONG:
            self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            self._sold(price, volume)
        self.update_profit()
        self.update_worth()

    def on_price_update(self, price: float) -> float:
        """
        Dealing with price update
        return: latest price of position
        """
        if not isinstance(price, float):
            GLOG.CRITICAL(f"Illegal price: {price} at on_price_update")
            import pdb

            pdb.set_trace()
            return
        self._price = price
        self.update_profit()
        self.update_worth()
        return self.price

    def set(self, code: str, price: float, volume: int) -> None:
        """
        Data reset.
        return: none
        """
        code = str(code)
        price = float(price)
        volume = int(volume)
        self._code = code
        self._price = price
        self._cost = price
        self._volume = volume

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)
