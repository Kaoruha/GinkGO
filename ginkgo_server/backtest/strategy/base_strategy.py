"""
策略类

好的策略应该：
1、相当搞的预期年化收益率
2、相对于起预期年化收益率比较合理的最大会策划
3、全球股票市场的低相关度（相关度最好是一个很小很小的负值）
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

    def try_gen_enter_signal(self):
        """进入策略"""
        raise NotImplementedError("Must implement enter_market()")

    def try_gen_exit_signal(self):
        """退出策略"""
        raise NotImplementedError("Must implement exit_market()")

    def try_gen_signals(self):
        self.try_gen_enter_signal()
        self.try_gen_exit_signal()
