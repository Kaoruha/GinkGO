from ginkgo.backtest.order import Order
from ginkgo.enums import SOURCE_TYPES


class BasePortfolio(object):
    def init(self, *args, **kwargs):
        self.cash: float = 100000
        self.freeze: float = 0
        self.position: dict = {}

    def check_position(self, code: str) -> bool:
        if code in self.position.keys():
            return True
        else:
            return False

    def pre_buy(self, code: str, volume: int):
        o = Order()
        pass

    def pre_sell(self, code: str, volume: int):
        pass

    def buy_done(self, code: str, order_id: str):
        pass

    def buy_cancel(self, code: str, order_id: str):
        pass

    def sell_done(self, code: str, order_id: str):
        pass

    def sell_cancel(self, code: str, order_id: str):
        pass
