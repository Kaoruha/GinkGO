"""
基础绘图类
"""
import pandas as pd
import matplotlib.pyplot as plt
from ginkgo.backtest.price import DayBar, Min5Bar


class BasePainter(object):
    def __init__(self, *args):
        super(BasePainter, self).__init__(*args)
        self.raw = pd.DataFrame()
        self.data = None
        self.broker = None
        plt.ion()

    def get_price(self, broker, price: DayBar):
        self.broker = broker
        dic = {}
        for i in price.data.keys():
            dic[i] = price.data[i]
        df = pd.Series(dic)
        self.raw = self.raw.append(df, ignore_index=True)

    def pre_treate(self):
        df = self.raw.copy()
        df["date"] = pd.DatetimeIndex(df["date"])
        df.set_index(["date"], inplace=True)
        df = df.sort_index()
        df["open"] = df["open"].astype(float)
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)

        self.data = df

    def draw(self):
        pass
