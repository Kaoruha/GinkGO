# Upstream: PaperTradingWorker, 回测完成后评估, 偏差检测链路
# Downstream: BacktestEvaluator, DeviationChecker, SlicePeriodOptimizer, LiveDeviationDetector, MetricStabilityCalculator, SliceDataManager
# Role: 评估工具包导出 — 回测评估/切片周期优化/偏差检测/指标稳定性计算/切片数据管理






"""
Ginkgo Backtest Evaluation Module

This module provides tools for evaluating backtest stability and monitoring live performance.
It includes slice analysis, stability metrics calculation, and deviation detection.
"""

from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker
from ginkgo.trading.analysis.evaluation.slice_period_optimizer import SlicePeriodOptimizer
from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector
from ginkgo.trading.analysis.evaluation.metric_stability_calculator import MetricStabilityCalculator
from ginkgo.trading.analysis.evaluation.slice_data_manager import SliceDataManager

__all__ = [
    "BacktestEvaluator",
    "DeviationChecker",
    "SlicePeriodOptimizer",
    "LiveDeviationDetector",
    "MetricStabilityCalculator",
    "SliceDataManager",
]
