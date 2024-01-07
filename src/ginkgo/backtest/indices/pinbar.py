import pandas as pd
from src.ginkgo.backtest.indices.base_index import BaseIndex


class PinBar(BaseIndex):
    def __init__(self, name: str = "pinbar", *args, **kwargs) -> None:
        super(PinBar, self).__init__(name=name, *args, **kwargs)

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
            up = r["high"] - r["open"]
            down = r["close"] - r["low"]
            chg_pct = abs(r["close"] - r["open"]) / r["open"]
            if chg_pct > 0.03:
                rs.loc[i, column_name] = 0
                continue
            if down == 0:
                rs.loc[i, column_name] = 0
                continue
            if up / down < 1.4 and up / down > 0.6:
                rs.loc[i, column_name] = 0
            else:
                shadow = up if up > down else down
                if shadow > abs(r["high"] - r["low"]) * 2 / 3:
                    rs.loc[i, column_name] = 1 if up > down else -1
                else:
                    rs.loc[i, column_name] = 0
        return rs
