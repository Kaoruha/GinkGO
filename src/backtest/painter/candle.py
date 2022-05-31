"""
蜡烛图
"""
import time
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import numpy as np
from matplotlib.widgets import Cursor
from src.backtest.enums import Direction
from src.backtest.painter.base_painter import BasePainter
from src.data.ginkgo_mongo import ginkgo_mongo as gm


class CandlePainter(BasePainter):
    def __init__(self, name="蜡烛图", mav=(), *args) -> None:
        super(CandlePainter, self).__init__(name=name, mav=mav, *args)
        self.figure = plt.figure(num="Ginkgo回测 by Suny", figsize=(16, 9))
        self.code = "股票代码"
        self.ax1 = None
        self.ax2 = None
        self.trade_history = []

    def draw_live(self) -> None:
        # 设置字体
        # plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["font.sans-serif"] = ["Songti SC"]
        plt.rcParams["axes.unicode_minus"] = False
        title = ""
        draw_count = 0
        idle_count = 0
        while True:
            if self.raw.shape[0] < 10:
                next
            if self.raw.shape[0] > draw_count:
                idle_count = 0
                draw_count = self.raw.shape[0]
                if self.code == "股票代码":
                    self.code = self.raw["code"].loc[0]
                plt.cla()
                plt.clf()
                # 设置标题
                if title == "":
                    title = f"{self.raw.loc[0].code} Simulating"
                self.figure.suptitle(title, fontsize=20, x=0.5, y=0.97)
                # 预处理
                plt.ion()
                self.pre_treate()
                x = self.data["date"].values
                open_ = self.data["open"].values
                close = self.data["close"].values
                high = self.data["high"].values
                low = self.data["low"].values
                volume = self.data["volume"].values
                # 成交数据处理
                self.trade_history = self.broker.trade_history[
                    self.broker.trade_history["done"] == True
                ]
                buy_date = self.trade_history[
                    self.trade_history["deal"] == Direction["BUY"].value
                ]["date"].values
                buy_price = self.trade_history[
                    self.trade_history["deal"] == Direction["BUY"].value
                ]["price"].values
                sell_date = self.trade_history[
                    self.trade_history["deal"] == Direction["SELL"].value
                ]["date"].values
                sell_price = self.trade_history[
                    self.trade_history["deal"] == Direction["SELL"].value
                ]["price"].values
                # 划分Grid
                gs = mpl.gridspec.GridSpec(40, 40)

                # 生成上下两张图
                self.ax2 = self.figure.add_subplot(gs[29:40, 0:40])
                self.ax1 = self.figure.add_subplot(gs[0:30, 0:40], sharex=self.ax2)

                # 判断涨跌颜色
                up = close >= open_
                colors = np.zeros(up.size, dtype="U5")
                colors[:] = "coral"
                colors[up] = "teal"

                # 画图
                # 蜡烛
                height = self.data["height"].values
                self.ax1.bar(
                    x=x, height=height, bottom=open_, color=colors, zorder=1, alpha=1
                )
                # 腊烛芯
                self.ax1.vlines(
                    x, low, high, color=colors, linewidth=0.6, zorder=1, alpha=1
                )
                # 移动均线
                if len(self.mav) > 0:
                    for i in range(len(self.mav)):
                        name = "MA" + str(self.mav[i])
                        self.ax1.plot(x, self.data[name], label=name, zorder=1)
                # 成交记录
                self.ax1.scatter(
                    buy_date,
                    buy_price,
                    marker="v",
                    c="blue",
                    s=200,
                    zorder=3,
                    label="Buy",
                )
                self.ax1.scatter(
                    sell_date,
                    sell_price,
                    marker="^",
                    c="black",
                    s=200,
                    zorder=3,
                    label="Sell",
                )

                # 经纪人资产
                self.ax1.plot(
                    x, self.data["total_capital"] * close[0], label="Capital", zorder=1
                )

                self.ax1.axhline(
                    y=close[0], color="red", linestyle="--", linewidth=0.5, zorder=1
                )
                # 成交量
                self.ax2.bar(x=x, height=volume, color=colors)
                self.ax1.grid(color="gray", linestyle="--", linewidth=1, alpha=0.3)
                self.ax2.grid(color="gray", linestyle="--", linewidth=1, alpha=0.3)
                self.ax1.xaxis.set_major_locator(mpl.ticker.NullLocator())
                # self.ax1.xaxis.set_major_locator(
                #     mpl.ticker.MultipleLocator(base=int(len(x) / 10))
                # )
                gutter = max(20, int(len(x) / 12))
                self.ax2.xaxis.set_major_locator(
                    mpl.ticker.MultipleLocator(base=gutter)
                )
                self.ax1.legend()
                plt.pause(0.2)
                plt.ioff()
            else:
                idle_count += 1
                if idle_count > 50000:
                    break

        # 鼠标参考线
        # cursor1 = Cursor(
        #     self.ax1,
        #     horizOn=True,
        #     vertOn=True,
        #     useblit=True,
        #     color="lightblue",
        #     linewidth=0.8,
        # )
        # cursor2 = Cursor(
        #     self.ax2,
        #     horizOn=True,
        #     vertOn=True,
        #     useblit=True,
        #     color="lightblue",
        #     linewidth=0.8,
        # )
        plt.ion()
        title = f"{self.code} 回测完成"
        self.figure.suptitle(title, fontsize=20, x=0.5, y=0.97)
        plt.ioff()
        plt.show()
