# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 分析模块导出基类/年化收益/夏普比率/最大回撤/波动率等分析器支持交易系统功能和组件集成提供完整业务支持






"""
Analysis Module - 分析评估层

Ginkgo Backtest Framework 分析评估层模块

- analyzers/: 性能分析器
- evaluation/: 评估工具
- plots/: 可视化图表

统一的分析评估接口和实现
"""

# === 分析器模块 ===
from ginkgo.trading.analysis.analyzers import *

# === 可视化模块 ===
try:
    from ginkgo.trading.analysis.plots import *
except ImportError:
    # 可视化模块是可选的，导入失败时跳过
    pass

__all__ = [
    # 分析器基类和实现
    "BaseAnalyzer", "AnalyzerBase", 
    "Profit", "NetValue", "MaxDrawdown", "SharpeRatio", 
    "HoldPct", "SignalCount",
    
    # 新增分析器
    "CalmarRatio", "SortinoRatio", "Volatility", "WinRate",
    "ConsecutivePnL", "UnderwaterTime", "VarCVar", "SkewKurtosis",
]