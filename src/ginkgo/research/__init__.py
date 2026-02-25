# Upstream: ginkgo.data.cruds, ginkgo.service_hub
# Downstream: ginkgo.trading.strategies, ginkgo.validation
# Role: 因子研究模块 - IC分析、分层、正交化等

"""
Ginkgo Research Module - 因子研究模块

提供因子研究和分析功能:
- ICAnalyzer: IC 分析
- FactorLayering: 因子分层
- FactorOrthogonalizer: 因子正交化
- FactorComparator: 因子对比
- FactorDecayAnalyzer: 衰减分析
- FactorTurnoverAnalyzer: 换手率分析
"""

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # P1 - 核心分析
    "ICAnalyzer",
    "FactorLayering",
    "FactorOrthogonalizer",
    # P1 - 扩展分析
    "FactorComparator",
    "FactorDecayAnalyzer",
    "FactorTurnoverAnalyzer",
    # Container
    "ResearchContainer",
]

# 延迟导入，避免循环依赖
def __getattr__(name: str):
    if name == "ICAnalyzer":
        from ginkgo.research.ic_analysis import ICAnalyzer
        return ICAnalyzer
    elif name == "FactorLayering":
        from ginkgo.research.layering import FactorLayering
        return FactorLayering
    elif name == "FactorOrthogonalizer":
        from ginkgo.research.orthogonalization import FactorOrthogonalizer
        return FactorOrthogonalizer
    elif name == "FactorComparator":
        from ginkgo.research.factor_comparison import FactorComparator
        return FactorComparator
    elif name == "FactorDecayAnalyzer":
        from ginkgo.research.decay_analysis import FactorDecayAnalyzer
        return FactorDecayAnalyzer
    elif name == "FactorTurnoverAnalyzer":
        from ginkgo.research.turnover_analysis import FactorTurnoverAnalyzer
        return FactorTurnoverAnalyzer
    elif name == "ResearchContainer":
        from ginkgo.research.containers import ResearchContainer
        return ResearchContainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
