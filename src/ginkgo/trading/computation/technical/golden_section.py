import pandas as pd
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class GoldenSection(BaseIndicator):
    # 从一波明显的趋势的起点画到终点，然后将这一波趋势分成五段，分别是0.236、0.382、0.5、0.618、1
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
