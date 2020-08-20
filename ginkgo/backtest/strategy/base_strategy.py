"""
策略类
"""
import pandas as pd
import abc
from ginkgo.backtest.event_engine import EventEngine


class BaseStrategy(metaclass=abc.ABCMeta):
    """
    基础策略类
    回头改成抽象类
    """
    def engine_register(self, engine:EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def data_transfer(self, data: pd.DataFrame):
        # 数据传递至策略
        raise NotImplementedError("Must implement data_transfer()")

    def enter_market(self):
        raise NotImplementedError("Must implement enter_market()")

    def exit_market(self):
        raise NotImplementedError("Must implement exit_market()")
