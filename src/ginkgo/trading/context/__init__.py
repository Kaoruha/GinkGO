# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 上下文模块公共接口，导出EngineContext引擎上下文、PortfolioContext组合上下文等上下文管理类，提供组件运行环境信息






"""
Context package for hierarchical context management in Ginkgo trading system.

Provides:
- EngineContext: Engine-level context (engine_id, run_id)
- PortfolioContext: Portfolio-level context (portfolio_id + EngineContext reference)
"""

from ginkgo.trading.context.engine_context import EngineContext
from ginkgo.trading.context.portfolio_context import PortfolioContext

__all__ = ["EngineContext", "PortfolioContext"]
