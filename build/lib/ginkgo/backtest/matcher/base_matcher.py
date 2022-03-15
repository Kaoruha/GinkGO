"""
撮合基类
先开发回测模拟撮合，回头接入实盘，接入券商API
"""
import pandas as pd
import abc
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.events import OrderEvent, DealType


class BaseMatcher(metaclass=abc.ABCMeta):
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
    ):
        self._name = name
        self._stamp_tax_rate = stamp_tax_rate  # 设置印花税，默认千1
        self._transfer_fee_rate = transfer_fee_rate  # 设置过户费,默认万2
        self._commission_rate = commission_rate  # 交易佣金，按最高千3计算了，一般比这个低
        self._min_commission = min_commission  # 最低交易佣金，交易佣金的起步价
        self._match_list = []
        # self._engine = None  # 用来推送事件

    # def engine_register(self, engine: EventEngine):
    # """
    # 引擎注册，通过Broker的注册获得引擎实例
    # :param engine: [description]
    # :type engine: EventEngine
    # """
    # self._engine = engine

    def get_result(self):
        """
        获取交易结果

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement get_result()")

    def try_match(self, order):
        """
        尝试撮合成交

        回测Matcher直接成功
        实盘Matcher异步等待交易结果后再处理

        :param event: [description]
        :type event: SignalEvent
        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement try_match()")

    def send_order(self, order):
        """
        发送订单，模拟回测的话直接将订单存至队列

        实盘的话向券商发送订单
        """
        raise NotImplementedError("Must implement send_order()")

    def get_result(self):
        raise NotImplementedError("Must implement get_result()")

    def fee_cal(self, bussiness_volume, deal_type):
        fee = 0
        commision = bussiness_volume * self._commission_rate
        commision = (
            commision if commision > self._min_commission else self._min_commission
        )
        transfer = bussiness_volume * self._transfer_fee_rate
        fee = commision + transfer
        if deal_type == DealType.SELL:
            stamp = bussiness_volume * self._stamp_tax_rate
            fee = fee + stamp

        return fee

    def clear_match_list(self):
        self._match_list = []
