"""
事件类
定义不同种类的事件
"""

from ginkgo.libs.enums import EventType
import pandas as pd


class MarketEvent(object):
    def __init__(self):
        self.type_ = EventType.Market
        # TODO 市场信息


class SignalEvent(object):
    def __init__(self, date, code, buy_or_sell='BUY'):
        self.date = date
        self.code = code
        self.type_ = EventType.Signal
        if buy_or_sell == 'BUY' or buy_or_sell == 'SELL':
            self.buy_or_sell = buy_or_sell
        else:
            print('buy_or_sell can only be BUY or SELL')


class OrderEvent(object):
    """
    下单事件类
    """

    def __init__(self, buy_or_sell='BUY', code='sh.600000', price=0, volume=0):
        self.type_ = EventType.Order
        self.buy_or_sell = buy_or_sell  # 'BUY' or 'SELL'
        self.code = code  # 股票代码 默认为sh.600000 浦发银行
        self.price = price  # 下单价格
        self.volume = volume  # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.optimize_volume(volume=volume)

    def optimize_volume(self, volume):
        """
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param volume: [准备下单的股票数量]
        :type volume: [int]
        """
        if self.buy_or_sell == 'BUY':
            self.volume = int(volume / 100) * 100


class DailyEvent(object):
    def __init__(self, data: pd.DataFrame):
        self.type_ = EventType.DailyPrice
        self.data = data
