from matplotlib.widgets import Cursor, MultiCursor
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import logging
import datetime

from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.plots.base_plot import BasePlot
from ginkgo.backtest.indices.base_index import BaseIndex


class CandleWithIndexPlot(BasePlot):
    __abstract__ = False

    def __init__(self, title: str = "", *args, **kwargs) -> None:
        super(CandleWithIndexPlot, self).__init__(title, args, kwargs)
        self.ax1 = None
        self._indecies = []
        self._independente_indecies = []
        self._result = {}
        self._independente_ax = {}
        self._independent_result = {}

    def add_index(self, index, type: str = "line") -> None:
        if not isinstance(index, BaseIndex):
            GLOG.ERROR("Plot.add_index only support BaseIndex.")
            return
        self._indecies.append({"type": type, "index": index})

    def add_independent_index(self, index, type: str = "line") -> None:
        if not isinstance(index, BaseIndex):
            GLOG.ERROR("Plot.add_index only support BaseIndex.")
            return
        self._independente_indecies.append({"type": type, "index": index})

    def update_data(self, df: pd.DataFrame) -> None:
        if not isinstance(df, pd.DataFrame):
            GLOG.ERROR("Plot.get_data only support DataFrame. ")
            return

        if df.shape[0] == 0:
            GLOG.WARN("Plot got no data. ")
            return

        self.raw = df.copy()
        self.cal_index(df)
        self.update_plot()

    def on_press(self, event):
        if self.raw is None:
            self.infotips.set_text("Be Patient. There is no data in memory. ")
            return
        try:
            x, y = event.xdata, event.ydata
            date = matplotlib.dates.num2date(x).strftime("%Y-%m-%d")
            timestamp = datetime.datetime.strptime(date, "%Y-%m-%d")
            info = self.raw[self.raw.timestamp == timestamp]
            self.figure.canvas.draw_idle()
            msg = ""
            if info is None or info.shape[0] == 0:
                msg += f"No Data on {date}\n"
            elif info.shape[0] > 0:
                msg += f"DATE: {date}\n"
                msg += f"OPEN: {info.open.values[0]}\n"
                msg += f"HIGH: {info.high.values[0]}\n"
                msg += f"LOW : {info.low.values[0]}\n"
                msg += f"CLS : {info.close.values[0]}\n"
                msg += f"VOL : {info.volume.values[0]}\n"
                # Index
                for i in self._result.keys():
                    data = self._result[i]["data"][
                        self._result[i]["data"].timestamp == timestamp
                    ]
                    msg += f"{i}: {data[i].values[0]}\n"
                for i in self._independent_result.keys():
                    data = self._independent_result[i]["data"][
                        self._independent_result[i]["data"].timestamp == timestamp
                    ]
                    msg += f"{i}: {data[i].values[0]}\n"
            self.infotips.set_text(msg)
        except Exception as e:
            self.infotips.set_text(f"{e}")

    def cal_index(self, raw: pd.DataFrame) -> None:
        self._result = {}
        for i in self._indecies:
            self._result[i["index"].name] = {
                "type": i["type"],
                "data": i["index"].cal(raw),
            }
        for i in self._independente_indecies:
            self._independent_result[i["index"].name] = {
                "type": i["type"],
                "data": i["index"].cal(raw),
            }

    def figure_init(self) -> None:
        # TODO
        pass
        logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

        self.figure = plt.figure(figsize=(16, 9))
        # 设置字体
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False

        # 设置标题
        self.figure.suptitle(self.title, fontsize=20, x=0.5, y=0.97)

        # 划分Grid
        height = 40 + len(self._independente_indecies) * 20
        gs = gridspec.GridSpec(height, 40)

        # 生成上下两张图
        self.ax2 = self.figure.add_subplot(gs[29:40, 0:40])
        self.ax1 = self.figure.add_subplot(gs[0:30, 0:40], sharex=self.ax2)
        for i in range(len(self._independente_indecies)):
            start = 44 + i * 16
            end = 60 + i * 16
            ax = self.figure.add_subplot(gs[start:end, 0:40], sharex=self.ax2)
            self._independente_ax[self._independente_indecies[i]["index"].name] = ax

    def update_plot(self):
        if self.raw is None:
            GLOG.WARN("There is no data in plot.raw. ")
            return
        plt.ion()
        plt.cla()
        dates = self.raw["timestamp"].values
        open_ = self.raw["open"].astype(float).values
        close = self.raw["close"].astype(float).values
        high = self.raw["high"].astype(float).values
        low = self.raw["low"].astype(float).values
        volume = self.raw["volume"].astype(float).values
        # 判断涨跌颜色
        up = close >= open_
        colors = np.zeros(up.size, dtype="U5")
        colors[:] = "g"
        colors[up] = "r"
        # 蜡烛
        self.ax1.bar(
            x=dates, height=close - open_, bottom=open_, color=colors, alpha=0.5
        )
        # 腊烛芯
        self.ax1.vlines(dates, low, high, color=colors, linewidth=1, alpha=0.5)
        plt.xticks(ticks=dates)
        # 成交量
        self.ax2.bar(x=dates, height=volume, color=colors, alpha=0.5)
        self.ax1.grid(color="gray", linestyle="--", linewidth=1, alpha=0.2)
        self.ax1.xaxis.set_major_locator(ticker.NullLocator())
        self.ax2.xaxis.set_major_locator(ticker.MultipleLocator(base=30))
        self.ax2.grid(color="gray", linestyle="--", linewidth=1, alpha=0.2)
        plt.draw()

        # Cursor
        self.cursor = Cursor(
            self.ax1, horizOn=True, useblit=True, color="darkblue", linewidth=1.6
        )
        # self.cursor = MultiCursor(
        #     self.figure.canvas,
        #     (self.ax1, self.ax2, *self._independente_ax.values()),
        #     horizOn=True,
        #     vertOn=True,
        #     color="r",
        #     linewidth=0.6,
        # )
        # Txt Init
        self.infotips = self.ax1.text(
            0.02,
            0.98,
            "Click the figure.",
            horizontalalignment="left",
            verticalalignment="top",
            transform=self.ax1.transAxes,
        )
        # Index
        if len(self._result) > 0:
            for i in self._result.keys():
                plt_type = self._result[i]["type"]
                data = self._result[i]["data"]
                if data is None:
                    continue
                if plt_type == "line":
                    self.ax1.plot(data["timestamp"], data[i], label=f"fuck")
                elif plt_type == "scatter":
                    self.ax1.scatter(data["timestamp"], data[i], label=f"fuck")
                else:
                    self.ax1.plot(data["timestamp"], data[i], label=f"fuck")

        # Independent Index
        if len(self._independent_result) > 0:
            for i in self._independent_result.keys():
                plt_type = self._independent_result[i]["type"]
                data = self._independent_result[i]["data"]
                if data is None:
                    continue
                if plt_type == "line":
                    self._independente_ax[i].plot(
                        data["timestamp"],
                        data[i],
                    )
                elif plt_type == "scatter":
                    self._independente_ax[i].scatter(
                        data["timestamp"],
                        data[i],
                    )
                else:
                    self._independente_ax[i].plot(
                        data["timestamp"],
                        data[i],
                    )

        self.figure.canvas.mpl_connect("button_press_event", self.on_press)
        plt.ioff()
