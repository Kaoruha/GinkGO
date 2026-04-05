# Upstream: Metric Protocol (base.py)
# Downstream: AnalysisEngine, 分析报告模块
# Role: Signal 层级指标实现 (SignalCount, LongShortRatio, DailySignalFreq)


"""
Signal 层级分析指标

提供基于 Signal 数据的分析指标：信号计数、多空比例、日均信号频率。
"""

from typing import Dict, Any, List

import pandas as pd


class SignalCount:
    """信号总数指标

    计算信号 DataFrame 的总行数，即信号总数。
    """

    name: str = "signal_count"
    requires: List[str] = ["signal"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> int:
        """返回信号总数"""
        df = data["signal"]
        return len(df)


class LongShortRatio:
    """多空比例指标

    计算做多信号数量与做空信号数量的比值。
    当无做空信号时返回 0。
    """

    name: str = "long_short_ratio"
    requires: List[str] = ["signal"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        """返回多空比例，无做空信号时返回 0"""
        df = data["signal"]
        long_count = len(df[df["direction"] == 1])
        short_count = len(df[df["direction"] == -1])
        if short_count == 0:
            return 0.0
        return long_count / short_count


class DailySignalFreq:
    """日均信号频率指标

    计算总信号数除以唯一交易日天数。
    """

    name: str = "daily_signal_freq"
    requires: List[str] = ["signal"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        """返回日均信号频率"""
        df = data["signal"]
        if df.empty:
            return 0.0
        unique_days = df["timestamp"].dt.date.nunique()
        if unique_days == 0:
            return 0.0
        return len(df) / unique_days
