# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role:   Init  模块提供EvaluationAnalyzers评估分析器模块提供分析器功能支持代码分析功能支持回测评估和代码验证






"""
Static and runtime analyzers for component evaluation.

This package contains analyzer implementations:
- ASTAnalyzer: Static analysis using Python AST module
- RuntimeAnalyzer: Runtime inspection using inspect module
- SignalTracer: Runtime signal generation tracking
"""

from ginkgo.trading.evaluation.analyzers.runtime_analyzer import (
    AdapterFactory,
    BarDataAdapter,
    DataSourceAdapter,
    signal_tracer,
    SignalTracer,
    TickDataAdapter,
)

__all__ = [
    "DataSourceAdapter",
    "BarDataAdapter",
    "TickDataAdapter",
    "AdapterFactory",
    "SignalTracer",
    "signal_tracer",
]
