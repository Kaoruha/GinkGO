"""
价格信息类
"""
import abc
import pandas as pd
from src.backtest.enums import Interval


class Price(metaclass=abc.ABCMeta):
    def __init__(self, price_type: Interval):
        self.type_ = price_type
        self.data = None


class DayBar(Price):
    def __init__(
        self,
        date: str,
        code: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        pre_close: float,
        volume: int,
        amount: float,
        adjust_flag: int,
        turn: float,
        pct_change: float,
        is_st: int,
        *args,
        **kwargs
    ):
        super(DayBar, self).__init__(price_type=Interval.DAILY)
        self.index = [
            "date",
            "code",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "volume",
            "amount",
            "adjust_flag",
            "turn",
            "pct_chg",
            "is_st",
        ]
        self.data = pd.Series(index=self.index)
        self.data.date = date
        self.data.code = code
        self.data.open = open_
        self.data.high = high
        self.data.low = low
        self.data.close = close
        self.data.pre_close = pre_close
        self.data.volume = volume
        self.data.amount = amount
        self.data.adjust_flag = adjust_flag
        self.data.turn = turn
        self.data.pct_chg = pct_change
        self.data.is_st = is_st

    def __repr__(self):
        s = str(self.data)
        return s


class Min5Bar(Price):
    def __init__(
        self,
        date: str,
        time: str,
        code: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        amount: float,
        adjust_flag: int,
    ):
        super(Min5Bar, self).__init__(price_type=Interval.MIN5)
        self.index = [
            "date",
            "time",
            "code",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "amount",
            "adjustFlag",
        ]
        self.data = pd.Series(index=self.index)
        self.data.date = date
        self.data.time = time
        self.data.code = code
        self.data.open = open_
        self.data.high = high
        self.data.low = low
        self.data.close = close
        self.data.volume = volume
        self.data.amount = amount
        self.data.adjustFlag = adjust_flag

    def __repr__(self):
        s = str(self.data)
        return s


class CurrentPrice(Price):
    pass
