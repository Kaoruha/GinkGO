"""
Author: Kaoru
Date: 2022-03-08 21:37:29
LastEditTime: 2022-04-03 01:14:04
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/ginkgo/backtest/selector/base_selector.py
What goes around comes around.
"""

import abc


class BaseSelector(abc.ABC):
    """
    选股模块的基类
    """

    def __init__(self, name="基础筛选器", *args, **kwargs):
        self.name = name

    @abc.abstractmethod
    def get_result(self, today: str) -> list:
        """
        返回需要关注的股票代码
        """
        raise NotImplementedError("Must implement get_result()")
