"""
策略类
"""
from ginkgo.libs.enums import MarketType
import pandas as pd


class BaseStrategy(object):
    """
    基础策略类
    回头改成抽象类
    """

    def data_transfer(self, data: pd.DataFrame):
        raise NotImplementedError("Must implement data_transfer()")

    def enter_market(self):
        raise NotImplementedError("Must implement enter_market()")

    def exiting_market(self):
        raise NotImplementedError("Must implement existing_market()")
