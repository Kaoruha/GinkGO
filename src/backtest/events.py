"""
事件类
定义不同种类的事件
"""
from src.backtest.enums import EventType, DealType, InfoType


class Event(object):
    def __init__(self, event_type, date="", code="", source=""):
        self.type_ = event_type
        self.date = date
        self.code = code
        self.source = source


class MarketEvent(Event):
    """
    市场事件，分为新的价格事件，新的消息事件
    """

    def __init__(self, date, code, source, info_type, data, time="0000"):
        super(MarketEvent, self).__init__(
            event_type=EventType.Market, date=date, code=code, source=source
        )
        self.info_type = info_type
        self.data = data
        self.time = time

    def __repr__(self):
        t = ""
        if self.info_type == InfoType.DailyPrice:
            t = "日线价格信息"
        elif self.info_type == InfoType.MinutePrice:
            t = "分钟价格信息"
        elif self.info_type == InfoType.Message:
            t = "市场信息"
        else:
            t = "未知市场事件"
        s = f"{self.date} {t}"
        return s


class SignalEvent(Event):
    """
    信号事件，给经纪人发出买入或者卖出信号
    """

    def __init__(
        self,
        date,  # 信号日期
        code,  # 股票代码
        deal=DealType.BUY,  # 交易类型
        source="",
    ):
        super(SignalEvent, self).__init__(
            event_type=EventType.Signal, date=date, code=code, source=source
        )
        self.type_ = EventType.Signal
        self.deal = deal

        print(self)

    def __repr__(self):
        d = "多" if self.deal == DealType.BUY else "空"
        s = f"{self.date} 产生 {self.code} 「{d}头」交易信号，信号来源为「{self.source}」"
        return s


class OrderEvent(Event):
    """
    下单事件类，经纪人发出多空订单
    """

    def __init__(
        self,
        date,  # 信号日期
        code,  # 股票代码
        deal=DealType.BUY,  # 交易类型
        status=1,
        volume=0,  # 购买或卖出的量
        source="",
        price_limit=0,
    ):
        # TODO 添加限价、市场价成交方式
        super(OrderEvent, self).__init__(
            event_type=EventType.Order, date=date, code=code, source=source
        )
        self.deal = deal  # 'BUY' or 'SELL'
        # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.volume = self.optimize_volume(volume=volume)
        self.freeze = 0
        self.price_limit = price_limit
        print(self)

    def __repr__(self):
        d = "多" if self.deal == DealType.BUY else "空"
        s = f"{self.date} 产生 {self.code} 「{d}头」下单事件，份额「{self.volume}」，事件来源为「{self.source}」"
        return s

    def optimize_volume(self, volume):
        """
        调整买入数
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param volume: [准备下单的股票数量]
        :type volume: [int]
        """
        if self.deal == DealType.BUY:
            return int(volume / 100) * 100
        else:
            return volume

    def adjust_volume(self, volume):
        target = self.volume + volume
        self.volume = self.optimize_volume(target)

    def freeze_money(self, money):
        self.freeze = money


class FillEvent(Event):
    """
    交易事件
    根据标的资金，冻结可用资金，并尝试交易
    交易成功后通知经纪人交易成功，更新持仓股票与资金池
    交易失败后通知经纪人交易失败，并解除资金冻结
    """

    def __init__(
        self,
        deal,
        date,
        code,
        price,
        volume,
        source,
        fee,
        remain,
        freeze,
        done,
    ):
        super(FillEvent, self).__init__(
            event_type=EventType.Fill, date=date, code=code, source=source
        )
        self.deal = deal  # 'BUY' or 'SELL'
        self.price = price  # 下单价格
        self.volume = volume  # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.fee = fee  # 此次交易的税费
        self.remain = remain  # 此次交易盈余
        self.freeze = freeze  # 之前冻结的金额或者标的量
        self.done = done  # Ture为交易成功，False为交易失败
        print(self)

    def __repr__(self):
        s = f"{self.date} {self.code} "
        s += "「"
        s += "购买" if self.deal == DealType.BUY else "卖出"
        s += "成功" if self.done else "失败"
        s += "」"
        s += f" 事件来源为「{self.source}」, "
        s += f"价格「{round(self.price, 2)}」, "
        s += f"成交量「{round(self.volume, 2)}」, "
        s += f"盈余现金「{round(self.remain, 2)}」, "
        s += f"税费「{round(self.fee, 2)}」"
        return s
