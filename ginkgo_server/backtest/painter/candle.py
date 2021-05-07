"""
蜡烛图
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import mplfinance as mpf
import pandas as pd

from ginkgo_server.data.ginkgo_mongo import ginkgo_mongo as gm


def test():
    data = gm.get_dayBar_by_mongo(
        code="sz.000725", start_date="2020-01-01", end_date="2020-04-04"
    )
    data["date"] = pd.DatetimeIndex(data["date"])
    data.set_index(["date"], inplace=True)
    data["open"] = data["open"].astype(float)
    data["close"] = data["close"].astype(float)
    data["high"] = data["high"].astype(float)
    data["low"] = data["low"].astype(float)
    data["volume"] = data["volume"].astype(int)
    # print(data.columns)
    df = data[["open", "close", "high", "low", "volume"]]
    mc = mpf.make_marketcolors(
        up="red", down="green", edge="i", wick="i", volume="in", inherit=True
    )
    style = mpf.make_mpf_style(
        gridaxis="both", gridstyle="-.", y_on_right=False, marketcolors=mc
    )
    mpl.rcParams["lines.linewidth"] = 0.2

    add_plot = [mpf.make_addplot(data["high"])]
    mpf.plot(
        df,
        type="candle",
        title="sz000725",
        figratio=(1200 / 72, 480 / 60),
        volume=True,
        mav=((5, 20)),
        addplot=add_plot,
        style=style,
        datetime_format="%Y-%m-%d",
        xrotation=45,
    )
    plt.show()
