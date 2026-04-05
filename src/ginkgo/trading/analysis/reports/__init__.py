# Upstream: AnalysisEngine, MetricRegistry, DataProvider
# Downstream: CLI/API/Web UI 消费方
# Role: 分析报告模块导出 AnalysisReport, SingleReport, ComparisonReport, SegmentReport, RollingReport


"""
分析报告模块 (Reports Module)

提供统一的报告生成和输出适配，支持 dict/DataFrame/Rich 三种消费方式。
包含单次报告、对比报告、分段报告和滚动窗口报告。
"""

from .base import AnalysisReport
from .single import SingleReport
from .comparison import ComparisonReport
from .segment import SegmentReport
from .rolling import RollingReport

__all__ = [
    "AnalysisReport",
    "SingleReport",
    "ComparisonReport",
    "SegmentReport",
    "RollingReport",
]
