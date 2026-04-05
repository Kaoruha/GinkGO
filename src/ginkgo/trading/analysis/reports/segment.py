# Upstream: DataProvider (分析器时间序列数据)
# Downstream: CLI/API/Web UI 消费方
# Role: 分段分析报告 — 按时间频率分段对任意分析器计算基本统计量


"""
分段分析报告 (SegmentReport)

将任意分析器的时间序列按频率 (月/季/年) 分段，
对每个分段独立计算基本统计量 (mean, std, min, max, final)，
支持 dict/DataFrame/Rich 三种输出。
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from rich.table import Table

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider


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

    按时间频率将任意分析器的时间序列分段，对每段独立计算基本统计量。
    不再依赖 MetricRegistry，直接在 value 列上计算。

    Args:
        run_id: 回测运行标识
        data: 数据容器 (DataProvider，每个分析器必须包含 timestamp 和 value 列)
        freq: 分段频率，"M"=月, "Q"=季, "Y"=年
        analyzers: 可选的分析器名称列表，None = 处理 DataProvider 中所有分析器

    Raises:
        ValueError: data 中无任何可用分析器时抛出
    """

    def __init__(
        self,
        run_id: str,
        data: DataProvider,
        freq: str = "M",
        analyzers: Optional[List[str]] = None,
    ):
        if len(data.available) == 0:
            raise ValueError("DataProvider 中无任何可用数据")

        if freq not in _FREQ_LABELS:
            raise ValueError(f"不支持的频率 '{freq}'，支持: M, Q, Y")

        self.run_id = run_id
        self._data = data
        self.freq = freq
        self.analyzers = analyzers

        # --- 分段 ---
        self._results: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._compute_all_segments()

    def _compute_all_segments(self) -> None:
        """对所有分析器按时间分段计算统计量"""
        # 确定要处理的分析器列表
        analyzer_names = self.analyzers or [
            k for k in self._data.available
            if self._data.get(k) is not None
        ]

        for name in analyzer_names:
            df = self._data.get(name)
            if df is None or not isinstance(df, pd.DataFrame) or "value" not in df.columns:
                GLOG.WARNING(f"SegmentReport: 分析器 '{name}' 无可用数据，跳过")
                continue

            if "timestamp" not in df.columns:
                GLOG.WARNING(f"SegmentReport: 分析器 '{name}' 缺少 'timestamp' 列，跳过")
                continue

            self._compute_segments_for_analyzer(name, df)

    def _compute_segments_for_analyzer(
        self, analyzer_name: str, df: pd.DataFrame
    ) -> None:
        """对单个分析器按时间分段并计算统计量"""
        df = df.copy()

        # 根据 freq 确定 segment_key
        df["segment_key"] = df["timestamp"].dt.to_period(self.freq).astype(str)

        for label, group in df.groupby("segment_key"):
            values = group["value"].dropna()
            if len(values) == 0:
                continue

            if label not in self._results:
                self._results[label] = {}

            self._results[label][analyzer_name] = {
                "mean": float(values.mean()),
                "std": float(values.std()),
                "min": float(values.min()),
                "max": float(values.max()),
                "final": float(values.iloc[-1]),
            }

    # ============================================================
    # 输出适配
    # ============================================================

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            {segment_label: {analyzer_name: {mean, std, min, max, final}, ...}, ...}
        """
        return {
            label: {name: dict(stats) for name, stats in analyzers.items()}
            for label, analyzers in self._results.items()
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame

        Returns:
            以分段标签为 index，以 analyzer.stat 为列的 DataFrame
            例如: columns = ["net_value.mean", "net_value.std", "sharpe.mean", ...]
        """
        if not self._results:
            return pd.DataFrame()

        # 构建扁平字典
        flat: Dict[str, Dict[str, float]] = {}
        for label, analyzers in self._results.items():
            row: Dict[str, float] = {}
            for name, stats in analyzers.items():
                for stat_name, value in stats.items():
                    row[f"{name}.{stat_name}"] = value
            flat[label] = row

        df = pd.DataFrame(flat).T
        df.index.name = "segment"
        return df

    def to_rich(self) -> Table:
        """转换为 Rich Table

        Returns:
            以分段为行、每个分析器一列的 Rich Table。
            每个单元格显示 "mean=X, std=Y, final=Z" 格式。
        """
        table = Table(title=f"[Segment] Analysis Report — {self.run_id} (freq={self.freq})")

        # 收集所有分析器名
        all_analyzer_names: List[str] = []
        seen: set = set()
        for analyzers in self._results.values():
            for name in analyzers:
                if name not in seen:
                    all_analyzer_names.append(name)
                    seen.add(name)

        if not all_analyzer_names:
            table.add_column("Segment", style="cyan")
            table.add_row("(无可用数据)", "")
            return table

        # 列定义
        table.add_column("Segment", style="cyan")
        for name in all_analyzer_names:
            table.add_column(name, style="green")

        # 行数据
        for label, analyzers in self._results.items():
            values = []
            for name in all_analyzer_names:
                stats = analyzers.get(name)
                if stats is None:
                    values.append("")
                else:
                    values.append(
                        f"mean={stats['mean']:.4f}, std={stats['std']:.4f}, "
                        f"final={stats['final']:.4f}"
                    )
            table.add_row(label, *values)

        return table
