"""
Author: Kaoru
Date: 2022-01-09 22:17:46
LastEditTime: 2022-04-18 16:01:40
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/matcher/base_matcher.py
What goes around comes around.
"""
"""
撮合基类
先开发回测模拟撮合，回头接入实盘，接入券商API
"""
import datetime
import queue
import abc
from typing import OrderedDict
from src.backtest.event_engine import EventEngine
from src.backtest.enums import Direction, OrderStatus, Source
from src.backtest.events import OrderEvent, FillEvent
from src.libs import GINKGOLOGGER as gl


class BaseMatcher(abc.ABC):
    """
    撮合基类

    买入时，会产生佣金、过户费两项费用，佣金为成交金额*佣金费率，单笔佣金不满最低佣金时，按最低佣金计算。
    卖出时，会产生佣金、过户费、印花税。印花税为成交金额*印花税费，
    """

    def __init__(
        self,
        name="撮合基类",
        stamp_tax_rate=0.001,
        transfer_fee_rate=0.0002,
        commission_rate=0.0003,
        min_commission=5,
        *args,
        **kwargs,
    ):
        self.name = name
        self.stamp_tax_rate = stamp_tax_rate  # 设置印花税，默认千1
        self.transfer_fee_rate = transfer_fee_rate  # 设置过户费,默认万2
        self.commission_rate = commission_rate  # 交易佣金，按最高千3计算了，一般比这个低
        self.min_commission = min_commission  # 最低交易佣金，交易佣金的起步价
        self.order_list = queue.Queue()  # 订单队列
        self.match_list = {}  # 撮合队列
        self.result_list = queue.Queue()  # 结果队列
        self.engine: EventEngine = None  # 用来推送事件
        self.order_count = 0  # 订单计数器
        self.datetime: datetime = None

    def gen_fillevent(
        self, order: OrderEvent, is_complete: bool, price: float = 0, volume: int = 0
    ):
        fill = FillEvent(
            code=order.code,
            direction=order.direction,
            price=0,
            volume=0,
            fee=0,
            source=Source.SIMMATCHER,
            datetime=self.datetime,
        )
        if is_complete:
            fill.price = price
            fill.volume = volume
            fill.fee = self.fee_cal(
                direction=order.direction, price=price, volume=volume
            )

        return fill

    def fee_cal(self, direction: Direction, price: float, volume: int):
        total = price * volume
        if total == 0:
            return 0
        stamp_tax = 0
        transfer = total * self.transfer_fee_rate
        commision = total * self.commission_rate
        if commision < self.min_commission:
            commision = self.min_commission
        if direction == direction.BEAR:
            stamp_tax = total * self.stamp_tax_rate
        return commision + stamp_tax + transfer

    def get_order(self, order: OrderEvent):
        """
        获取订单
        """
        if order.status == OrderStatus.CREATED:
            self.order_list.put(order)
            gl.logger.info(
                f"{self.name} 获取Order: {order.code} {order.direction} {order.order_type}"
            )
        else:
            gl.logger.error(f"{order.code} 状态异常，提交失败")
            order.status = OrderStatus.REJECTED
            if self.engine:
                self.engine.put(order)
            else:
                gl.logger.critical(f"{self.name} 引擎未注册")
        return self.order_list.qsize()

    def engine_register(self, engine: EventEngine):
        """
        引擎注册，通过Broker的注册获得引擎实例
        :param engine: [description]
        :type engine: EventEngine
        """
        self._engine = engine

    @abc.abstractmethod
    def try_match(self, order: OrderEvent):
        """
        尝试撮合成交

        回测Matcher直接成功
        实盘Matcher异步等待交易结果后再处理

        """
        raise NotImplementedError("Must implement try_match()")

    @abc.abstractmethod
    def send_order(self, order):
        """
        发送订单，模拟回测的话直接将订单存至队列

        实盘的话向券商发送订单
        """
        raise NotImplementedError("Must implement send_order()")

    @abc.abstractmethod
    def get_result(self):
        raise NotImplementedError("Must implement get_result()")
