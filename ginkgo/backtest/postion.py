"""
持仓类
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
        # 买入交易成功后调用
        to_buy = volume - (volume % 100)
        self.price = (self.price * self.volume +
                      price * to_buy) / (self.volume + to_buy)
        self.volume = self.volume + to_buy

    def sell(self, target_volume: int):
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        # 卖出交易成功后调用
        if target_volume > self.freeze:
            self.freeze = 0
            print("预计卖出股票大于持仓  请检查策略")
        else:
            self.freeze -= target_volume

    def ready_to_sell(self, target_volume: int):
        """
        持仓卖出的预处理

        卖出前冻结股票份额
        卖出交易发起前调用
        """      

        # 如果预计卖出量大于现在持仓，则把预计卖出修正为现有持仓再清仓
        if target_volume >= self.volume:
            target_volume = self.volume

        self.freeze += target_volume
        self.volume -= target_volume

    def ready_to_buy(self):
        """
        持仓买入预处理

        买入前冻结资金
        买入交易发起前调用
        """
        pass