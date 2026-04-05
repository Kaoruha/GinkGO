# Upstream: AnalysisEngine, MetricRegistry
# Downstream: None (leaf metric implementations)
# Role: 订单层级指标 - FillRate, AvgSlippage, CancelRate


"""
订单层级分析指标 (Order-level Metrics)

提供订单成交率、平均滑点、撤单率等核心指标。
"""

from typing import Dict, Any, List

import pandas as pd


class FillRate:
    """订单成交率指标

    计算已成交订单占总订单的比例。
    成交判定：status == 1。
    """

    name: str = "fill_rate"
    requires: List[str] = ["order"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        df = data["order"]
        total = len(df)
        if total == 0:
            return 0.0
        filled = len(df[df["status"] == 1])
        return filled / total


class AvgSlippage:
    """平均滑点指标

    计算已成交订单的平均滑点。
    滑点定义：limit_price - transaction_price（正值为不利滑点）。
    仅统计 status == 1 的订单，无成交时返回 0.0。
    """

    name: str = "avg_slippage"
    requires: List[str] = ["order"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        df = data["order"]
        if len(df) == 0:
            return 0.0
        filled = df[df["status"] == 1]
        if len(filled) == 0:
            return 0.0
        slippage = filled["limit_price"] - filled["transaction_price"]
        return slippage.mean()


class CancelRate:
    """撤单率指标

    计算已撤单订单占总订单的比例。
    撤单判定：status == 0。
    """

    name: str = "cancel_rate"
    requires: List[str] = ["order"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        df = data["order"]
        total = len(df)
        if total == 0:
            return 0.0
        cancelled = len(df[df["status"] == 0])
        return cancelled / total
