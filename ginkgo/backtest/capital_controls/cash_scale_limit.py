"""
头寸单位规模限制法则
"""
from ginkgo.backtest.capital_controls.base_capital import BaseCapitial


class CashScaleLimit(BaseCapitial):
    def __init__(self, stock_limit: float):
        """
        初始化函数
        :param stock_limit:头寸单位规模限制，输入为0~1，0.1代表规模为资金池10%
        """
        if stock_limit>0 and stock_limit <1:
            self.stock_limit = stock_limit
        else:
            print('头寸规模应该在0~1之间')
            self.stock_limit = .3

    def check(self):
        pass
