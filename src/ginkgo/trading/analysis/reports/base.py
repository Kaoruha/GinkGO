# Upstream: MetricRegistry, DataProvider, 各层级 Metric 实现
# Downstream: SingleReport, CLI/API/Web UI 消费方
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

from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry


# ============================================================
# 标准数据源分类映射
# ============================================================

# requires 精确匹配 → 对应分类
_STANDARD_CATEGORIES: Dict[tuple, str] = {
    ("net_value",): "summary",
    ("signal",): "signal_analysis",
    ("order",): "order_analysis",
    ("position",): "position_analysis",
}


def _categorize_metric(requires: List[str]) -> Optional[str]:
    """根据 requires 列表确定指标分类。

    规则:
    - requires 精确匹配标准列表 → 对应分类
    - requires 包含多个标准数据源 (跨数据源指标) → summary
    - 其他 (非标准 requires) → None (custom)

    Args:
        requires: 指标的数据依赖列表

    Returns:
        分类名称，None 表示自定义分类
    """
    req_tuple = tuple(sorted(requires))
    if req_tuple in _STANDARD_CATEGORIES:
        return _STANDARD_CATEGORIES[req_tuple]

    # 跨数据源指标：requires 包含多个标准 key
    standard_keys = {item for pair in _STANDARD_CATEGORIES for item in pair}
    if len(req_tuple) > 1 and all(k in standard_keys for k in req_tuple):
        return "summary"

    return None


# ============================================================
# AnalysisReport
# ============================================================

class AnalysisReport:
    """分析报告基类

    在构造时自动完成所有可用指标的计算，
    将结果按类别组织，并提供多种输出适配。

    分类规则:
    - summary: requires=["net_value"] 或跨数据源指标
    - signal_analysis: requires=["signal"]
    - order_analysis: requires=["order"]
    - position_analysis: requires=["position"]
    - custom_metrics: 非标准 requires 的指标 + 未被注册指标消耗的 DataProvider key

    Args:
        run_id: 回测运行标识
        registry: 指标注册中心
        data: 数据容器

    Raises:
        ValueError: data 中不包含 net_value 时抛出
    """

    def __init__(
        self,
        run_id: str,
        registry: MetricRegistry,
        data: DataProvider,
    ):
        # --- 前置校验 ---
        if "net_value" not in data:
            raise ValueError("DataProvider 必须包含 'net_value' 数据")

        self.run_id = run_id
        self._data = data
        self._registry = registry

        # --- 计算所有指标 ---
        available_names, missing_names = registry.check_availability(data)
        available_instances: Dict[str, Any] = {}
        for name in available_names:
            try:
                instance = registry.instantiate(name)
                available_instances[name] = instance
            except Exception:
                available_instances[name] = None

        # --- 按类别组织指标结果 ---
        self.summary: Dict[str, Any] = {}
        self.signal_analysis: Dict[str, Any] = {}
        self.order_analysis: Dict[str, Any] = {}
        self.position_analysis: Dict[str, Any] = {}
        self.custom_metrics: Dict[str, Any] = {}

        # 计算可用指标并分类
        data_dict: Dict[str, pd.DataFrame] = {}
        for key in data.available:
            data_dict[key] = data.get(key)

        consumed_keys: set = set()
        for name, instance in available_instances.items():
            if instance is None:
                continue
            requires = getattr(instance, "requires", [])
            consumed_keys.update(requires)
            category = _categorize_metric(requires)
            try:
                value = instance.compute(data_dict)
            except Exception:
                value = "ERROR"

            if category == "summary":
                self.summary[name] = value
            elif category == "signal_analysis":
                self.signal_analysis[name] = value
            elif category == "order_analysis":
                self.order_analysis[name] = value
            elif category == "position_analysis":
                self.position_analysis[name] = value
            else:
                self.custom_metrics[name] = value

        # 不可用指标 → N/A
        self._na_metrics: Dict[str, str] = {}
        for name in missing_names:
            self._na_metrics[name] = "N/A"

        # 自定义数据：DataProvider 中未被任何注册指标消耗的 key
        all_registered_requires: set = set()
        for name in registry.list_metrics():
            cls = registry.get(name)
            if cls:
                reqs = getattr(cls, "requires", [])
                all_registered_requires.update(reqs)
        for key in data.available:
            if key not in all_registered_requires:
                self.custom_metrics[key] = data.get(key)

        # 原始时间序列
        self.time_series: Dict[str, pd.DataFrame] = dict(data_dict)

    # ============================================================
    # 输出适配
    # ============================================================

    def to_dict(self) -> dict:
        """转换为字典 (API 消费)

        Returns:
            包含所有 section 的扁平字典
        """
        return {
            "run_id": self.run_id,
            "summary": dict(self.summary),
            "signal_analysis": dict(self.signal_analysis),
            "order_analysis": dict(self.order_analysis),
            "position_analysis": dict(self.position_analysis),
            "custom_metrics": self._serialize_custom(),
            "metrics": dict(self._na_metrics),
            "time_series": {
                k: v.to_dict(orient="records") if isinstance(v, pd.DataFrame) else v
                for k, v in self.time_series.items()
            },
        }

    def _serialize_custom(self) -> dict:
        """序列化 custom_metrics 中的 DataFrame"""
        result = {}
        for k, v in self.custom_metrics.items():
            if isinstance(v, pd.DataFrame):
                result[k] = v.to_dict(orient="records")
            else:
                result[k] = v
        return result

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame (Python 消费)

        Returns:
            以指标名为 index、值为 value 列的 DataFrame
        """
        rows = []

        for name, value in self.summary.items():
            rows.append({"section": "summary", "metric": name, "value": value})
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
            Rich Table 实例，包含 metric 和 value 两列
        """
        table = Table(title=f"Analysis Report — {self.run_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        sections = [
            ("Summary", self.summary),
            ("Signal Analysis", self.signal_analysis),
            ("Order Analysis", self.order_analysis),
            ("Position Analysis", self.position_analysis),
        ]

        for section_name, section_data in sections:
            table.add_section()
            table.add_row(f"[bold]{section_name}[/bold]", "")
            if not section_data:
                table.add_row("  (empty)", "")
            for name, value in section_data.items():
                display_value = self._format_value(value)
                table.add_row(f"  {name}", display_value)

        # 不可用指标
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
