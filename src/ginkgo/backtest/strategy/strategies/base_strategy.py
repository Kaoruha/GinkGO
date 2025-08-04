import pandas as pd
from typing import List
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.core.backtest_base import BacktestBase


class StrategyBase(BacktestBase):
    def __init__(self, name: str = "Strategy", *args, **kwargs):
        super(StrategyBase, self).__init__(name, *args, **kwargs)
        self._raw = {}
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    @property
    def data_feeder(self):
        return self._data_feeder

    def cal(self, portfolio_info, event, *args, **kwargs) -> List[Signal]:
        """
        策略计算方法
        Args:
            portfolio_info(Dict): 投资组合信息
            event(EventBase): 事件
        Returns:
            List[Signal]: 信号列表，如果没有信号返回空列表
        """
        return []
