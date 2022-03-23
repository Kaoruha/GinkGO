"""
Author: Kaoru
Date: 2022-03-08 21:37:29
LastEditTime: 2022-03-23 00:34:27
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/selector/base_selector.py
What goes around comes around.
"""
"""
选股模块的基类
"""

import abc


class BaseSelector(abc.ABC):
    def __init__(self, name="基础筛选器", *args, **kwargs):
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def get_result(self, today: str) -> []:
        """
        返回需要查看的股票代码
        """
        return []
        # raise NotImplementedError("Must implement get_result()")
