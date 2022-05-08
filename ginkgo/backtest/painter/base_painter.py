"""
基础绘图类
"""
import pandas as pd
import abc
import matplotlib.pyplot as plt
from ginkgo.backtest.price import Bar


class BasePainter(abc.ABC):
    def __init__(self, name="基础绘图", mav=(), *args):
        super(BasePainter, self).__init__(*args)
        self.name = name
        self.raw = pd.DataFrame()
        self.data = None
        self.broker = None
        self.figure = None
        self.mav = mav

        self.create_canvas()

    def create_canvas(self):
        pass

    def get_price(self, broker, price: Bar):
        self.broker = broker
        dic = {}
        for i in price.data.keys():
            dic[i] = price.data[i]
        dic["total_capital"] = broker.total_capital / broker.init_capital
        df = pd.Series(dic)
        self.raw = self.raw.append(df, ignore_index=True)

    def pre_treate(self):
        """
        数据预处理
        """
        df = self.raw.copy()
        df["open"] = df["open"].astype(float)
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["height"] = df["close"] - df["open"]
        df["height"][df["height"] == 0] = 0.01
        if len(self.mav) > 0:
            for i in range(len(self.mav)):
                name = "MA" + str(self.mav[i])
                df[name] = df["close"].rolling(self.mav[i], min_periods=1).mean()

        self.data = df.copy()

    def draw(self):
        pass
