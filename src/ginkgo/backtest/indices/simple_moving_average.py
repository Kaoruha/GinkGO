import pandas as pd
from src.ginkgo.backtest.indices.base_index import BaseIndex


class SimpleMovingAverage(BaseIndex):
    """
    SMA
    """

    def __init__(self, name: str = "sma", timeperiod: int = 5, *args, **kwargs) -> None:
        super(SimpleMovingAverage, self).__init__(name, *args, **kwargs)
        self._timeperiod = timeperiod

    def cal(self, raw: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        df = raw.copy()
        rs = pd.DataFrame()
        column_name = f"{self.name}"
        rs["timestamp"] = df["timestamp"]
        rs[column_name] = df["close"].rolling(self._timeperiod).mean()
        # rs.fillna(0, inplace=True)
        return rs
