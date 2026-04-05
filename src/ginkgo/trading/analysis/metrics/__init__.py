# Upstream: AnalysisEngine, 分析报告模块
# Downstream: 具体指标实现 (Portfolio/Position/Signal/Order 层级)
# Role: 分析指标模块导出 Metric Protocol、DataProvider、MetricRegistry


"""
分析指标模块 (Metrics Module)

提供统一的指标定义协议、数据容器和注册中心。
"""

from .base import Metric, DataProvider, MetricRegistry

__all__ = [
    "Metric",
    "DataProvider",
    "MetricRegistry",
]
