"""
蜡烛图
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import mplfinance as mpf
import pandas as pd

from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo_server.backtest.painter.base_painter import BasePainter


class CandlePainter(BasePainter):
    def __init__(self, *args):
        super(CandlePainter, self).__init__(*args)
        self.market_colors = mpf.make_marketcolors(
            up="red", down="green", edge="i", wick="i", volume="in", inherit=True
        )
        self.style = mpf.make_mpf_style(
            gridaxis="both",
            gridstyle="-.",
            y_on_right=False,
            marketcolors=self.market_colors,
        )
        self.fig, self.axex = mpf.plot(
            self.data[["open", "close", "high", "low", "volume"]],
            type="candle",
            title="sz000725",
            figratio=(2, 1),
            figscale=1.2,
            returnfig=True,
            volume=True,
            mav=((5, 30)),
            # addplot=add_plot,
            style=self.style,
            datetime_format="%Y-%m-%d",
            xrotation=45,
        )

    def draw(self):
        # 预处理
        self.pre_treate()
        df = self.data[["open", "close", "high", "low", "volume"]]
        self.axex[0].clear()
        self.axex[2].clear()
        mpf.plot(df, ax=self.axex[0], volume=self.axex[2])


# def test():
#     data = gm.get_dayBar_by_mongo(code="sz.000725", start_date="2020-01-01")
#     data["date"] = pd.DatetimeIndex(data["date"])
#     data.set_index(["date"], inplace=True)
#     data = data.sort_index()
#     data["open"] = data["open"].astype(float)
#     data["close"] = data["close"].astype(float)
#     data["high"] = data["high"].astype(float)
#     data["low"] = data["low"].astype(float)
#     data["volume"] = data["volume"].astype(float)
#     # print(data.columns)
#     df = data[["open", "close", "high", "low", "volume"]]
#     mc = mpf.make_marketcolors(
#         up="red", down="green", edge="i", wick="i", volume="in", inherit=True
#     )
#     style = mpf.make_mpf_style(
#         gridaxis="both", gridstyle="-.", y_on_right=False, marketcolors=mc
#     )
#     mpl.rcParams["lines.linewidth"] = 0.5

#     # add_plot = [mpf.make_addplot(data["high"])]
#     mpf.plot(
#         df,
#         type="candle",
#         title="sz000725",
#         figratio=(2, 1),
#         figscale=1.2,
#         volume=True,
#         mav=((5, 30)),
#         # addplot=add_plot,
#         style=style,
#         datetime_format="%Y-%m-%d",
#         xrotation=45,
#     )
# plt.show()
