"""
Author: Kaoru
Date: 2022-03-22 22:14:51
LastEditTime: 2022-04-21 01:51:03
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/ginkgo.backtest/price.py
What goes around comes around.
"""
import pandas as pd
import abc
from datetime import datetime
from ginkgo.backtest.enums import Interval, Source


class PriceBase(abc.ABC):
    def __init__(self, code) -> None:
        super().__init__()
        self.code = code


class Bar(PriceBase):
    """
    某一个时间段内的成交信息
    """

    @property
    def pct_change(self):
        r = (self.close_price - self.open_price) / self.open_price
        return round(r, 2)

    @property
    def data_series(self):
        d = pd.Series(index=self.index)
        d.datetime = self.datetime
        d.code = self.code
        d.open = self.open_price
        d.close = self.close_price
        d.high = self.high_price
        d.low = self.low_price
        d.volume = self.volume
        d.turnover = self.turnover
        d.open_interest = self.open_interest
        d['pct_change'] = self.pct_change
        return d


    def __init__(
        self,
        code: str = "bar",  # 代码
        interval: Interval = Interval.DAILY,  # Bar的间隔
        open_price: float = 0.0,  # 开盘价
        close_price: float = 0.0,  # 收盘价
        high_price: float = 0.0,  # 最高价
        low_price: float = 0.0,  # 最低价
        volume: int = 0,  # 成交量
        turnover: float = 0.0,  # 换手率
        open_interest: int = 0,  # 未结清权益
        source: Source = Source.BACKTEST,
        datetime: datetime = None,
    ) -> None:
        super(Bar, self).__init__(code=code)
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
        self.index = [
            "datetime",
            "code",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
            "open_interest",
            "pct_change",
        ]

    def __repr__(self):
        s = str(self.data_series)
        return s



class Tick(PriceBase):
    pass
