"""
仓位管理类
"""
from ginkgo.libs.meta_class import with_metaclass


class MetaPosition(object):
    """
    持仓元类
    """
    pass


class Position(with_metaclass(MetaPosition, object)):
    """
    持仓类
    """

    def __init__(self, code: str, price: float, amount: int):
        self.code = code
        self.price = price
        self.amount = amount

    def buy(self, price: float, amount: int):
        # 买入调整持仓
        # 一手为100股，买入的基础单位为手
        to_buy = amount - (amount % 100)
        self.price = (self.price * self.amount + price * to_buy) / (self.amount + to_buy)
        self.amount = self.amount + to_buy

    def sell(self, amount: int):
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        if amount >= self.amount:
            self.amount = 0
        else:
            self.amount = self.amount - amount
