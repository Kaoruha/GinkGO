"""
事件类
定义不同种类的事件
"""
import pandas as pd
from ginkgo.backtest.enums import EventType, DealType, InfoType


class MarketEvent(object):
    """
    市场事件，分为新的价格事件，新的消息事件
    """

    def __init__(self, info_type: InfoType, data):
        self.type_ = EventType.Market
        self.info_type = info_type
        self.data = data


class SignalEvent(object):
    """
    信号事件，给经纪人发出买入或者卖出信号
    """

    def __init__(self, date, code, deal: DealType = DealType.BUY):
        self.date = date
        self.code = code
        self.type_ = EventType.Signal
        self.deal = deal


class OrderEvent(object):
    """
    下单事件类，经纪人发出多空订单
    """

    def __init__(self, date: str, deal='BUY', code='sh.600000', volume=0, capital=0):
        self.date = date
        self.type_ = EventType.Order
        self.deal = deal  # 'BUY' or 'SELL'
        self.code = code  # 股票代码 默认为sh.600000 浦发银行
        self.capital = capital
        self.volume = self.optimize_volume(volume=volume)  # 下单数(单位是手，买入只能整百，卖出可以零散)

    def optimize_volume(self, volume):
        """
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param volume: [准备下单的股票数量]
        :type volume: [int]
        """
        if self.deal == DealType.BUY:
            return int(volume / 100) * 100
        else:
            return volume


class FillEvent(object):
    """
    交易事件，交易成功后通知经纪人交易成功，更新持仓股票与资金池
    交易失败后通知经纪人交易失败，解除资金冻结
    """

    def __init__(self, deal: DealType, code: str, price=0, volume=0, fee=0, remain=0, done: bool = True):
        self.type_ = EventType.Fill
        self.deal = deal  # 'BUY' or 'SELL'
        self.code = code  # 股票代码 默认为sh.600000 浦发银行
        self.price = price  # 下单价格
        self.volume = volume  # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.fee = fee  # 此次交易的税费
        self.remain = remain  # 此次交易盈余

        self.done = done
