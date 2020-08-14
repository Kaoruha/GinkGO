"""
持仓信息类
"""
from ginkgo.data.data_portal import data_portal


class HoldInfo(object):
    # 'code': ['price', 'amount']
    def __init__(self, code, price, amount):
        # TODO 判断code是否在stock_code内
        self.code = code if data_portal.check_code_exist(code=code) else 'sh.600000'
        self.price = price
        self.amount = amount
