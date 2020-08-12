"""
基础的资金管理策略
"""


class BaseCapitial(object):
    def __init__(self, stock_limit: int):
        if stock_limit > 0:
            self.stock_limit = stock_limit
