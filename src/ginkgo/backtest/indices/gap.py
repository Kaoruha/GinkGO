import pandas as pd
from ginkgo.backtest.indices.base_index import BaseIndex


class Gap(BaseIndex):
    # Need Optimize , so many gap, need to filter
    def __init__(self, name: str = "gap", *args, **kwargs) -> None:
        super(Gap, self).__init__(name=name, *args, **kwargs)
        self._filter = 0.5

    def cal(self, raw: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        rs = pd.DataFrame()
        column_name = f"{self.name}"
        for i, r in df.iterrows():
            rs.loc[i, "timestamp"] = r["timestamp"]
            if i == 0:
                rs.loc[i, column_name] = 0
                continue
            last_top = df.loc[i - 1, "high"]
            last_bot = df.loc[i - 1, "low"]
            h = last_top - last_bot
            top = (
                df.loc[i, "open"]
                if df.loc[i, "open"] > df.loc[i, "close"]
                else df.loc[i, "close"]
            )
            bot = (
                df.loc[i, "open"]
                if df.loc[i, "open"] < df.loc[i, "close"]
                else df.loc[i, "close"]
            )
            if bot > last_top:
                gap = bot - last_top
                rs.loc[i, column_name] = gap if gap > h * self._filter else 0
                continue
            if top < last_bot:
                gap = top - last_bot
                rs.loc[i, column_name] = gap if abs(gap) > h * self._filter else 0
                continue
            rs.loc[i, column_name] = 0
        return rs
