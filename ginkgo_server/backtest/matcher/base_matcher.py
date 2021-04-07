"""
撮合基类
先开发回测模拟撮合，回头接入实盘，接入券商API
"""
import pandas as pd
import abc
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.events import OrderEvent


class BaseMatcher(metaclass=abc.ABCMeta):
    """
    撮合基类
    """

    def __init__(
        self,
        stamp_tax_rate=0.001,
        fee_rate=0.0002,
        commission_rate=0.0003,
        min_commission=5,
    ):
        self._stamp_tax_rate = stamp_tax_rate  # 设置印花税，默认千1
        self._fee_rate = fee_rate  # 设置过户费,默认万2
        self._commission_rate = commission_rate  # 交易佣金，按最高千3计算了，一般比这个低
        self._min_commission = min_commission  # 最低交易佣金，交易佣金的起步价
        self.target_volume = 0  # 准备买入or卖出的股票量 TODO 要删掉
        self._match_list = []
        self._engine = None  # 用来推送事件

    def engine_register(self, engine: EventEngine):
        """
        引擎注册，通过Broker的注册获得引擎实例

        :param engine: [description]
        :type engine: EventEngine
        """
        self._engine = engine

    def get_result(self):
        """
        获取交易结果

        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement get_result()")

    def try_match(self, event: OrderEvent):
        """
        尝试撮合成交

        回测Matcher直接成功
        实盘Matcher异步等待交易结果后再处理

        :param event: [description]
        :type event: SignalEvent
        :raises NotImplementedError: [description]
        """
        raise NotImplementedError("Must implement try_match()")
