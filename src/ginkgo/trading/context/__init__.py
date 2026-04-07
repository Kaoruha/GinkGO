# Upstream: BaseEngine, PortfolioBase, 全部ContextMixin组件
# Downstream: context.engine_context, context.portfolio_context
# Role: 上下文管理模块包入口，导出EngineContext引擎级上下文和PortfolioContext组合级上下文，提供分层运行环境信息






"""
Context package for hierarchical context management in Ginkgo trading system.

Provides:
- EngineContext: Engine-level context (engine_id, run_id)
- PortfolioContext: Portfolio-level context (portfolio_id + EngineContext reference)
"""

from ginkgo.trading.context.engine_context import EngineContext
from ginkgo.trading.context.portfolio_context import PortfolioContext

__all__ = ["EngineContext", "PortfolioContext"]
