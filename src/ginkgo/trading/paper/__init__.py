# Upstream: ginkgo.data.cruds, ginkgo.trading.engines
# Downstream: ginkgo.client, ginkgo.trading.comparison
# Role: Paper Trading 模块 - 滑点模型（旧版 PaperTradingEngine 已移除，使用 PaperTradingWorker）

"""
Ginkgo Paper Trading Module - Paper Trading 模块

提供 Paper Trading 相关组件:
- SlippageModel: 滑点模型基类
- FixedSlippage: 固定滑点
- PercentageSlippage: 百分比滑点
- NoSlippage: 无滑点

注意: 旧版 PaperTradingEngine 已废弃移除，请使用 PaperTradingWorker（基于 TimeControlledEventEngine）。
"""

__version__ = "0.2.0"
__all__ = [
    "__version__",
    "SlippageModel",
    "FixedSlippage",
    "PercentageSlippage",
    "NoSlippage",
]

def __getattr__(name: str):
    if name == "SlippageModel":
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
