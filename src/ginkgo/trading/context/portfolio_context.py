# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: PortfolioContext组合上下文提供组合状态和配置管理支持交易系统功能支持交易系统功能支持交易系统功能和组件集成提供完整业务支持






"""
PortfolioContext - Portfolio-level context management.

This class is maintained by Portfolio and references EngineContext.
Provides unified access to portfolio_id, engine_id, and run_id.
"""

from typing import Optional
from ginkgo.trading.context.engine_context import EngineContext


class PortfolioContext:
    """
    Portfolio-level context - references EngineContext

    Responsibilities:
    - Store portfolio_id (read-only)
    - Reference EngineContext (shared)
    - Provide unified context access interface

    Design:
    - Portfolio maintains this instance
    - References EngineContext (shared across Portfolios)
    - All read-only properties for safety
    """

    def __init__(self, portfolio_id: str, engine_context: EngineContext):
        """
        Initialize PortfolioContext

        Args:
            portfolio_id: Unique portfolio identifier
            engine_context: Reference to EngineContext (shared)
        """
        self._portfolio_id = portfolio_id
        self._engine_context = engine_context

    @property
    def portfolio_id(self) -> str:
        """Read-only: Portfolio ID"""
        return self._portfolio_id

    @property
    def engine_id(self) -> str:
        """Read-only: Engine ID (from EngineContext)"""
        return self._engine_context.engine_id

    @property
    def run_id(self) -> Optional[str]:
        """Read-only: Run session ID (from EngineContext)"""
        return self._engine_context.run_id

    def __repr__(self) -> str:
        return (f"PortfolioContext(portfolio_id={self._portfolio_id[:8]}..., "
                f"engine_id={self.engine_id[:8]}..., "
                f"run_id={self.run_id[:8] if self.run_id else None}...)")
