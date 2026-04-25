# Upstream: MetricRegistry, DataProvider, 各层级 Metric 实现
# Downstream: SingleReport, ComparisonReport, CLI/API/Web UI 消费方
# Role: 分析报告基类 - 构造时自动计算所有可用指标并按类别组织


"""
分析报告基类 (AnalysisReport)

在构造时通过 MetricRegistry 检查数据可用性，
自动计算所有可用的指标，按数据源类别组织结果，
并提供 dict/DataFrame/Rich 三种输出适配。
"""

from typing import Any, Dict, List, Optional

import pandas as pd
from rich.table import Table

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry


# ============================================================
# AnalysisReport
# ============================================================

class AnalysisReport:
    """分析报告基类

    在构造时自动完成所有可用指标的计算，
    将结果按类别组织，并提供多种输出适配。

    分类规则:
    - analyzer_summary: DataProvider 中每个含 "value" 列的 DataFrame 的统计摘要
    - stability_analysis: 名称不以 "ic." 开头的注册指标
    - ic_analysis: 名称以 "ic." 开头的注册指标
    - signal_analysis: signal 数据的计数统计
    - order_analysis: order 数据的计数统计
    - position_analysis: position 数据的计数统计

    Args:
        task_id: 回测运行标识
        registry: 指标注册中心
        data: 数据容器

    Raises:
        ValueError: data 中无任何可用数据时抛出
    """

    def __init__(
        self,
        task_id: str,
        registry: MetricRegistry,
        data: DataProvider,
    ):
        # --- 前置校验 ---
        if len(data.available) == 0:
            raise ValueError("DataProvider 中无任何可用数据")

        self.task_id = task_id
        self._data = data
        self._registry = registry

        # --- 构建数据字典 ---
        data_dict: Dict[str, pd.DataFrame] = {}
        for key in data.available:
            data_dict[key] = data.get(key)

        # --- analyzer_summary: 对每个含 "value" 列的 DataFrame 计算统计量 ---
        self.analyzer_summary: Dict[str, Dict[str, float]] = {}
        for key, df in data_dict.items():
            if isinstance(df, pd.DataFrame) and "value" in df.columns:
                series = df["value"].dropna()
                if len(series) > 0:
                    self.analyzer_summary[key] = {
                        "final": float(series.iloc[-1]),
                        "mean": float(series.mean()),
                        "std": float(series.std()),
                        "min": float(series.min()),
                        "max": float(series.max()),
                    }

        # 向后兼容别名
        self.summary = self.analyzer_summary

        # --- 通过 MetricRegistry 计算已注册指标 ---
        available_names, missing_names = registry.check_availability(data)

        self.stability_analysis: Dict[str, Any] = {}
        self.ic_analysis: Dict[str, Any] = {}

        for name in available_names:
            try:
                # 优先获取实例级注册（参数化指标）
                instance = registry.get_instance(name)
                if instance is None:
                    instance = registry.instantiate(name)
            except Exception:
                GLOG.WARNING(f"指标 '{name}' 实例化失败")
                continue

            try:
                value = instance.compute(data_dict)
            except Exception:
                GLOG.WARNING(f"指标 '{name}' 计算失败")
                value = "ERROR"

            if name.startswith("ic."):
                self.ic_analysis[name] = value
            else:
                self.stability_analysis[name] = value

        # --- signal / order / position 基本计数 ---
        self.signal_analysis: Dict[str, Any] = {}
        self.order_analysis: Dict[str, Any] = {}
        self.position_analysis: Dict[str, Any] = {}

        count_map = {
            "signal": (self.signal_analysis, "signal"),
            "order": (self.order_analysis, "order"),
            "position": (self.position_analysis, "position"),
        }
        for attr_name, (section_dict, data_key) in count_map.items():
            df = data_dict.get(attr_name)
            if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
                section_dict[f"{data_key}_count"] = len(df)

        # --- 不可用指标 ---
        self._na_metrics: Dict[str, str] = {}
        for name in missing_names:
            self._na_metrics[name] = "N/A"

        # --- 原始时间序列 ---
        self.time_series: Dict[str, pd.DataFrame] = dict(data_dict)

    # ============================================================
    # 输出适配
    # ============================================================

    def to_dict(self) -> dict:
        """转换为字典 (API 消费)

        Returns:
            包含所有 section 的字典
        """
        return {
            "task_id": self.task_id,
            "analyzer_summary": {
                k: dict(v) for k, v in self.analyzer_summary.items()
            },
            "stability_analysis": dict(self.stability_analysis),
            "ic_analysis": dict(self.ic_analysis),
            "signal_analysis": dict(self.signal_analysis),
            "order_analysis": dict(self.order_analysis),
            "position_analysis": dict(self.position_analysis),
            "metrics": dict(self._na_metrics),
            "time_series": {
                k: v.to_dict(orient="records") if isinstance(v, pd.DataFrame) else v
                for k, v in self.time_series.items()
            },
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame (Python 消费)

        Returns:
            以 metric 为 index、section 为分组列的 DataFrame
        """
        rows = []

        for analyzer_name, stats in self.analyzer_summary.items():
            for stat_name, value in stats.items():
                rows.append({
                    "section": "analyzer_summary",
                    "metric": f"{analyzer_name}.{stat_name}",
                    "value": value,
                })
        for name, value in self.stability_analysis.items():
            rows.append({"section": "stability_analysis", "metric": name, "value": value})
        for name, value in self.ic_analysis.items():
            rows.append({"section": "ic_analysis", "metric": name, "value": value})
        for name, value in self.signal_analysis.items():
            rows.append({"section": "signal_analysis", "metric": name, "value": value})
        for name, value in self.order_analysis.items():
            rows.append({"section": "order_analysis", "metric": name, "value": value})
        for name, value in self.position_analysis.items():
            rows.append({"section": "position_analysis", "metric": name, "value": value})
        for name, value in self._na_metrics.items():
            rows.append({"section": "unavailable", "metric": name, "value": value})

        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.set_index("metric")
        return df

    def to_rich(self) -> Table:
        """转换为 Rich Table (CLI/TUI 消费)

        Returns:
            Rich Table 实例，包含各分区的指标和值
        """
        table = Table(title=f"Analysis Report — {self.task_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        # Analyzer Summary
        table.add_section()
        table.add_row("[bold]Analyzer Summary[/bold]", "")
        if not self.analyzer_summary:
            table.add_row("  (empty)", "")
        for analyzer_name, stats in self.analyzer_summary.items():
            for stat_name, value in stats.items():
                table.add_row(f"  {analyzer_name}.{stat_name}", self._format_value(value))

        # Stability Analysis（仅非空时显示）
        if self.stability_analysis:
            table.add_section()
            table.add_row("[bold]Stability Analysis[/bold]", "")
            for name, value in self.stability_analysis.items():
                table.add_row(f"  {name}", self._format_value(value))

        # IC Analysis（仅非空时显示）
        if self.ic_analysis:
            table.add_section()
            table.add_row("[bold]IC Analysis[/bold]", "")
            for name, value in self.ic_analysis.items():
                table.add_row(f"  {name}", self._format_value(value))

        # Signal / Order / Position Analysis（始终显示段落标题）
        for section_label, section_data in [
            ("Signal Analysis", self.signal_analysis),
            ("Order Analysis", self.order_analysis),
            ("Position Analysis", self.position_analysis),
        ]:
            table.add_section()
            table.add_row(f"[bold]{section_label}[/bold]", "")
            if not section_data:
                table.add_row("  (empty)", "")
            for name, value in section_data.items():
                table.add_row(f"  {name}", self._format_value(value))

        # 不可用指标（仅非空时显示）
        if self._na_metrics:
            table.add_section()
            table.add_row("[bold]Unavailable[/bold]", "")
            for name, value in self._na_metrics.items():
                table.add_row(f"  {name}", str(value))

        return table

    @staticmethod
    def _format_value(value: Any) -> str:
        """格式化指标值为可显示字符串"""
        if isinstance(value, float):
            return f"{value:.6f}"
        if isinstance(value, pd.Series):
            return f"Series(len={len(value)})"
        if isinstance(value, pd.DataFrame):
            return f"DataFrame({value.shape[0]}x{value.shape[1]})"
        return str(value)
