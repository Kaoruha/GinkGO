"""
蜡烛图
"""
import matplotlib.pyplot as plt
from matplotlib.widgets import Cursor
import matplotlib as mpl
import pandas as pd
import numpy as np
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.backtest.painter.base_painter import BasePainter


class CandlePainter(BasePainter):
    def __init__(self, mav=(), *args):
        super(CandlePainter, self).__init__(mav=mav, *args)
        self.figure = plt.figure(num="Ginkgo回测 by Suny", figsize=(16, 9))
        self.ax1 = None
        self.ax2 = None

    def draw_live(self):
        draw_count = 0
        idle_count = 0
        while True:
            if self.raw.shape[0] > draw_count:
                idle_count = 0
                draw_count = self.raw.shape[0]
                plt.cla()
                plt.clf()
                # 设置字体
                # plt.rcParams["font.sans-serif"] = ["SimHei"]
                plt.rcParams["font.sans-serif"] = ["Songti SC"]
                plt.rcParams["axes.unicode_minus"] = False
                # 设置标题
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

                # 划分Grid
                gs = mpl.gridspec.GridSpec(40, 40)

                # 生成上下两张图
                self.ax2 = self.figure.add_subplot(gs[29:40, 0:40])
                self.ax1 = self.figure.add_subplot(gs[0:30, 0:40], sharex=self.ax2)

                # 判断涨跌颜色
                up = close >= open_
                colors = np.zeros(up.size, dtype="U5")
                colors[:] = "red"
                colors[up] = "green"

                # 画图
                # 蜡烛
                height = self.data["height"].values
                self.ax1.bar(x=x, height=height, bottom=open_, color=colors)
                # 腊烛芯
                self.ax1.vlines(x, low, high, color=colors, linewidth=0.6)
                # 移动均线
                if len(self.mav) > 0:
                    for i in range(len(self.mav)):
                        name = "MA" + str(self.mav[i])
                        self.ax1.plot(x, self.data[name], label=name)

                # 经纪人资产
                self.ax1.plot(x, self.data["total_capital"] * close[0], label="Capital")

                self.ax1.axhline(y=close[0], color="red", linestyle="--", linewidth=0.5)
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
                if idle_count > 4:
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
        title = f"{self.raw.loc[0].code} Complete"
        self.figure.suptitle(title, fontsize=20, x=0.5, y=0.97)
        plt.ioff()
        plt.show()
