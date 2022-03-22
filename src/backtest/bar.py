"""
Author: Kaoru
Date: 2022-03-22 11:36:02
LastEditTime: 2022-03-22 11:36:03
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/bar.py
What goes around comes around.
"""
from datetime import datetime
from src.backtest.enums import Interval, Source


class Bar(object):
    """
    某一个时间段内的成交信息
    """

    def __init__(
        self,
        interval: Interval = Interval.DAILY,
        source: Source = Source.BACKTEST,
        datetime: datetime = None,
        volume: int = 0,
        turnover: float = 0.0,
        open_interest: int = 0,
        open_price: float = 0.0,
        high_price: float = 0.0,
        low_price: float = 0.0,
        close_price: float = 0.0,
    ) -> None:
        self.interval: Interval = interval
        self.source: Source = source
        self.datetime: datetime = datetime
        self.volume: int = volume
        self.turnover: float = turnover
        self.open_interest: int = open_interest
        self.open_price: float = open_price
        self.high_price: float = high_price
        self.low_price: float = low_price
        self.close_price: float = close_price
