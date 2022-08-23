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
        return self.__datetime

    @datetime.setter
    def datetime(self, value):
        if isinstance(value, datetime.datetime):
            self.__datetime = value
        elif isinstance(value, str):
            self.__datetime = datetime.datetime.strptime(value, "%Y-%m-%d")
        else:
            self.__datetime = datetime.datetime.strptime("9999-01-01", "%Y-%m-%d")

    @property
    def uuid(self):
        return self.__uuid

    @property
    def code(self):
        return self.__code

    @property
    def type(self):
        return self.__type

    def __init__(
        self,
        datetime: str,
        code: str,
        source: Source,
        *args,
        **kwargs,
    ):
        self.__type = EventType.BASE
        self.__code = code
        self.__uuid = str(uuid.uuid4()).replace("-", "")
        self.datetime = datetime
        self.source = source


class MarketEvent(Event):
    """
    市场事件，分为新的价格事件，新的消息事件
    """

    def __init__(
        self,
        code: str,  #  相关标的
        raw,  # 具体数据
        market_event_type: MarketEventType,
        source: Source = Source.TEST,  # 来源
        datetime: str = None,  # 时间 "2020-01-01 00:00:00"
        *args,
        **kwargs,
    ):
        super(MarketEvent, self).__init__(
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.__type = EventType.MARKET
        self.__market_event_type = market_event_type
        self.raw = raw

    @property
    def market_event_type(self):
        return self.__market_event_type

    def __repr__(self):
        return f"{self.datetime} {self.raw}"


class SignalEvent(Event):
    """
    信号事件
    """

    def __init__(
        self,
        datetime: str = None,  # 信号发生时间
        code: str = "testcode",  # 股票代码
        direction: Direction = Direction.NET,  # 交易方向
        source: Source = Source.TEST,  # 来源
        latest_price: float = 0,  # 最新价格
        *args,
        **kwargs,
    ):
        super(SignalEvent, self).__init__(
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.__type = EventType.SIGNAL
        self.__direction = direction
        self.__latest_price = latest_price

    @property
    def direction(self):
        return self.__direction

    @property
    def latest_price(self):
        return self.__latest_price

    def __repr__(self):
        d = "多" if self.direction == Direction.LONG else "空"
        s = f"{self.datetime} 产生 {self.code} 「{d}头」交易信号，信号来源为「{self.source}」"
        return s


class OrderEvent(Event):
    """
    下单事件类，经纪人发出多空订单
    """

    def __init__(
        self,
        datetime: str = None,  # 信号日期
        code: str = "testcode",  # 股票代码
        direction: Direction = Direction.NET,  # 交易类型
        order_type: OrderType = OrderType.MARKET,
        price: float = 0,
        quantity: int = 0,  # 购买或卖出的量
        frozen_money: float = 0,
        source: Source = Source.TEST,
        status: OrderType = OrderStatus.CREATED,
        *args,
        **kwargs,
    ):
        super(OrderEvent, self).__init__(
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.__type = EventType.ORDER
        self.__order_type = order_type
        self.__direction: Direction = direction  # 'LONG' or 'SHORT'
        # 下单数(单位是手，买入只能整百，卖出可以零散)
        self.__quantity = self.__optimize_quantity(quantity=quantity)
        self.price = price
        self.traded = 0
        self.status = status

    @property
    def order_type(self):
        return self.__order_type

    @property
    def direction(self):
        return self.__direction

    @property
    def quantity(self):
        return self.__quantity

    def __repr__(self):
        s = f"{self.datetime} {self.code}「{self.direction.value}」下单事件，份额「{self.volume}」，状态「{self.status.value}」，事件来源为「{self.source.value}」"
        return s

    def __optimize_quantity(self, quantity: int):
        """
        调整买入数
        股票买入以手为单位，一手为一百股，volume只能是整百的倍数
        卖出不作限制

        :param volume: [准备下单的股票数量]
        :type volume: [int]
        """
        if self.direction == Direction.LONG:
            r = int(quantity / 100) * 100
            if r != quantity:
                gl.logger.warning(f"已调整买入量「{volume}」->「{r}」")
            return r
        elif self.direction == Direction.SHORT:
            return quantity


class FillEvent(Event):
    """
    成交事件
    """

    # describe the cost of purchase or sale as well as the transaction costs, such as fees or slippage

    def __init__(
        self,
        datetime: str = None,  # when the order was filled
        code: str = "testcode",  # 股票代码
        order: OrderEvent = None,
        direction: Direction = Direction.NET,
        price: float = 0,
        quantity: int = 0,
        commision: float = 0,
        money_remain: float = 0,  # TODO Update UnitTest and sim matcher
        source: Source = Source.TEST,
        *args,
        **kwargs,
    ):
        super(FillEvent, self).__init__(
            datetime=datetime,
            code=code,
            source=source,
            args=args,
            kwargs=kwargs,
        )
        self.__type = EventType.FILL
        self.__direction = direction  # 'LONG' or 'SHORT'
        self.__price = price  # Fill Price
        self.__quantity = quantity  # Fill Volume
        self.__commision = commision  # 此次交易的税费
        self.__money_remain = money_remain  # 交易剩余的金额

    @property
    def direction(self):
        return self.__direction

    @property
    def price(self):
        return self.__price

    @property
    def quantity(self):
        return self.__quantity

    @property
    def commision(self):
        return self.__commision

    @property
    def money_remain(self):
        return self.__money_remain

    def __repr__(self):
        s = f"{self.datetime} {self.code} "
        s += "「"
        s += "购买" if self.direction == Direction.BULL else "卖出"
        s += "」"
        s += f" 事件来源为「{self.source.value}」, "
        s += f"价格「{round(self.price, 2)}」, "
        s += f"成交量「{round(self.quantity, 2)}」, "
        s += f"税费「{round(self.commision, 2)}」"
        return s
