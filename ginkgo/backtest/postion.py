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

    def buy(self, price: float, volume: int):
        # 买入调整持仓
        # 一手为100股，买入的基础单位为手
        to_buy = volume - (volume % 100)
        self.price = (self.price * self.volume + price * to_buy) / (self.volume + to_buy)
        self.volume = self.volume + to_buy

    def sell(self, volume: int):
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        if volume >= self.volume:
            self.volume = 0
        else:
            self.volume = self.volume - volume
