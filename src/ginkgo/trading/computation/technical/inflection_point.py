# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: InflectionPoint拐点分析继承BaseIndicator提供价格拐点检测和趋势反转分析支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import numpy as np
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class InflectionPoint(BaseIndicator):
    """
    InflectionPoint is a class that represents the inflection point index.
    Reverse and continue 4 bars after the inflection point.
    """

    def __init__(self, name: str = "ip", window: int = 4, *args, **kwargs):
        super(InflectionPoint, self).__init__(name, *args, **kwargs)
        self._window = window

    def cal(self, raw: pd.DataFrame, *args, **kwargs) -> None:
        df = raw.copy()
        rs = pd.DataFrame()
        column_name = f"{self.name}"
        rs["timestamp"] = df["timestamp"]
        for i, r in df.iterrows():
            if i < self._window - 1:
                rs.loc[i, column_name] = np.nan
                continue
            if i > df.shape[0] - self._window:
                rs.loc[i, column_name] = np.nan
                continue
            first_ind = i - self._window + 1
            direction = (
                1 if df.loc[first_ind, "close"] > df.loc[first_ind, "open"] else -1
            )
            flag = True
            for j in range(self._window):
                index = j + first_ind + 1
                if (df.loc[index, "close"] - df.loc[index, "open"]) * direction >= 0:
                    flag = False
                    break
                if j >= 1:
                    if (
                        df.loc[index, "close"] - df.loc[index - 1, "close"]
                    ) * direction >= 0:
                        flag = False
                        break

            if flag:
                rs.loc[i, column_name] = direction * -1
            else:
                rs.loc[i, column_name] = 0
        return rs
