import pandas as pd
import numpy as np
from ginkgo.backtest.indices.base_index import BaseIndex


class AverageTrueRange(BaseIndex):
    """
    ATR
    """

    def __init__(self, name: str = "atr", n: int = 14, *args, **kwargs) -> None:
        super(AverageTrueRange, self).__init__(name, *args, **kwargs)
        self._n = n

    def cal(self, raw: pd.DataFrame, *args, **kwargs) -> None:
        # Data check
        if raw.shape[0] < self._n + 1:
            return 0
        df = raw.copy()
        df.sort_values(by="timestamp", inplace=True)
        tr = 0
        column_name = f"{self._name}"
        for i, r in df.iterrows():
            if i == 0:
                df.loc[i, "tr"] = np.nan
                continue
            h = r["high"]
            l = r["low"]
            c = r["close"]
            pc = df.iloc[i - 1]["close"]
            ph = df.iloc[i - 1]["high"]
            pl = df.iloc[i - 1]["low"]
            tr = max(h - l, abs(c - pl), abs(ph - c))
            df.loc[i, "tr"] = tr
        df[column_name] = df["tr"].rolling(self._n).mean()
        return df[column_name].values[-1]
