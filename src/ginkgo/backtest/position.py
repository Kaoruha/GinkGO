from ginkgo.backtest.base import Base
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs import base_repr
from ginkgo.enums import DIRECTION_TYPES


class Position(Base):
    def __init__(self, code="", price=0.0, volume=0, *args, **kwargs):
        super(Position, self).__init__(*args, **kwargs)
        self._code = code
        self._price = price
        self._cost = price
        self.volume = volume
        self._frozen = 0
        self._fee = 0

    @property
    def worth(self) -> float:
        return round((self.volume + self.frozen) * self.price, 4)

    @property
    def code(self) -> str:
        return self._code

    @property
    def price(self) -> float:
        return self._price

    @property
    def cost(self) -> float:
        return self._cost

    @property
    def frozen(self) -> float:
        return self._frozen

    @property
    def fee(self) -> float:
        return self._fee

    @property
    def profit(self) -> float:
        return (self.volume + self.frozen) * (self.price - self.cost) - self.fee

    def _bought(self, price: float, volume: int) -> None:
        GLOG.WARN(f"Position ++")
        if price < 0 or volume < 0:
            GLOG.ERROR(f"Illegal price:{price} or volume:{volume}")
            return
        old_price = self.cost
        old_volume = self.volume
        self.volume += volume
        self._cost = (old_price * old_volume + price * volume) / self.volume
        self._cost = round(self._cost, 4)
        self.on_price_update(price)
        GLOG.INFO(
            f"POS {self.code} add {volume} at {price}. Final price: {price}, volume: {self.volume}, frozen: {self.frozen}"
        )
        GLOG.WARN(f"Position ++ DONE")

    def _sold(self, price: float, volume: int) -> None:
        if price < 0:
            return
        if volume > self.frozen:
            GLOG.ERROR(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code"
            )
            return

        self._frozen -= volume
        self.on_price_update(price)
        GLOG.WARN(
            f"POS {self.code} sold {volume}. Final volume:{self.volume}  frozen:{self.frozen}"
        )

    def on_price_update(self, price: float) -> None:
        self._price = price

    def set(self, code: str, price: float, volume: int) -> None:
        self._code = code
        self._price = price
        self._cost = price
        self.volume = volume

    def deal(self, direction: DIRECTION_TYPES, price: float, volume: int) -> None:
        if direction == DIRECTION_TYPES.LONG:
            self._bought(price, volume)
        elif direction == DIRECTION_TYPES.SHORT:
            self._sold(price, volume)
        else:
            GLOG.ERROR(
                f"Can not handle this deal. direction:{direction}  price:{price}  volume:{volume}"
            )

    def freeze(self, volume: int) -> int:
        if volume > self.volume:
            GLOG.ERROR(
                f"POS {self.code} just has {self.volume} cant afford {volume}, please check your code"
            )
            return self.volume

        self.volume -= volume
        self._frozen += volume
        GLOG.INFO(
            f"POS {self.code} freezed {volume}. Final volume:{self.volume} frozen: {self.frozen}"
        )
        return volume

    def unfreeze(self, volume: int) -> None:
        GLOG.WARN("START UNFREEZE...")
        if volume > self.frozen:
            GLOG.ERROR(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}."
            )
            return

        self._frozen -= volume
        self.volume += volume
        GLOG.INFO(
            f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen: {self.frozen}"
        )
        GLOG.WARN("DONE UNFREEZE.")

    def add_fee(self, fee: float) -> None:
        self._fee += fee

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)
