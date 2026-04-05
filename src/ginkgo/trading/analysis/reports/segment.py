# Upstream: MetricRegistry, DataProvider, 各层级 Metric 实现
# Downstream: CLI/API/Web UI 消费方
# Role: 分段分析报告 — 按时间频率分段计算指标


"""
分段分析报告 (SegmentReport)

将 net_value 时间序列按频率 (月/季/年) 分段，
对每个分段独立计算组合指标，支持 dict/DataFrame/Rich 三种输出。
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from rich.table import Table

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.reports.base import AnalysisReport


# ============================================================
# 频率映射
# ============================================================

_FREQ_LABELS: Dict[str, str] = {
    "M": "month",
    "Q": "quarter",
    "Y": "year",
}


# ============================================================
# SegmentReport
# ============================================================

class SegmentReport:
    """分段分析报告

    按时间频率将 net_value 分段，对每段独立计算指标。

    Args:
        run_id: 回测运行标识
        registry: 指标注册中心
        data: 数据容器 (net_value 必须包含 timestamp 和 value 列)
        freq: 分段频率，"M"=月, "Q"=季, "Y"=年

    Raises:
        ValueError: data 中不包含 net_value 或 net_value 无 timestamp 列时抛出
    """

    def __init__(
        self,
        run_id: str,
        registry: MetricRegistry,
        data: DataProvider,
        freq: str = "M",
    ):
        if "net_value" not in data:
            raise ValueError("DataProvider 必须包含 'net_value' 数据")

        nv_df = data.get("net_value")
        if nv_df is None or "timestamp" not in nv_df.columns:
            raise ValueError("net_value 必须包含 'timestamp' 列")

        self.run_id = run_id
        self._registry = registry
        self._data = data
        self.freq = freq

        # --- 分段 ---
        self._segments: Dict[str, pd.DataFrame] = {}
        self._compute_segments(nv_df)

        # --- 对每个分段计算指标 ---
        self._results: Dict[str, Dict[str, Any]] = {}
        self._compute_all_segments()

    def _compute_segments(self, nv_df: pd.DataFrame) -> None:
        """按频率分段 net_value"""
        df = nv_df.copy()

        # 根据 freq 确定 groupby key
        if self.freq == "M":
            df["segment_key"] = df["timestamp"].dt.to_period("M").astype(str)
        elif self.freq == "Q":
            df["segment_key"] = df["timestamp"].dt.to_period("Q").astype(str)
        elif self.freq == "Y":
            df["segment_key"] = df["timestamp"].dt.to_period("Y").astype(str)
        else:
            raise ValueError(f"不支持的频率 '{self.freq}'，支持: M, Q, Y")

        for label, group in df.groupby("segment_key"):
            segment_nv = group[["value"]].reset_index(drop=True)
            # 将原始 timestamp 保留在时间序列中
            segment_nv["timestamp"] = group["timestamp"].values
            self._segments[label] = segment_nv

    def _compute_all_segments(self) -> None:
        """对每个分段计算所有可用指标"""
        for label, segment_df in self._segments.items():
            self._results[label] = self._compute_segment_metrics(segment_df)

    def _compute_segment_metrics(self, segment_df: pd.DataFrame) -> Dict[str, Any]:
        """对单个分段计算指标"""
        available_names, _ = self._registry.check_availability(
            {"net_value": segment_df}
        )

        results: Dict[str, Any] = {}
        for name in available_names:
            try:
                instance = self._registry.instantiate(name)
                value = instance.compute({"net_value": segment_df})
                results[name] = value
            except Exception:
                GLOG.WARNING(f"SegmentReport: 计算分段指标 '{name}' 失败")
                results[name] = "ERROR"

        return results

    # ============================================================
    # 输出适配
    # ============================================================

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            {segment_label: {metric_name: value, ...}, ...}
        """
        return {
            label: dict(metrics) for label, metrics in self._results.items()
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame

        Returns:
            以分段标签为 index、指标名为列的 DataFrame
        """
        if not self._results:
            return pd.DataFrame()

        df = pd.DataFrame(self._results).T
        df.index.name = "segment"
        return df

    def to_rich(self) -> Table:
        """转换为 Rich Table

        Returns:
            以分段为行、指标为列的 Rich Table
        """
        table = Table(title=f"[Segment] Analysis Report — {self.run_id} (freq={self.freq})")

        # 收集所有指标名
        all_metric_names: List[str] = []
        seen: set = set()
        for metrics in self._results.values():
            for name in metrics:
                if name not in seen:
                    all_metric_names.append(name)
                    seen.add(name)

        # 列定义
        table.add_column("Segment", style="cyan")
        for name in all_metric_names:
            table.add_column(name, style="green")

        # 行数据
        for label, metrics in self._results.items():
            values = []
            for name in all_metric_names:
                val = metrics.get(name, "")
                if isinstance(val, float):
                    values.append(f"{val:.6f}")
                elif isinstance(val, (pd.Series, pd.DataFrame)):
                    values.append(str(type(val).__name__))
                elif val == "":
                    values.append("")
                else:
                    values.append(str(val))
            table.add_row(label, *values)

        return table
