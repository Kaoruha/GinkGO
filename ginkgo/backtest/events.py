"""
事件类
定义不同种类的事件
"""
import abc
import datetime
import uuid

from ginkgo.backtest.enums import (
    EventType,
    Direction,
    OrderStatus,
    OrderType,
    Source,
    MarketEventType,
)
from ginkgo.libs import GINKGOLOGGER as gl


class Event(abc.ABC):
    @property
    def datetime(self):
        return self._datetime

    @datetime.setter
    def datetime(self, value):
        if isinstance(value, datetime.datetime):
            self._datetime = value
        elif isinstance(value, str):
            self._datetime = datetime.datetime.strptime(value, "%Y-%m-%d")
        else:
            self._datetime = datetime.datetime.strptime("9999-01-01", "%Y-%m-%d")

    def __init__(
        self,
        event_type: EventType,
        datetime: str,
        code: str,
        source: Source,
        *args,
        **kwargs,
    ):
        self.event_type: EventType = event_type
        self.datetime = datetime
        self.code: str = code
        self.source: Source = source
        self.uuid = str(uuid.uuid4()).replace("-", "")


class MarketEvent(Event):
    """
    市场事件，分为新的价格事件，新的消息事件
    """

    def __init__(
        self,
        code: str,  #  相关标的
        raw,  # 具体数据
        markert_event_type: MarketEventType,
        source: Source = Source.TEST,  # 来源
        datetime: str = None,  # 时间 "2020-01-01 00:00:00"
        *args,
        **kwargs,
    ):
        super(MarketEvent, self).__init__(
            event_type=EventType.MARKET,
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
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
        code: str,  # 股票代码
        direction: Direction,  # 交易方向
        datetime: str = None,  # 信号发生时间
        source: Source = Source.TEST,  # 来源
        last_price: float = 0,  # 最新价格
        *args,
        **kwargs,
    ):
        super(SignalEvent, self).__init__(
            event_type=EventType.SIGNAL,
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.direction = direction
        self.last_price = last_price

    def __repr__(self):
        d = "多" if self.direction == Direction.BULL else "空"
        s = f"{self.datetime} 产生 {self.code} 「{d}头」交易信号，信号来源为「{self.source}」"
        return s


class OrderEvent(Event):
    """
    下单事件类，经纪人发出多空订单
    """

    def __init__(
        self,
        code: str,  # 股票代码
        direction: Direction,  # 交易类型
        order_type: OrderType = OrderType.LIMIT,
        price: float = 0,
        volume: int = 0,  # 购买或卖出的量
        source: Source = Source.TEST,
        datetime: str = None,  # 信号日期
        status: OrderType = OrderStatus.CREATED,
        frozen_money: float = 0,
        *args,
        **kwargs,
    ):
        super(OrderEvent, self).__init__(
            event_type=EventType.ORDER,
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.order_type: OrderType = order_type
        self.status: OrderStatus = status
        self.direction: Direction = direction  # 'BUY' or 'SELL'
        # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.volume: int = self.__optimize_volume(volume=volume)
        self.price: float = price
        self.traded: int = 0

    def __repr__(self):
        s = f"{self.datetime} {self.code}「{self.direction.value}」下单事件，份额「{self.volume}」，状态「{self.status.value}」，事件来源为「{self.source.value}」"
        return s

    def __optimize_volume(self, volume: int):
        """
        调整买入数
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param volume: [准备下单的股票数量]
        :type volume: [int]
        """
        if self.direction == Direction.BULL:
            r = int(volume / 100) * 100
            if r != volume:
                gl.logger.warning(f"已调整买入量「{volume}」->「{r}」")
            return r
        else:
            return volume


class FillEvent(Event):
    """
    成交事件
    """

    def __init__(
        self,
        code: str,  # 股票代码
        direction: Direction,
        price: float,
        volume: int,
        fee: float,
        money_remain: float = 0,  # TODO Update UnitTest and sim matcher
        source: Source = Source.TEST,
        datetime: str = None,  # 信号日期
        *args,
        **kwargs,
    ):
        super(FillEvent, self).__init__(
            event_type=EventType.FILL,
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.direction: Direction = direction  # 'BULL' or 'BEAR'
        self.price: float = price  # 下单价格
        self.volume: int = volume
        self.fee = fee  # 此次交易的税费
        self.money_remain = money_remain  # 交易剩余的金额

    def __repr__(self):
        s = f"{self.datetime} {self.code} "
        s += "「"
        s += "购买" if self.direction == Direction.BULL else "卖出"
        s += "」"
        s += f" 事件来源为「{self.source.value}」, "
        s += f"价格「{round(self.price, 2)}」, "
        s += f"成交量「{round(self.volume, 2)}」, "
        s += f"税费「{round(self.fee, 2)}」"
        return s
