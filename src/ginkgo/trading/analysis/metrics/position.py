# Upstream: AnalysisEngine, 分析报告模块
# Downstream: 分析报告消费方
# Role: 持仓层级指标实现 (MaxPositions, ConcentrationTopN)


"""
持仓层级分析指标

提供持仓数量统计和集中度分析等指标。
"""

from typing import Any, Dict, List

import pandas as pd

from ginkgo.trading.analysis.metrics.base import Metric


class MaxPositions:
    """最大同时持仓数量

    按时间戳分组，统计每个时间点上 volume > 0 的唯一 code 数量，
    返回所有时间戳中的最大值。

    requires: ["position"]
    params: {}
    """

    name: str = "max_positions"
    requires: List[str] = ["position"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any:
        df = data["position"]
        active = df[df["volume"] > 0]
        if active.empty:
            return 0
        counts = active.groupby("timestamp")["code"].nunique()
        return int(counts.max())


class ConcentrationTopN:
    """Top N 持仓集中度

    在最后一个时间戳上，获取 volume 最大的 N 个持仓，
    返回 sum(top_n_volume) / sum(all_volume)。
    当总 volume 为 0 时返回 0。

    requires: ["position"]
    params: {"n": 3}
    """

    def __init__(self, n: int = 3):
        self.name = "concentration_top_n"
        self.requires: List[str] = ["position"]
        self.params: Dict[str, Any] = {"n": n}
        self._n = n

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any:
        df = data["position"]
        last_ts = df["timestamp"].max()
        last_positions = df[df["timestamp"] == last_ts]

        if last_positions.empty or last_positions["volume"].sum() == 0:
            return 0.0

        total_volume = last_positions["volume"].sum()
        top_n = last_positions.nlargest(self._n, "volume")
        top_volume = top_n["volume"].sum()

        return float(top_volume / total_volume)
