"""
Ginkgo Backtest Evaluation Module

This module provides tools for evaluating backtest stability and monitoring live performance.
It includes slice analysis, stability metrics calculation, and deviation detection.
"""

from .backtest_evaluator import BacktestEvaluator
from .slice_period_optimizer import SlicePeriodOptimizer
from .live_deviation_detector import LiveDeviationDetector
from .metric_stability_calculator import MetricStabilityCalculator
from .slice_data_manager import SliceDataManager

__all__ = [
    "BacktestEvaluator",
    "SlicePeriodOptimizer", 
    "LiveDeviationDetector",
    "MetricStabilityCalculator",
    "SliceDataManager"
]