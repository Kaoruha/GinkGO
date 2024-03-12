from ginkgo.backtest.base import Base
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import base_repr
from ginkgo.enums import DIRECTION_TYPES
import numpy


class Position(Base):
    def __init__(self, code="", price=0.0, volume=0, *args, **kwargs):
        super(Position, self).__init__(*args, **kwargs)
        self._code = code
        self._price = price
        self._cost = price
        self._volume = volume
        self._frozen = 0
        self._fee = 0

    @property
    def volume(self) -> int:
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
        return round((self.volume + self.frozen) * self.price, 4)

    @property
    def code(self) -> str:
        return self._code

    @property
    def price(self) -> float:
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
        if self._cost < 0:
            GLOG.CRITICAL(f"Cost is less than 0: {self._cost}")
            import pdb

            pdb.set_trace()
            return 0
        if not isinstance(self._cost, (float, int)):
            GLOG.CRITICAL(f"Cost is not a float/int: {self._cost}")
            import pdb

            pdb.set_trace()
            return 0
        return self._cost

    @property
    def frozen(self) -> float:
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

    @property
    def fee(self) -> float:
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

    @property
    def profit(self) -> float:
        return (self.volume + self.frozen) * (self.price - self.cost) - self.fee

    def _bought(self, price: float, volume: int) -> None:
        GLOG.WARN(f"Position ++")
        if price < 0 or volume < 0:
            GLOG.ERROR(f"Illegal price:{price} or volume:{volume}")
            import pdb

            pdb.set_trace()
            return
        volume = int(volume)
        old_price = self.cost
        old_volume = self.volume
        self._volume += volume
        if self.volume == 0:
            GLOG.CRITICAL("Should not have 0 volume after BUY.")
            import pdb

            pdb.set_trace()
            self._cost = 0
        else:
            self._cost = (old_price * old_volume + price * volume) / self.volume
            self._cost = round(self._cost, 4)
        self.on_price_update(price)
        GLOG.INFO(
            f"POS {self.code} add {volume} at {price}. Final price: {price}, volume: {self.volume}, frozen: {self.frozen}"
        )
        GLOG.WARN(f"Position ++ DONE")

    def _sold(self, price: float, volume: int) -> None:
        if price < 0:
            GLOG.CRITICAL(f"Illegal price: {price} at SOLD.")
            import pdb

            pdb.set_trace()
            return
        if volume < 0:
            GLOG.CRITICAL(f"Illegal volume: {volume} at SOLD.")
            import pdb

            pdb.set_trace()
            return
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

    def on_price_update(self, price: float) -> None:
        if not isinstance(price, float):
            GLOG.CRITICAL(f"illegal price: {price} at on_price_update")
            import pdb

            pdb.set_trace()
            return
        self._price = price

    def set(self, code: str, price: float, volume: int) -> None:
        code = str(code)
        price = float(price)
        volume = int(volume)
        self._code = code
        self._price = price
        self._cost = price
        self._volume = volume

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int) -> None:
        if direction == DIRECTION_TYPES.LONG:
            self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            self._sold(price, volume)
        else:
            GLOG.CRITICAL(
                f"Can not handle this deal. direction:{direction}  price:{price}  volume:{volume}"
            )
            import pdb

            pdb.set_trace()

    def freeze(self, volume: int) -> int:
        if volume > self.volume:
            GLOG.CRITICAL(
                f"POS {self.code} just has {self.volume} cant afford {volume}, please check your code"
            )
            import pdb

            pdb.set_trace()
            return self.volume
        volume = int(volume)

        self._volume -= volume
        self._frozen += volume
        GLOG.INFO(
            f"POS {self.code} freezed {volume}. Final volume:{self.volume} frozen: {self.frozen}"
        )
        return volume

    def unfreeze(self, volume: int) -> None:
        if volume > self.frozen:
            GLOG.CRITICAL(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}."
            )
            import pdb

            pdb.set_trace()
            return

        volume = int(volume)
        self._frozen -= volume
        self._volume += volume
        GLOG.INFO(
            f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen: {self.frozen}"
        )

    def add_fee(self, fee: float) -> None:
        self._fee += fee

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)
