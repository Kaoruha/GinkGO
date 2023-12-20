from matplotlib.widgets import Cursor
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


class ResultPlot(BasePlot):
    __abstract__ = False

    def __init__(self, title: str = "", *args, **kwargs) -> None:
        super(ResultPlot, self).__init__(title, args, kwargs)
        self.ax = []
        self.backtest_id = ""
        self.raw = None

    def update_data(self, id: str, data: dict) -> None:
        self.backtest_id = id
        fig_count = len(data.keys())
        self.raw = data
        if fig_count == 0:
            GLOG.ERROR("Plot.Show got no data. ")
            return
        self.figure_init(fig_count)
        self.update_plot(data)

    def figure_init(self, fig_count: int) -> None:
        logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

        self.figure = plt.figure(figsize=(16, 9))
        # self.figure, self.ax = plt.subplots(fig_count, 1)
        # 设置字体
        plt.rcParams["font.sans-serif"] = ["SimHei"]
        plt.rcParams["axes.unicode_minus"] = False

        # 设置标题
        self.figure.suptitle(f"Backtest {self.backtest_id}", fontsize=20, x=0.5, y=0.97)

        # 划分Grid
        hight = fig_count * 20
        gs = gridspec.GridSpec(40, hight)

        for i in range(fig_count):
            if i > 0:
                self.ax.append(
                    # self.figure.add_subplot(gs[i * 20 : (i + 1) * 20 - 1, 0:40])
                    self.figure.add_subplot(
                        gs[i * 20 : (i + 1) * 20 - 1, 0:40], sharex=self.ax[0]
                    )
                )
            else:
                self.ax.append(
                    self.figure.add_subplot(gs[i * 20 : (i + 1) * 20 - 2, 0:40])
                )
            self.ax[i].legend(title=str(i), title_fontsize=25)
            self.ax[i].set_ylabel("Y-Label")
            print(f"should have set ax {i}")
            print(self.ax[i])

    def update_plot(self, data: dict):
        if data is None:
            GLOG.WARN("Can not plot null.")
            return
        if len(data.keys()) == 0:
            GLOG.WARN("Can not plot null.")
            return
        # plt.ion()
        plt.cla()
        date_start = None
        date_end = None
        for key in data.keys():
            min_date = data[key]["timestamp"].min()
            if date_start is None:
                date_start = min_date
            elif min_date < date_start:
                date_start = min_date
            max_date = data[key]["timestamp"].max()
            if date_end is None:
                date_end = max_date
            elif max_date > date_end:
                date_end = max_date
        complete_dates = pd.date_range(date_start, date_end)
        a = None
        for i in range(len(data.keys())):
            key = list(data.keys())[i]
            df = data[key]
            df_ = pd.DataFrame(
                {
                    "timestamp": complete_dates,
                    "value": [np.nan] * len(complete_dates),
                }
            )
            for index, row in df.iterrows():
                time = row["timestamp"]
                value = row["value"]
                df_.loc[df_["timestamp"] == time, "value"] = value
            df_.fillna(method="ffill", inplace=True)
            df_.fillna(0, inplace=True)
            y = df_["value"].astype(float).values
            self.ax[i].plot(complete_dates, y)
        plt.draw()
        plt.show()
        # plt.ioff()
