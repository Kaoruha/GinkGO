import pandas as pd
from src.ginkgo.backtest.indices.base_index import BaseIndex


class GoldenSection(BaseIndex):
    # Need Optimize , so many gap, need to filter
    def __init__(self, name: str = "gs", *args, **kwargs) -> None:
        super(GoldenSection, self).__init__(name=name, *args, **kwargs)

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
