"""
事件类
定义不同种类的事件
"""
from ginkgo_server.backtest.enums import EventType, DealType, InfoType


class Event(object):
    def __init__(self, date: str, code: str, source: str = ""):
        self.date = date if date else ""
        self.code = code if code else ""
        self.source = source


class MarketEvent(Event):
    """
    市场事件，分为新的价格事件，新的消息事件
    """

    def __init__(self, info_type: InfoType, data):
        # Event.__init__(date=date, code=code, source=source)
        self.type_ = EventType.Market
        self.info_type = info_type
        self.data = data


class SignalEvent(Event):
    """
    信号事件，给经纪人发出买入或者卖出信号
    """

    def __init__(
        self,
        date: str,  # 信号日期
        code: str,  # 股票代码
        current_price: float,  # 当前价格（目前是一天日交易数据的Close价格）
        deal: DealType = DealType.BUY,  # 交易类型
        source: str = "",
    ):
        Event.__init__(self, date=date, code=code, source=source)
        self.type_ = EventType.Signal
        self.current_price = current_price
        self.deal = deal


class OrderEvent(Event):
    """
    下单事件类，经纪人发出多空订单
    """

    def __init__(
        self,
        date: str,  # 信号日期
        deal: DealType,  # 交易类型
        code: str,  # 股票代码
        ready_capital: float = 0,  # 如果是多头，用来购买股票的资金
        target_volume: int = 0,  # 购买或卖出的量
        source: str = "",
    ):
        Event.__init__(self, date=date, code=code, source=source)
        self.type_ = EventType.Order
        self.deal = deal  # 'BUY' or 'SELL'
        self.ready_capital = ready_capital
        # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.target_volume = self.optimize_volume(target_volume=target_volume)

    def optimize_volume(self, target_volume):
        """
        调整买入数
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param target_volume: [准备下单的股票数量]
        :type target_volume: [int]
        """
        if self.deal == DealType.BUY:
            return int(target_volume / 100) * 100
        else:
            return target_volume


class FillEvent(Event):
    """
    交易事件
    根据标的资金，冻结可用资金，并尝试交易
    交易成功后通知经纪人交易成功，更新持仓股票与资金池
    交易失败后通知经纪人交易失败，并解除资金冻结
    """

    def __init__(
        self,
        deal: DealType,
        date: str,
        code: str,
        price: float = 0,
        volume: int = 0,
        source: str = "",
        fee: float = 0,
        remain: float = 0,
        done: bool = True,
    ):
        Event.__init__(self, date=date, code=code, source=source)
        self.type_ = EventType.Fill
        self.deal = deal  # 'BUY' or 'SELL'
        self.price = price  # 下单价格
        self.volume = volume  # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.fee = fee  # 此次交易的税费
        self.remain = remain  # 此次交易盈余
        self.done = done  # Ture为交易成功，False为交易失败
