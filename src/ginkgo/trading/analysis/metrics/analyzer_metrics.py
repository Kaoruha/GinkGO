# Upstream: MetricRegistry, AnalyzerRecord 时间序列
# Downstream: AnalysisEngine 报告生成
# Role: 事后分析指标 — 基于 AnalyzerRecord 时间序列的滚动/IC 分析


"""
事后分析指标 (Analyzer Metrics)

基于 AnalyzerRecord 生成的时间序列数据，提供滚动统计和 IC 分析指标。
所有指标都按 analyzer 名称参数化，通过 register_instance() 注册到 MetricRegistry。
"""

from typing import Any, Dict, List

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .base import Metric


class RollingMean(Metric):
    """滚动均值 — 对指定 analyzer 的 value 列做窗口滚动平均"""

    def __init__(self, analyzer_name: str, window: int = 20):
        self.name = f"rolling_mean.{analyzer_name}"
        self.requires = [analyzer_name]
        self.params: Dict[str, Any] = {"analyzer": analyzer_name, "window": window}

    def compute(self, data: Dict[str, pd.DataFrame]) -> pd.Series:
        return data[self.requires[0]]["value"].rolling(self.params["window"]).mean()


class RollingStd(Metric):
    """滚动标准差 — 对指定 analyzer 的 value 列做窗口滚动标准差"""

    def __init__(self, analyzer_name: str, window: int = 20):
        self.name = f"rolling_std.{analyzer_name}"
        self.requires = [analyzer_name]
        self.params: Dict[str, Any] = {"analyzer": analyzer_name, "window": window}

    def compute(self, data: Dict[str, pd.DataFrame]) -> pd.Series:
        return data[self.requires[0]]["value"].rolling(self.params["window"]).std()


class CV(Metric):
    """变异系数 = rolling_std / rolling_mean"""

    def __init__(self, analyzer_name: str, window: int = 20):
        self.name = f"cv.{analyzer_name}"
        self.requires = [analyzer_name]
        self.params: Dict[str, Any] = {"analyzer": analyzer_name, "window": window}

    def compute(self, data: Dict[str, pd.DataFrame]) -> pd.Series:
        r_mean = data[self.requires[0]]["value"].rolling(self.params["window"]).mean()
        r_std = data[self.requires[0]]["value"].rolling(self.params["window"]).std()
        return r_std / r_mean


class IC(Metric):
    """IC — Analyzer 与未来收益的 Spearman 相关性

    计算 analyzer 值与 lag 天后 net_value 变化的相关性。
    requires = [analyzer_name, "net_value"]
    """

    def __init__(self, analyzer_name: str, method: str = "spearman", lag: int = 1):
        self.name = f"ic.{analyzer_name}"
        self.requires = [analyzer_name, "net_value"]
        self.params: Dict[str, Any] = {
            "analyzer": analyzer_name,
            "method": method,
            "lag": lag,
        }

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        a = data[self.params["analyzer"]]["value"]
        nv = data["net_value"]["value"]
        # net_value 变化率
        nv_changes = nv.pct_change().shift(-self.params["lag"])
        aligned = pd.DataFrame({"a": a, "nv_changes": nv_changes}).dropna()
        if len(aligned) < 5:
            return 0.0
        corr, _ = spearmanr(aligned["a"], aligned["nv_changes"])
        return float(corr) if not np.isnan(corr) else 0.0
