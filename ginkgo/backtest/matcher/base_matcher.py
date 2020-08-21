"""
撮合类
先开发回测模拟撮合，回头接入实盘，接入券商API
"""
import pandas as pd
import abc
from ginkgo.backtest.event_engine import EventEngine
from ginkgo.backtest.event import SignalEvent


class BaseMatcher(metaclass=abc.ABCMeta):
    """
    撮合类
    """

    def __init__(self, stamp_tax: float = .001, fee: float = .0002, commission: float = .0003, min_commission=5):
        self._stamp_tax = stamp_tax  # 设置印花税，默认千1
        self._fee = fee  # 设置过户费,默认万.2
        self._commission = commission  # 交易佣金，按最高千3计算了，一般比这个低
        self._min_commission = min_commission  # 最低交易佣金，交易佣金的起步价

    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def get_result(self):
        # 获取交易结果
        raise NotImplementedError("Must implement get_result()")

    def try_match(self, event: SignalEvent):
        raise NotImplementedError("Must implement try_match()")
