"""
持仓类
"""


class Position(object):
    """
    持仓类
    """

    def __init__(self, code, price, volume, date):
        self.code = code
        self.price = price
        self.volume = volume  # 当前持有股票量
        self.freeze = 0  # 总冻结股票
        self.date = date  # 开仓日

    def __repr__(self):
        s = f"持仓 {self.code} 单价「{self.price}」 持有量「{self.volume}」 冻结「{self.freeze}」"
        return s

    def pre_buy(self, money: float, broker):
        """
        持仓买入预处理

        买入前冻结资金
        买入交易发起前调用
        """
        broker.freeze_money(money=money)

    def per_sell(self, volume: int):
        """
        持仓卖出的预处理

        卖出前冻结股票份额
        卖出交易发起前调用
        """

        # 如果预计卖出量大于现在持仓，则把预计卖出修正为现有持仓再清仓
        if volume >= self.volume:
            volume = self.volume

        self.freeze += volume
        self.volume -= volume

    def buy(self, price, volume):
        """
        买入成功后的操作

        :param price: 成交的价格
        :param volume: 成交量
        :param done: 买入是否成功

        """
        # 买入调整持仓
        # 买入的基础单位为手，一手为100股
        # 买入交易成功后调用
        self.price = (self.price * self.volume + price * volume) / (
            self.volume + volume
        )
        self.volume += volume

    def sell(self, volume, done):
        """
        卖出后的处理

        :param volume: 卖出的股票数
        :param done: 卖出是否成功
        """
        # 卖出调整持仓
        # 如果卖出的数量大于持仓直接清空
        # 卖出交易成功后调用
        if done:
            if volume > self.freeze:
                print("成功卖出的股票大于冻结的股票，请检查策略")
                self.freeze = 0
            else:
                self.freeze -= volume
        else:
            self.volume += volume
            self.freeze -= volume
