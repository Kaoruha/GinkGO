# Upstream: AnalysisEngine, MetricRegistry, DataProvider
# Downstream: CLI/API/Web UI 消费方
# Role: 分析报告模块导出 AnalysisReport, SingleReport


"""
分析报告模块 (Reports Module)

提供统一的报告生成和输出适配，支持 dict/DataFrame/Rich 三种消费方式。
"""

from .base import AnalysisReport
from .single import SingleReport

__all__ = [
    "AnalysisReport",
    "SingleReport",
]
