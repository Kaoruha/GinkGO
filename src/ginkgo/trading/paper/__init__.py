# Upstream: ginkgo.data.cruds, ginkgo.trading.engines, ginkgo.service_hub
# Downstream: ginkgo.client, ginkgo.trading.comparison
# Role: Paper Trading 模块 - 实盘数据模拟交易

"""
Ginkgo Paper Trading Module - Paper Trading 模块

提供 Paper Trading 功能:
- PaperTradingEngine: Paper Trading 引擎
- SlippageModel: 滑点模型基类
- FixedSlippage: 固定滑点
- PercentageSlippage: 百分比滑点
- NoSlippage: 无滑点
"""

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # P0 - Paper Trading
    "PaperTradingEngine",
    # 滑点模型
    "SlippageModel",
    "FixedSlippage",
    "PercentageSlippage",
    "NoSlippage",
    # Container
    "PaperContainer",
    # Data models
    "PaperTradingState",
    "PaperTradingSignal",
]

# 延迟导入
def __getattr__(name: str):
    if name == "PaperTradingEngine":
        from ginkgo.trading.paper.paper_engine import PaperTradingEngine
        return PaperTradingEngine
    elif name == "SlippageModel":
        from ginkgo.trading.paper.slippage_models import SlippageModel
        return SlippageModel
    elif name == "FixedSlippage":
        from ginkgo.trading.paper.slippage_models import FixedSlippage
        return FixedSlippage
    elif name == "PercentageSlippage":
        from ginkgo.trading.paper.slippage_models import PercentageSlippage
        return PercentageSlippage
    elif name == "NoSlippage":
        from ginkgo.trading.paper.slippage_models import NoSlippage
        return NoSlippage
    elif name == "PaperContainer":
        from ginkgo.trading.paper.containers import PaperContainer
        return PaperContainer
    elif name == "PaperTradingState":
        from ginkgo.trading.paper.models import PaperTradingState
        return PaperTradingState
    elif name == "PaperTradingSignal":
        from ginkgo.trading.paper.models import PaperTradingSignal
        return PaperTradingSignal
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
