# Upstream: AnalysisReport (base.py)
# Downstream: CLI/API/Web UI 消费方
# Role: 单次回测报告 — AnalysisReport 的语义别名


"""
单次回测分析报告 (SingleReport)

AnalysisReport 的轻量子类，专门用于单次回测场景。
添加 report_type 元数据以区分于对比/分段报告。
"""

from typing import Dict, Any, List

import pandas as pd
from rich.table import Table

from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from .base import AnalysisReport


class SingleReport(AnalysisReport):
    """单次回测分析报告

    继承 AnalysisReport 的全部功能，
    添加 report_type 元数据用于区分报告类型。

    Args:
        task_id: 回测运行标识
        registry: 指标注册中心
        data: 数据容器
    """

    report_type: str = "single"

    def __init__(
        self,
        task_id: str,
        registry: MetricRegistry,
        data: DataProvider,
    ):
        super().__init__(task_id=task_id, registry=registry, data=data)

    def to_dict(self) -> dict:
        """转换为字典，附带 report_type 元数据"""
        d = super().to_dict()
        d["report_type"] = self.report_type
        return d

    def to_rich(self) -> Table:
        """转换为 Rich Table，标题标注 [Single]"""
        table = super().to_rich()
        table.title = f"[Single] Analysis Report — {self.task_id}"
        return table
