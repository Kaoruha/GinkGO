"""
仓位管理类
"""
import datetime
import abc
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.backtest.event_engine import EventEngine


class BaseSizer(metaclass=abc.ABCMeta):
    """
    仓位管理基类

    """

    def __init__(self, name):
        self._engine = None
        self.__name = name

    @property
    def name(self):
        return self.__name

    def __repr__(self):
        engine_status = "未挂载引擎" if self._engine is None else f"已挂载引擎 {self._engine}"
        return f"仓位管理基类，{engine_status}"

    def engine_register(self, engine: EventEngine):
        """
        引擎注册，通过Broker的注册获得引擎实例

        :param engine: [description]
        :type engine: EventEngine
        """
        self._engine = engine

    def get_signal(self, event, broker):
        """
        获取信号事件
        根据初始金额、手持现金、当前持仓进行仓位调整，产生订单事件OrderEvent
        :param event: 某只股票的多空信号
        :param broker: 当前经纪人
        """
        raise NotImplementedError("Must implement get_signal()")
