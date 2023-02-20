"""
Average True Range
均幅指标（ATR）是取一定时间周期内的股价波动幅度的移动平均值，主要用于研判买卖时机。
均幅指标是显示市场变化率的指标，威尔德发现较高的ATR值常发生在市场底部，并伴随恐慌性抛盘。当其值较低时，则往往发生在合并以后的市场顶部。
"""
import datetime
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm


def CAL_TR(df):
    """
    TR计算方法，传入连续两个交易日的交易数据
    """
    df["high"] = df["high"].astype("float")
    df["low"] = df["low"].astype("float")
    df["close"] = df["close"].astype("float")
    today_range = df.iloc[-1]["high"] - df.iloc[-1]["low"]
    last_day_range_high = abs(df.iloc[-2]["close"] - df.iloc[-1]["high"])
    last_day_range_low = abs(df.iloc[-2]["close"] - df.iloc[-1]["low"])
    return max(today_range, last_day_range_low, last_day_range_high)


def CAL_ATR(code, date, period):
    """
    ATR 计算
    """
    # ATR的统计周期至少是一天，0或者负数天是不成立的
    if period < 1:
        print("Period should more than 1 day.")
        return 0

    end = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    count = 1
    while True:
        start = (end + datetime.timedelta(days=-period * count - 1)).strftime(
            "%Y-%m-%d"
        )
        df = gm.get_dayBar_by_mongo(code=code, start_date=start, end_date=date)
        if df.shape[0] >= period + 1:
            break
        else:
            count += 1
            if count >= 10:
                print("Please Check your code.")
                return 0
    df = df.tail(period + 1)
    df = df[["date", "code", "open", "high", "low", "close"]]
    df["high"] = df["high"].astype("float")
    df["low"] = df["low"].astype("float")
    df["close"] = df["close"].astype("float")
    df["today_range"] = abs(df["high"] - df["low"]).fillna(0)
    df["last_high"] = abs(df["close"].shift(1) - df["high"]).fillna(0)
    df["last_low"] = abs((df["close"].shift(1) - df["close"]).fillna(0))
    df["atr"] = df[["today_range", "last_high", "last_low"]].max(axis=1)
    # print(f'{code} {date} ATR:{df.tail(period)["atr"].mean()}')
    return df.tail(period)["atr"].mean()
