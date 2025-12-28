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
