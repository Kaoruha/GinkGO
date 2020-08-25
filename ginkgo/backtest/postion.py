"""
仓位管理类
"""


class Position(object):
    """
    持仓类
    """
    def __init__(self, code: str, price: float, volume: int):
        self.code = code
        self.price = price
        self.volume = volume
        self.freeze = 0

    def buy(self, price: float, volume: int):
        # 买入调整持仓
        # 买入的基础单位为手，一手为100股
        to_buy = volume - (volume % 100)
        self.price = (self.price * self.volume +
                      price * to_buy) / (self.volume + to_buy)
        self.volume = self.volume + to_buy

    def sell(self, volume: int):
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        if volume >= self.freeze:
            self.freeze = 0
        else:
            self.freeze -= volume

    def ready_to_sell(self, volume: int):
        # 卖出前冻结
        if volume >= self.volume:
            volume = self.volume
        self.freeze += volume
        self.volume -= volume
