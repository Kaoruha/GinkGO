"""
事件类
定义不同种类的事件
"""
import abc
import datetime

from src.backtest.enums import (
    EventType,
    Direction,
    OrderStatus,
    OrderType,
    Source,
    MarketEventType,
)
from src.libs.ginkgo_logger import ginkgo_logger as gl


class Event(abc.ABC):
    @property
    def datetime(self):
        return self._datetime

    @datetime.setter
    def datetime(self, value):
        if isinstance(value, datetime.datetime):
            self._datetime = value
        elif isinstance(value, str):
            self._datetime = datetime.datetime.strptime(datetime, "%Y-%m-%d")
        else:
            self._datetime = datetime.datetime.strptime("9999-01-01", "%Y-%m-%d")

    def __init__(self, event_type: EventType, datetime: str, code: str, source: Source):
        self.event_type: EventType = event_type
        self.datetime = datetime
        self.code: str = code
        self.source: Source = source
        # TODO 加上id


class MarketEvent(Event):
    """
    市场事件，分为新的价格事件，新的消息事件
    """

    def __init__(
        self,
        datetime: str,  # 时间 "2020-01-01 00:00:00"
        code: str,  #  相关标的
        source: Source,  # 来源
        raw,  # 具体数据
        markert_event_type: MarketEventType,
    ):
        super(MarketEvent, self).__init__(
            event_type=EventType.MARKET, datetime=datetime, code=code, source=source
        )
        self.market_event_type = markert_event_type
        self.raw = raw

    def __repr__(self):
        return f"{self.datetime} {self.raw}"


class SignalEvent(Event):
    """
    信号事件
    """

    def __init__(
        self,
        datetime: str,  # 信号发生时间
        code: str,  # 股票代码
        direction: Direction,  # 交易方向
        source: Source,
    ):
        super(SignalEvent, self).__init__(
            event_type=EventType.SIGNAL, datetime=datetime, code=code, source=source
        )
        self.direction = direction

    def __repr__(self):
        d = "多" if self.deal == Direction.BUY else "空"
        s = f"{self.date} 产生 {self.code} 「{d}头」交易信号，信号来源为「{self.source}」"
        return s


class OrderEvent(Event):
    """
    下单事件类，经纪人发出多空订单
    """

    def __init__(
        self,
        datetime: str,  # 信号日期
        code: str,  # 股票代码
        direction: Direction,  # 交易类型
        source: Source,
        status: OrderType = OrderStatus.CREATED,
        volume: int = 0,  # 购买或卖出的量
        price: float = 0,
        order_type: OrderType = OrderType.LIMIT,
    ):
        super(OrderEvent, self).__init__(
            event_type=EventType.Order, datetime=datetime, code=code, source=source
        )
        self.order_type: OrderType = order_type
        self.status: OrderStatus = status
        self.direction: Direction = direction  # 'BUY' or 'SELL'
        # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.volume: int = self.optimize_volume(volume=volume)
        self.price: float = price
        self.traded: int = 0

    def __repr__(self):
        d = "多" if self.deal == Direction.BUY else "空"
        s = f"{self.date} 产生 {self.code} 「{d}头」下单事件，份额「{self.volume}」，事件来源为「{self.source}」"
        return s

    def optimize_volume(self, volume: int):
        """
        调整买入数
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param volume: [准备下单的股票数量]
        :type volume: [int]
        """
        if self.direction == Direction.LONG:
            r = int(volume / 100) * 100
            if r != volume:
                gl.warning(f"已调整买入量「{volume}」->「{r}」")
            return r
        else:
            return volume


class FillEvent(Event):
    """
    成交事件
    """

    def __init__(
        self,
        datetime: str,  # 信号日期
        code: str,  # 股票代码
        direction: Direction,
        price: float,
        volume: int,
        source: Source,
        fee: float,
    ):
        super(FillEvent, self).__init__(
            event_type=EventType.Fill, datetime=datetime, code=code, source=source
        )
        self.direction: Direction = direction  # 'LONG' or 'SHORT'
        self.price: float = price  # 下单价格
        self.volume: int = volume
        self.fee = fee  # 此次交易的税费

    def __repr__(self):
        s = f"{self.datetime} {self.code} "
        s += "「"
        s += "购买" if self.deal == Direction.LONG else "卖出"
        s += "」"
        s += f" 事件来源为「{self.source}」, "
        s += f"价格「{round(self.price, 2)}」, "
        s += f"成交量「{round(self.volume, 2)}」, "
        s += f"税费「{round(self.fee, 2)}」"
        return s
