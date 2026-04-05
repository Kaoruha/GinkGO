# Upstream: MetricRegistry, DataProvider, 各层级 Metric 实现
# Downstream: CLI/API/Web UI 消费方
# Role: 滚动窗口分析报告 — 在滑动窗口上计算指标


"""
滚动窗口分析报告 (RollingReport)

对 net_value 时间序列应用滑动窗口，
在每个窗口位置独立计算组合指标。
"""

from typing import Any, Dict, List

import pandas as pd
from rich.table import Table

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.reports.base import AnalysisReport


# ============================================================
# RollingReport
# ============================================================

class RollingReport:
    """滚动窗口分析报告

    对 net_value 时间序列应用滑动窗口，在每个窗口位置计算指标。

    Args:
        run_id: 回测运行标识
        registry: 指标注册中心
        data: 数据容器 (net_value 必须包含 timestamp 和 value 列)
        window: 窗口大小 (天数)

    Raises:
        ValueError: data 中不包含 net_value 或 net_value 无 timestamp 列时抛出
    """

    def __init__(
        self,
        run_id: str,
        registry: MetricRegistry,
        data: DataProvider,
        window: int = 60,
    ):
        if "net_value" not in data:
            raise ValueError("DataProvider 必须包含 'net_value' 数据")

        nv_df = data.get("net_value")
        if nv_df is None or "timestamp" not in nv_df.columns:
            raise ValueError("net_value 必须包含 'timestamp' 列")

        self.run_id = run_id
        self._registry = registry
        self._data = data
        self.window = window

        # --- 滚动窗口计算 ---
        self._results: Dict[str, Dict[str, Any]] = {}
        self._compute_rolling(nv_df)

    def _compute_rolling(self, nv_df: pd.DataFrame) -> None:
        """在滑动窗口上计算指标"""
        total_len = len(nv_df)
        if total_len < self.window:
            return

        step = self.window  # 非重叠窗口

        for start in range(0, total_len - self.window + 1, step):
            window_df = nv_df.iloc[start: start + self.window].copy()
            window_df = window_df[["value", "timestamp"]].reset_index(drop=True)

            # 窗口起始日期作为 key
            start_date = str(nv_df.iloc[start]["timestamp"].date())

            # 检查指标可用性并计算
            available_names, _ = self._registry.check_availability(
                {"net_value": window_df}
            )

            metrics: Dict[str, Any] = {}
            for name in available_names:
                try:
                    instance = self._registry.instantiate(name)
                    value = instance.compute({"net_value": window_df})
                    metrics[name] = value
                except Exception:
                    GLOG.WARNING(f"RollingReport: 计算滚动指标 '{name}' 失败")
                    metrics[name] = "ERROR"

            self._results[start_date] = metrics

    # ============================================================
    # 输出适配
    # ============================================================

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            {window_start_date: {metric_name: value, ...}, ...}
        """
        return {
            date: dict(metrics) for date, metrics in self._results.items()
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame

        Returns:
            以窗口起始日期为 index、指标名为列的 DataFrame
        """
        if not self._results:
            return pd.DataFrame()

        df = pd.DataFrame(self._results).T
        df.index.name = "window_start"
        return df

    def to_rich(self) -> Table:
        """转换为 Rich Table

        Returns:
            以窗口起始日期为行、指标为列的 Rich Table
        """
        table = Table(title=f"[Rolling] Analysis Report — {self.run_id} (window={self.window})")

        # 收集所有指标名
        all_metric_names: List[str] = []
        seen: set = set()
        for metrics in self._results.values():
            for name in metrics:
                if name not in seen:
                    all_metric_names.append(name)
                    seen.add(name)

        # 列定义
        table.add_column("Window Start", style="cyan")
        for name in all_metric_names:
            table.add_column(name, style="green")

        # 行数据
        for date_label, metrics in self._results.items():
            values = []
            for name in all_metric_names:
                val = metrics.get(name, "")
                if isinstance(val, float):
                    values.append(f"{val:.6f}")
                elif val == "":
                    values.append("")
                else:
                    values.append(str(val))
            table.add_row(date_label, *values)

        return table
