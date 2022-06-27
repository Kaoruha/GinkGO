import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
import numpy as np
from ginkgo.backtest.painter.base_painter import BasePainter
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


class CandleTrend(BasePainter):
    def __init__(
        self,
        code: str,
        starttime: str,
        endtime: str,
        name: str = "CandleTrend",
        mav=(5, 30),
        *args,
    ) -> None:
        super(CandleTrend, self).__init__(name=name, mav=mav, *args)
        self.figure = plt.figure(num="Ginkgo回测 by Suny", figsize=(16, 9))
        self.code = code
        self.starttime = starttime
        self.endtime = endtime
        plt.rcParams["font.sans-serif"] = ["Songti SC"]
        plt.rcParams["axes.unicode_minus"] = False

    def get_data(
        self,
    ):
        self.raw = gm.get_dayBar_by_mongo(
            code=self.code, start_date=self.starttime, end_date=self.endtime
        )
        self.pre_treate()

    def draw(
        self,
    ):
        # 设置标题
        title = f"{self.raw.loc[0].code} Simulating"
        self.figure.suptitle(title, fontsize=20, x=0.5, y=0.97)

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
        colors[:] = "coral"
        colors[up] = "teal"

        # 画图
        # 蜡烛
        height = self.data["height"].values
        self.ax1.bar(x=x, height=height, bottom=open_, color=colors, zorder=1, alpha=1)
        # 腊烛芯
        self.ax1.vlines(x, low, high, color=colors, linewidth=0.6, zorder=1, alpha=1)
        # 移动均线
        if len(self.mav) > 0:
            for i in range(len(self.mav)):
                name = "MA" + str(self.mav[i])
                self.ax1.plot(x, self.data[name], label=name, zorder=1)

        # 成交量
        self.ax2.bar(x=x, height=volume, color=colors)
        self.ax1.grid(color="gray", linestyle="--", linewidth=1, alpha=0.3)

        self.ax2.grid(color="gray", linestyle="--", linewidth=1, alpha=0.3)
        self.ax1.xaxis.set_major_locator(mpl.ticker.NullLocator())
        # self.ax1.xaxis.set_major_locator(
        #     mpl.ticker.MultipleLocator(base=int(len(x) / 10))
        # )

        gutter = max(20, int(len(x) / 12))
        self.ax2.xaxis.set_major_locator(mpl.ticker.MultipleLocator(base=gutter))
        self.ax1.legend()
        plt.show()
