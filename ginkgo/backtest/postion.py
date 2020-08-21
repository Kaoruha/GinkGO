"""
仓位管理类
"""


class Position(object):
    """
    持仓类
    """

    def __init__(self, code: str, price: float, volumn: int):
        self.code = code
        self.price = price
        self.volumn = volumn

    def buy(self, price: float, volumn: int):
        # 买入调整持仓
        # 一手为100股，买入的基础单位为手
        to_buy = volumn - (volumn % 100)
        self.price = (self.price * self.volumn + price * to_buy) / (self.volumn + to_buy)
        self.volumn = self.volumn + to_buy

    def sell(self, volumn: int):
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        if volumn >= self.volumn:
            self.volumn = 0
        else:
            self.volumn = self.volumn - volumn
