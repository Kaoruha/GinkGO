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