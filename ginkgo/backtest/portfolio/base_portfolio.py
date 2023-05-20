import datetime
from ginkgo.backtest.order import Order
from ginkgo.backtest.position import Position
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.libs import GINKGOLOGGER as gl
from ginkgo.libs.ginkgo_math import cal_fee


class BasePortfolio(object):
    def __init__(self, *args, **kwargs) -> None:
        self.name: str = "Fucking World"
        self.cash: float = 100000
        self.frozen: float = 0
        self.position: dict = {}
        self.tax_rate: float = 0.03

    def _check_position(self, code: str) -> bool:
        if code in self.position.keys():
            return True
        else:
            return False

    def pre_buy_limit(
        self, code: str, limit_price: float, volume: int, timestamp: str or datetime
    ) -> Order:
        o = Order()
        o.set(
            code,
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.LIMITORDER,
            volume,
            limit_price,
            timestamp,
        )
        money = limit_price * volume
        money += cal_fee(DIRECTION_TYPES.LONG, money, self.tax_rate)

        if money < self.cash:
            self.cash -= money
            self.frozen += money
            gl.logger.debug(
                f"Port {self.name} prebuy {code}:{volume} with limit {limit_price} on {timestamp}"
            )
            return o

        else:
            gl.logger.critical(
                f"Only have Cash: {self.cash}. Can not afford {code} with Price: {limit_price} * {volume}."
            )
            return None

        # TODO Backtest System need to rewirte this func to put the event
        # TODO Live System need to rewrite this func to put the order to Real Market

    def pre_buy_market(
        self, code: str, money: float, timestamp: str or datetime.datetime
    ) -> Order:
        if money > self.cash:
            gl.logger.critical(
                f"Only have Cash: {self.cash}. Can not afford {code} with {money}."
            )
            return None

        o = Order()
        o.set(
            code,
            DIRECTION_TYPES.LONG,
            ORDER_TYPES.MARKETORDER,
            0,
            money,
            timestamp,
        )
        gl.logger.debug(
            f"Portfolio {self.name} prebuy {code} with {money} at marketprice on {timestamp}"
        )
        self.cash -= money
        self.frozen += money
        return o

        # TODO Backtest System need to rewirte this func to put the event
        # TODO Live System need to rewrite this func to put the order to Real Market

    def pre_sell_limit(
        self,
        code: str,
        limit_price: float,
        volume: int,
        timestamp: str or datetime.datetime,
    ) -> Order:
        print("===========================")
        print(volume)
        if not self._check_position(code):
            gl.logger.critical(f"Portfolio:{self.name} do not have Position:{code}")
            return

        if volume <= 0:
            gl.logger.critical(f"Illegal volume {volume}")
            return

        if volume > self.position[code].volume:
            gl.logger.warn(
                f"Portfolio:{self.name} just have {self.position[code].volume}. Adjust {volume} ==>> {self.position[code].volume}"
            )
            volume = self.position[code].volume

        o = Order()
        o.set(
            code,
            DIRECTION_TYPES.SHORT,
            ORDER_TYPES.LIMITORDER,
            volume,
            limit_price,
            timestamp,
        )
        o.set_source(SOURCE_TYPES.PORTFOLIO)
        gl.logger.debug(
            f"Port {self.name} presell {code}:{volume} with limit {limit_price} on {timestamp}"
        )
        self.position[code].pre_sell(volume)
        return o

    def pre_sell_market(
        self, code: str, volume: int, timestamp: str or datetime.datetime
    ) -> Order:
        if not self._check_position(code):
            gl.logger.critical(f"Portfolio:{self.name} do not have Position:{code}")
            return
        if volume <= 0:
            gl.logger.critical(f"Illegal volume {volume}")
            return
        if volume > self.position[code].volume:
            gl.logger.warn(
                f"Portfolio:{self.name} just have {self.position[code].volume}. Adjust {volume} ==>> {self.position[code].volume}"
            )
            volume = self.position[code].volume
        o = Order()
        o.set(
            code,
            DIRECTION_TYPES.SHORT,
            ORDER_TYPES.MARKETORDER,
            volume,
            0,
            timestamp,
        )
        gl.logger.debug(f"Port {self.name} presell {code}:{volume} on {timestamp}")
        self.position[code].pre_sell(volume)
        return o

    def buy_done(
        self, code: str, price: float, volume: int, freezed: float, remain: float
    ):
        if freezed > self.frozen:
            return

        if self._check_position(code):
            self.position[code].buy_done(price, volume)
            self.cash += remain
            self.frozen -= freezed

        else:
            gl.logger.critical(f"do not have {code}")
            self.position[code] = Position(code=code, price=price, volume=volume)
            self.cash += remain
            self.frozen -= freezed

    def buy_cancel(self, freezed: float):
        if freezed > self.frozen:
            return
        self.frozen -= freezed
        self.cash += freezed

    def sold(self, code: str, price: float, volume: int):
        if not self._check_position(code=code):
            return

        money = price * volume
        fee = cal_fee(DIRECTION_TYPES.SHORT, money, self.tax_rate)
        self.cash = self.cash + money - fee
        self.position[code].sold(price, volume)
        if self.position[code].volume == 0:
            self.position.pop(code, f"No key -> {code}")

    def sell_cancel(self, code: str, volume: int):
        if not self._check_position(code=code):
            return
        self.position[code].sell_cancel(volume)
