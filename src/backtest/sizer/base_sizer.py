"""
Author: Kaoru
Date: 2022-01-09 22:17:46
LastEditTime: 2022-04-01 12:44:37
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/sizer/base_sizer.py
What goes around comes around.
"""
import abc

from src.backtest.events import SignalEvent
from src.backtest.postion import Position


class BaseSizer(abc.ABC):
    """
    仓位管理基类
    每次开仓前需要有仓位管理模块决定开仓大小

    """

    def __init__(self, name="base_sizer"):
        self.name = name

    def __repr__(self):
        return f"仓位管理基类，{self.name}"

    @abc.abstractmethod
    def cal_size(
        self, event: SignalEvent, capital: int, positions: dict[str, Position]
    ) -> float:
        """
        获取信号事件
        根据初始金额、手持现金、当前持仓进行仓位调整，产生订单事件OrderEvent
        :param event: 某只股票的多空信号
        :param broker: 当前经纪人
        """
        raise NotImplementedError("Must implement get_signal()")
