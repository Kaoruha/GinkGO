# Upstream: Metric Protocol (base.py)
# Downstream: AnalysisEngine, 分析报告模块
# Role: 跨数据源指标实现 (SignalOrderConversion, SignalIC)


"""
跨数据源分析指标

提供基于多数据源联合分析的计算指标：
信号-订单转化率、信号IC (Information Coefficient)。
"""

from typing import Dict, Any, List

import pandas as pd
from scipy.stats import spearmanr


class SignalOrderConversion:
    """信号订单转化率指标

    计算有信号产生的标的中被成功转化为订单的比例。
    conversion_rate = |signal_codes ∩ order_codes| / |signal_codes|
    无信号时返回 0。
    """

    name: str = "signal_order_conversion"
    requires: List[str] = ["signal", "order"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        """返回信号订单转化率"""
        df_signal = data["signal"]
        df_order = data["order"]

        signal_codes = set(df_signal["code"].unique())
        if len(signal_codes) == 0:
            return 0.0

        order_codes = set(df_order["code"].unique())
        converted = len(signal_codes & order_codes)
        return converted / len(signal_codes)


class SignalIC:
    """信号IC指标 (Information Coefficient)

    计算每日聚合信号方向与次日组合收益率的 Spearman 秩相关系数。
    IC 越高说明信号对次日收益的预测能力越强。

    聚合信号方向 = sum(direction) / count(direction)，long=+1, short=-1。
    次日收益率 = nav[T+1] / nav[T] - 1。
    数据点不足 (< 2) 时返回 0。
    """

    name: str = "signal_ic"
    requires: List[str] = ["signal", "net_value"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        """返回信号IC (Spearman秩相关系数)"""
        df_signal = data["signal"]
        df_nav = data["net_value"]

        # 按日期聚合信号方向：均值（long=+1, short=-1）
        df_signal = df_signal.copy()
        df_signal["date"] = pd.to_datetime(df_signal["timestamp"]).dt.date
        daily_signal = df_signal.groupby("date")["direction"].mean()

        # 构建净值时间序列，按日期索引
        df_nav = df_nav.copy()
        df_nav["date"] = pd.to_datetime(df_nav["timestamp"]).dt.date
        nav_series = df_nav.groupby("date")["value"].last().sort_index()

        # 计算次日收益率
        dates_with_next = sorted(set(daily_signal.index) & set(nav_series.index))
        paired_dates = []
        for d in dates_with_next:
            idx = nav_series.index.get_loc(d)
            if idx + 1 < len(nav_series):
                next_date = nav_series.index[idx + 1]
                paired_dates.append((d, next_date))

        if len(paired_dates) < 2:
            return 0.0

        signal_values = [float(daily_signal[d]) for d, _ in paired_dates]
        return_values = [float(nav_series[nd] / nav_series[d] - 1) for d, nd in paired_dates]

        correlation, _ = spearmanr(signal_values, return_values)
        # spearmanr 对常量输入返回 nan，此时 IC 无意义
        if pd.isna(correlation):
            return 0.0
        return float(correlation)
