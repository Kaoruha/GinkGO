"""
Context package for hierarchical context management in Ginkgo trading system.

Provides:
- EngineContext: Engine-level context (engine_id, run_id)
- PortfolioContext: Portfolio-level context (portfolio_id + EngineContext reference)
"""

from ginkgo.trading.context.engine_context import EngineContext
from ginkgo.trading.context.portfolio_context import PortfolioContext

__all__ = ["EngineContext", "PortfolioContext"]
