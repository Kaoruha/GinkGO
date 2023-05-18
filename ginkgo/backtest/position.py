from ginkgo.backtest.base import Base
from ginkgo.libs import GINKGOLOGGER as gl


class Position(Base):
    def __init__(self, code="", price=0.0, volume=0 * args, **kwargs):
        super(Position, self).__init__(*args, **kwargs)
        self.code = ""
        self.price = 0
        self.volume = 0
        self.freeze = 0
        self.profit = 0
        self.fee = 0

    def set(self, code: str, price: float, volume: int):
        self.code = code
        self.price = price
        self.volume = volume

    def buy_done(self, price: float, volume: int) -> None:
        if price < 0 or volume < 0:
            gl.logger.critical(f"Illegal price:{price} or volume:{volume}")
            return
        old_price = self.price
        old_volume = self.volume
        self.volume += volume
        self.price = (old_price * old_volume + price * volume) / self.volume
        gl.logger.debug(
            f"POS {self.code} add {volume} at {price}. Final price: {price}, volume: {self.volume}, freeze: {self.freeze}"
        )

    def pre_sell(self, volume: int) -> None:
        if volume > self.volume:
            gl.logger.critical(
                f"POS {self.code} just has {self.volume} cant afford {volume}, please check your code"
            )

        self.volume -= volume
        self.freeze += volume
        gl.logger.debug(
            f"POS {self.code} freezed {volume}. Final volume:{self.volume} freeze: {self.freeze}"
        )

    def sold(self, price: float, volume: int) -> None:
        # TODO
        if price < 0:
            return
        if volume > self.freeze:
            gl.logger.critical(
                f"POS {self.code} just freezed {self.freeze} cant afford {volume}, please check your code"
            )
            return
        self.volume -= volume
        self.profit += (price - self.price) * volume
        gl.logger.debug(
            f"POS {self.code} sold {volume}. Final volume:{self.volume}  freeze:{self.freeze}"
        )

    def sell_cancel(self, volume: int) -> None:
        if volume > self.freeze:
            gl.logger.critical(
                f"POS {self.code} just freezed {self.freeze} cant afford {volume}, please check your code"
            )
            return

        self.freeze -= volume
        self.volume += volume
        gl.logger.debug(
            f"POS {self.code} unfreeze {volume}. Final volume:{self.volume}  freeze:{self.freeze}"
        )
