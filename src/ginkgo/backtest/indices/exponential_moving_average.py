import pandas as pd
import numpy as np
from ginkgo.backtest.indices.base_index import BaseIndex


class ExponentialMovingAverage(BaseIndex):
    """
    EMA
    """

    def __init__(self, name: str = "ema", timeperiod: int = 5, *args, **kwargs) -> None:
        super(ExponentialMovingAverage, self).__init__(name, *args, **kwargs)
        self._timeperiod = timeperiod
        self._factor = 0.9
        self._factor_list = [self._factor**i for i in range(self._timeperiod)]
        self._weight = [
            self._factor_list[i] / sum(self._factor_list)
            for i in range(self._timeperiod)
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
                continue
            rs.loc[i, column_name] = sum(
                [
                    self._weight[j] * df.loc[i - j, "close"]
                    for j in range(self._timeperiod)
                ]
            )

        # rs.fillna(0, inplace=True)
        return rs
