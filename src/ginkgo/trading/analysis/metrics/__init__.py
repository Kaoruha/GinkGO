# Upstream: AnalysisEngine, 分析报告模块
# Downstream: 具体指标实现 (analyzer_metrics 等参数化指标)
# Role: 分析指标模块导出 Metric Protocol、DataProvider、MetricRegistry、事后分析指标


"""
分析指标模块 (Metrics Module)

提供统一的指标定义协议、数据容器、注册中心和事后分析指标。
"""

from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry
from ginkgo.trading.analysis.metrics.analyzer_metrics import RollingMean, RollingStd, CV, IC

__all__ = [
    "Metric", "DataProvider", "MetricRegistry",
    "RollingMean", "RollingStd", "CV", "IC",
]
