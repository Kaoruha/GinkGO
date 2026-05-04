# Upstream: DataProvider (分析器时间序列数据)
# Downstream: CLI/API/Web UI 消费方
# Role: 滚动窗口分析报告 — 在滑动窗口上对任意分析器计算基本统计量


"""
滚动窗口分析报告 (RollingReport)

对任意分析器的时间序列应用滑动窗口，
在每个窗口位置独立计算基本统计量 (mean, std, min, max, final)。
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from rich.table import Table

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider


# ============================================================
# RollingReport
# ============================================================

class RollingReport:
    """滚动窗口分析报告

    对任意分析器的时间序列应用滑动窗口，在每个窗口位置计算基本统计量。
    不再依赖 MetricRegistry，直接在 value 列上计算。

    Args:
        task_id: 回测运行标识
        data: 数据容器 (DataProvider，每个分析器必须包含 timestamp 和 value 列)
        window: 窗口大小 (天数)
        step: 滑动步长 (默认 1 = 真正的滑动窗口; 设为 window 则退化为滚动窗口)
        analyzers: 可选的分析器名称列表，None = 处理 DataProvider 中所有分析器

    Raises:
        ValueError: data 中无任何可用分析器时抛出
    """

    def __init__(
        self,
        task_id: str,
        data: DataProvider,
        window: int = 60,
        step: int = 1,
        analyzers: Optional[List[str]] = None,
    ):
        if len(data.available) == 0:
            raise ValueError("DataProvider 中无任何可用数据")

        self.task_id = task_id
        self._data = data
        self.window = window
        self.step = step
        self.analyzers = analyzers

        # --- 滚动窗口计算 ---
        self._results: Dict[str, Dict[str, Dict[str, float]]] = {}
        self._compute_rolling()

    def _compute_rolling(self) -> None:
        """在滑动窗口上对每个分析器计算基本统计量"""
        # 确定要处理的分析器列表
        analyzer_names = self.analyzers or [
            k for k in self._data.available
            if self._data.get(k) is not None
        ]

        for name in analyzer_names:
            df = self._data.get(name)
            if df is None or not isinstance(df, pd.DataFrame) or "value" not in df.columns:
                GLOG.WARNING(f"RollingReport: 分析器 '{name}' 无可用数据，跳过")
                continue

            if "timestamp" not in df.columns:
                GLOG.WARNING(f"RollingReport: 分析器 '{name}' 缺少 'timestamp' 列，跳过")
                continue

            total_len = len(df)
            if total_len < self.window:
                GLOG.WARNING(
                    f"RollingReport: 分析器 '{name}' 数据长度 ({total_len}) "
                    f"小于窗口大小 ({self.window})，跳过"
                )
                continue

            for start in range(0, total_len - self.window + 1, self.step):
                window_df = df.iloc[start: start + self.window]
                values = window_df["value"].dropna()
                if len(values) == 0:
                    continue

                start_date = str(df.iloc[start]["timestamp"].date())

                if start_date not in self._results:
                    self._results[start_date] = {}

                self._results[start_date][name] = {
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
            {window_start_date: {analyzer_name: {mean, std, min, max, final}, ...}, ...}
        """
        return {
            date: {name: dict(stats) for name, stats in analyzers.items()}
            for date, analyzers in self._results.items()
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame

        Returns:
            以窗口起始日期为 index，以 analyzer.stat 为列的 DataFrame
            例如: columns = ["net_value.mean", "net_value.std", "sharpe.mean", ...]
        """
        if not self._results:
            return pd.DataFrame()

        # 构建扁平字典
        flat: Dict[str, Dict[str, float]] = {}
        for date, analyzers in self._results.items():
            row: Dict[str, float] = {}
            for name, stats in analyzers.items():
                for stat_name, value in stats.items():
                    row[f"{name}.{stat_name}"] = value
            flat[date] = row

        df = pd.DataFrame(flat).T
        df.index.name = "window_start"
        return df

    def to_rich(self) -> Table:
        """转换为 Rich Table

        Returns:
            以窗口起始日期为行、每个分析器一列的 Rich Table。
            每个单元格显示 "mean=X, std=Y, final=Z" 格式。
        """
        table = Table(title=f"[Rolling] Analysis Report — {self.task_id} (window={self.window})")

        # 收集所有分析器名
        all_analyzer_names: List[str] = []
        seen: set = set()
        for analyzers in self._results.values():
            for name in analyzers:
                if name not in seen:
                    all_analyzer_names.append(name)
                    seen.add(name)

        if not all_analyzer_names:
            table.add_column("Window Start", style="cyan")
            table.add_row("(无可用数据)", "")
            return table

        # 列定义
        table.add_column("Window Start", style="cyan")
        for name in all_analyzer_names:
            table.add_column(name, style="green")

        # 行数据
        for date_label, analyzers in self._results.items():
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
            table.add_row(date_label, *values)

        return table
