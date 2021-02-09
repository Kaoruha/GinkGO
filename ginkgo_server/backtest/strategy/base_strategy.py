"""
策略类
"""
import pandas as pd
import abc
from ginkgo_server.backtest.event_engine import EventEngine
from ginkgo_server.backtest.postion import Position


class BaseStrategy(metaclass=abc.ABCMeta):
    """
    基础策略类
    回头改成抽象类
    """
    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine

    def data_transfer(self, data: pd.DataFrame, position: Position):
        # 数据传递至策略
        raise NotImplementedError("Must implement data_transfer()")

    def try_get_enter_signal(self):
        """买入信号的判断逻辑"""
        raise NotImplementedError("Must implement enter_market()")

    def try_get_exit_signal(self):
        """卖出信号的判断逻辑"""
        raise NotImplementedError("Must implement exit_market()")

    def try_get_signals(self):
        self.try_get_enter_signal()
        self.try_get_exit_signal()
