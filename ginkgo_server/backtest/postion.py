"""
持仓类
"""
from ginkgo_server.backtest.broker.base_broker import BaseBroker


class Position(object):
    """
    持仓类
    """

    def __init__(self, code: str, buy_price: float, volume: int):
        self.code = code
        self.price = buy_price
        self.volume = volume  # 当前持有股票量
        self.freeze = 0  # 总冻结股票

    def ready_to_buy(self, money: float, broker: BaseBroker):
        """
        持仓买入预处理

        买入前冻结资金
        买入交易发起前调用
        """
        if money < broker._capital:
            broker._capital -= money
            broker._freeze += money

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

    def buy_done(self, price: float, volume: int):
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
        self.price = (self.price * self.volume + price * volume) / (
            self.volume + volume
        )
        self.volume += volume

    def sell_done(self, volume: int):
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

    def update_price(self, current_price: float):
        self.current_price = current_price
