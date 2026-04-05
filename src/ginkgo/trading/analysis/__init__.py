# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System, CLI/API/Web UI
# Role: 分析模块统一导出 — 分析器/指标/报告/引擎，为回测系统提供完整分析评估能力


"""
Analysis Module - 分析评估层

Ginkgo Backtest Framework 分析评估层模块

- analyzers/: 性能分析器 (BaseAnalyzer 及具体实现)
- metrics/: 分析指标 (Metric Protocol, DataProvider, MetricRegistry)
- reports/: 分析报告 (Single/Comparison/Segment/Rolling)
- engine/: 分析引擎统一入口 (AnalysisEngine)
- evaluation/: 评估工具
- plots/: 可视化图表 (可选)
"""

# === 分析器模块 ===
from ginkgo.trading.analysis.analyzers import *

# === 结果汇总器 ===
from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

# === 指标模块 ===
from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry

# === 报告模块 ===
from ginkgo.trading.analysis.reports import (
    AnalysisReport, SingleReport, ComparisonReport, SegmentReport, RollingReport,
)

# === 分析引擎 ===
from ginkgo.trading.analysis.engine import AnalysisEngine

# === 可视化模块 (可选) ===
try:
    from ginkgo.trading.analysis.plots import *
except ImportError:
    # 可视化模块是可选的，导入失败时跳过
    pass

__all__ = [
    # 分析器基类和实现
    "BaseAnalyzer",
    "Profit", "NetValue", "MaxDrawdown", "SharpeRatio",
    "HoldPCT", "SignalCount",
    "AnnualizedReturn", "OrderCount",

    # 新增分析器
    "CalmarRatio", "SortinoRatio", "Volatility", "WinRate",
    "ConsecutivePnL", "UnderwaterTime", "VarCVar", "SkewKurtosis",

    # 配置
    "BASIC_ANALYZERS",

    # 结果汇总
    "BacktestResultAggregator",

    # 指标基础设施
    "Metric", "DataProvider", "MetricRegistry",

    # 报告
    "AnalysisReport", "SingleReport", "ComparisonReport",
    "SegmentReport", "RollingReport",

    # 分析引擎
    "AnalysisEngine",
]
