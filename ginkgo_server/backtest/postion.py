"""
持仓类
"""


class Position(object):
    """
    持仓类
    """

    def __init__(self, code: str, buy_price: float, volume: int):
        self.code = code
        self.buy_price = buy_price
        self.volume = volume  # 当前持有股票量
        self.freeze = 0  # 总冻结股票
        self.current_price = buy_price
        # print(f'建仓 {self.code} 价格:{self.buy_price} 持有量:{self.volume}')

    def buy(self, price: float, volume: int):
        """
        买入成功后的操作

        :param price: 成交的价格
        :type price: float
        :param volume: 成交量
        :type volume: int
        """
        # 买入调整持仓
        # 买入的基础单位为手，一手为100股
        # 买入交易成功后调用
        if volume % 100 != 0:
            print("买入量异常，请检查策略")
            return
        self.buy_price = (self.buy_price * self.volume + price * volume) / (
            self.volume + volume
        )
        self.volume = self.volume + volume
        self.test_shout('买入')

    def sell(self, volume: int):
        """
        卖出成功后的处理

        :param volume: 卖出的股票数
        :type volume: int
        """
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        # 卖出交易成功后调用
        if volume > self.freeze:
            self.freeze = 0
            print("成功卖出的股票大于冻结的股票，请检查策略")
        else:
            self.freeze -= volume
        self.test_shout('卖出  ')

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
        self.test_shout('预卖出')

    def ready_to_buy(self):
        """
        持仓买入预处理

        买入前冻结资金
        买入交易发起前调用
        """
        pass

    def update_price(self, current_price: float):
        self.current_price = current_price

    def test_shout(self, char: str):
        pass
        # print(f'{char}  Code:{self.code} BP:{self.buy_price} VL:{self.volume} FREEZE:{self.freeze} NP:{self.current_price}')