"""
基础策略
设定交易手续费等

生存第一
生存第一
生存第一
生存第一


"""
import pandas as pd


class BaseStrategy(object):
    broker = None
    data = None  # 数据

    def __init__(self, data: pd.DataFrame):
        super(BaseStrategy, self).__init__()
        self.data = data

    def on_start(self):
        """
        策略开始运行
        """
        pass

    def on_stop(self):
        """
        策略运行结束
        """
        pass

    def buy(self, price, volume):
        """
        期货中做多，或者现货买入
        :param price: 价格
        :type price: float
        :param volume: 交易数量
        :type volume: int
        """
        self.broker.buy(price, volume)

    def sell(self, price, volume):
        """
        期货中平多，或者现货卖出
        :param price: 价格
        :type price: float
        :param volume: 交易数量
        :type volume: int
        """
        self.broker.sell(price, volume)

    def short(self, price, volume):
        """
        期货做空
        :param price: 价格
        :type price: float
        :param volume: 交易数量
        :type volume: int
        """
        self.broker.short(price, volume)

    def cover(self, price, volume):
        """
        做空平仓
        :param price: 价格
        :type price: float
        :param volume: 交易数量
        :type volume: int
        """
        self.broker.cover(price, volume)
