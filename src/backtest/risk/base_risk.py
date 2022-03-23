"""
Author: Kaoru
Date: 2022-01-09 22:17:46
LastEditTime: 2022-03-23 00:34:05
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/risk/base_risk.py
What goes around comes around.
"""
"""
风控类
"""
import abc
from src.backtest.event_engine import EventEngine


class BaseRisk(abc.ABC):
    """
    风控基类
    回头改成抽象类
    """

    def __init__(self, name="基础风控") -> None:
        self._name = name
        self._engine = None

    @property
    def name(self):
        return self._name

    def engine_register(self, engine: EventEngine):
        # 引擎注册，通过Broker的注册获得引擎实例
        self._engine = engine
