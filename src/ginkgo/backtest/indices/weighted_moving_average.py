import pandas as pd
import numpy as np
from ginkgo.backtest.indices.base_index import BaseIndex


class WeightedMovingAverage(BaseIndex):
    """
    WMA
    """

    def __init__(self, name: str = "wma", timeperiod: int = 5, *args, **kwargs) -> None:
        super(WeightedMovingAverage, self).__init__(name, *args, **kwargs)
        self._timeperiod = timeperiod
        # Generate the weight, a list contains the weight of each data from 1 to timeperiod
        self._weight = [
            i / sum(range(1, self._timeperiod + 1))
            for i in range(1, self._timeperiod + 1)
        ]

    def cal(self, raw: pd.DataFrame, *args, **kwargs) -> None:
        df = raw.copy()
        rs = pd.DataFrame()
        column_name = f"{self.name}"
        rs["timestamp"] = df["timestamp"]
        # Calculate the weight, the sum of the weight is 1, the weight of the latest data is the largest
        for i, r in df.iterrows():
            if i < self._timeperiod:
                rs.loc[i, column_name] = np.nan
            else:
                rs.loc[i, column_name] = sum(
                    [
                        self._weight[j] * df.loc[i - j, "close"]
                        for j in range(self._timeperiod)
                    ]
                )
        return rs
