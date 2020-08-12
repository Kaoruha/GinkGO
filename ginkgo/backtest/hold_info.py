"""
持仓信息类
"""

class HoldInfo(object):
    # 'code': ['price', 'amount']
    def __init__(self, code, price, amount):
        # TODO 判断code是否在stock_code内
        self.code = code
        self.price = price
        self.amount = amount
            