"""
交易信息类
"""
from ginkgo.libs.meta_class import with_metaclass


class MetaTrade(object):
    """
    持仓元类
    """
    pass


class Trade(with_metaclass(MetaTrade, object)):
    """
    交易记录类
    """

    def __init__(self, code: str, date: str, price: float, volumn: int):
        self.code = code
        self.date = date
        self.price = price
        self.volumn = volumn
