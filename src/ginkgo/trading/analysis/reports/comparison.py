# Upstream: AnalysisReport (base.py), 各层级 Metric 实现
# Downstream: CLI/API/Web UI 消费方
# Role: 多次回测对比报告 — 将多个 AnalysisReport 并排展示


"""
多次回测对比报告 (ComparisonReport)

将多个 AnalysisReport 实例的 summary 指标进行并排对比，
支持 dict/DataFrame/Rich 三种输出格式。
"""

from typing import Any, Dict, List

import pandas as pd
from rich.table import Table

from ginkgo.trading.analysis.reports.base import AnalysisReport


class ComparisonReport:
    """多次回测对比报告

    接收多个 AnalysisReport 实例，按 task_id 组织并排展示。

    Args:
        reports: AnalysisReport 实例列表
    """

    def __init__(self, reports: List[AnalysisReport]):
        self.reports = reports

    def to_dict(self) -> dict:
        """转换为字典，以 task_id 为 key

        Returns:
            {task_id: {summary: {...}, signal_analysis: {...}, ...}, ...}
        """
        result: Dict[str, dict] = {}
        for report in self.reports:
            d = report.to_dict()
            task_id = d.pop("task_id")
            result[task_id] = d
        return result

    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame，以 task_id 为列

        Returns:
            以 metric.section 为 MultiIndex、task_id 为列的 DataFrame
        """
        if not self.reports:
            return pd.DataFrame()

        # 收集所有指标，按 (section, metric) 组织
        all_keys: Dict[tuple, Dict[str, Any]] = {}
        for report in self.reports:
            sections = [
                ("summary", report.summary),
                ("signal_analysis", report.signal_analysis),
                ("order_analysis", report.order_analysis),
                ("position_analysis", report.position_analysis),
            ]
            for section_name, section_data in sections:
                for metric_name, value in section_data.items():
                    key = (section_name, metric_name)
                    if key not in all_keys:
                        all_keys[key] = {}
                    all_keys[key][report.task_id] = value

        if not all_keys:
            return pd.DataFrame()

        # 构建 DataFrame
        df = pd.DataFrame(all_keys).T
        df.index = pd.MultiIndex.from_tuples(df.index, names=["section", "metric"])
        return df

    def to_rich(self) -> Table:
        """转换为 Rich Table

        Returns:
            以 task_id 为列、指标行为内容的 Rich Table
        """
        table = Table(title="[Comparison] Analysis Report")

        # 收集所有 task_id 作为列
        task_ids = [r.task_id for r in self.reports]
        table.add_column("Metric", style="cyan")
        for task_id in task_ids:
            table.add_column(task_id, style="green")

        if not self.reports:
            table.add_row("(no reports)", "")
            return table

        # 收集所有指标 (去重)
        all_metrics: List[tuple] = []
        seen: set = set()
        sections = [
            ("Summary", "summary"),
            ("Signal Analysis", "signal_analysis"),
            ("Order Analysis", "order_analysis"),
            ("Position Analysis", "position_analysis"),
        ]

        for section_label, section_attr in sections:
            for report in self.reports:
                section_data = getattr(report, section_attr, {})
                for name, value in section_data.items():
                    key = (section_label, name)
                    if key not in seen:
                        all_metrics.append(key)
                        seen.add(key)

        # 填充表格
        current_section = None
        for section_label, metric_name in all_metrics:
            if section_label != current_section:
                table.add_section()
                table.add_row(f"[bold]{section_label}[/bold]", *[""] * len(task_ids))
                current_section = section_label

            values = []
            attr_map = {
                "Summary": "summary",
                "Signal Analysis": "signal_analysis",
                "Order Analysis": "order_analysis",
                "Position Analysis": "position_analysis",
            }
            section_attr = attr_map[section_label]
            for report in self.reports:
                data = getattr(report, section_attr, {})
                val = data.get(metric_name, "")
                values.append(AnalysisReport._format_value(val) if not (isinstance(val, str) and val == "") else "")

            table.add_row(f"  {metric_name}", *values)

        return table
