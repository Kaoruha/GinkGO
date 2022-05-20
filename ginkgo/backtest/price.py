import pandas as pd
import abc
from datetime import datetime
from ginkgo.backtest.enums import Interval, Source


class PriceBase(abc.ABC):
    def __init__(self, code) -> None:
        self.code = code


class Bar(PriceBase):
    """
    某一个时间段内的成交信息
    """

    @property
    def pct_change(self):
        r = (self.close_price - self.open_price) / self.open_price * 100
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
        d["pct_change"] = self.pct_change
        d["pct_change_lastday"] = self.pct_change_lastday
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
        pct: float = 0.0,  # 与昨日相比涨跌幅
        open_interest: int = 0,  # 未结清权益
        source: Source = Source.BACKTEST,
        datetime: str = None,
    ) -> None:
        super(Bar, self).__init__(code=code)
        self.interval: Interval = interval
        self.source: Source = source
        self.datetime: datetime = datetime
        self.volume: int = int(volume)
        self.turnover: float = float(turnover)
        self.open_interest: int = int(open_interest)
        self.open_price: float = float(open_price)
        self.high_price: float = float(high_price)
        self.low_price: float = float(low_price)
        self.close_price: float = float(close_price)
        self.pct_change_lastday: float = float(pct)
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
            "pct_change_lastday",
        ]

    def __repr__(self):
        s = str(self.data_series)
        return s


class Tick(PriceBase):
    pass
