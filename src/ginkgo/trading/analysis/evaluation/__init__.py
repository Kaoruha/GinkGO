# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 回测分析评估模块导出评估器/切片数据管理/指标稳定性计算等组件支持交易系统功能和组件集成提供完整业务支持






"""
Ginkgo Backtest Evaluation Module

This module provides tools for evaluating backtest stability and monitoring live performance.
It includes slice analysis, stability metrics calculation, and deviation detection.
"""

from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
from ginkgo.trading.analysis.evaluation.slice_period_optimizer import SlicePeriodOptimizer
from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector
from ginkgo.trading.analysis.evaluation.metric_stability_calculator import MetricStabilityCalculator
from ginkgo.trading.analysis.evaluation.slice_data_manager import SliceDataManager

__all__ = [
    "BacktestEvaluator",
    "SlicePeriodOptimizer", 
    "LiveDeviationDetector",
    "MetricStabilityCalculator",
    "SliceDataManager"
]