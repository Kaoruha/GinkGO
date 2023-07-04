from ginkgo.backtest.base import Base
from ginkgo.libs import GLOG
from ginkgo.libs.ginkgo_pretty import base_repr


class Position(Base):
    def __init__(self, code="", price=0.0, volume=0, *args, **kwargs):
        super(Position, self).__init__(*args, **kwargs)
        self.code = ""
        self.price = price
        self.volume = volume
        self.frozen = 0
        self.profit = 0
        self.fee = 0

    def set(self, code: str, price: float, volume: int):
        self.code = code
        self.price = price
        self.volume = volume

    def buy_done(self, price: float, volume: int) -> None:
        if price < 0 or volume < 0:
            GLOG.logger.critical(f"Illegal price:{price} or volume:{volume}")
            return
        old_price = self.price
        old_volume = self.volume
        self.volume += volume
        self.price = (old_price * old_volume + price * volume) / self.volume
        GLOG.logger.debug(
            f"POS {self.code} add {volume} at {price}. Final price: {price}, volume: {self.volume}, frozen: {self.frozen}"
        )

    def pre_sell(self, volume: int) -> None:
        if volume > self.volume:
            GLOG.logger.critical(
                f"POS {self.code} just has {self.volume} cant afford {volume}, please check your code"
            )

        self.volume -= volume
        self.frozen += volume
        GLOG.logger.debug(
            f"POS {self.code} freezed {volume}. Final volume:{self.volume} frozen: {self.frozen}"
        )

    def sold(self, price: float, volume: int) -> None:
        # TODO
        if price < 0:
            return
        if volume > self.frozen:
            GLOG.logger.critical(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code"
            )
            return
        self.frozen -= volume
        self.profit += (price - self.price) * volume
        GLOG.logger.debug(
            f"POS {self.code} sold {volume}. Final volume:{self.volume}  frozen:{self.frozen}"
        )

    def sell_cancel(self, volume: int) -> None:
        if volume > self.frozen:
            GLOG.logger.critical(
                f"POS {self.code} just freezed {self.frozen} cant afford {volume}, please check your code"
            )
            return

        self.frozen -= volume
        self.volume += volume
        GLOG.logger.debug(
            f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  frozen: {self.frozen}"
        )

    def __repr__(self) -> str:
        return base_repr(self, Position.__name__, 12, 60)
