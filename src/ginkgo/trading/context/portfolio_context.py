# Upstream: PortfolioBase, 分析器、策略等组合内组件
# Downstream: context.engine_context
# Role: 组合级上下文管理，持有portfolio_id并引用EngineContext，统一提供portfolio_id/engine_id/task_id只读访问






"""
PortfolioContext - Portfolio-level context management.

This class is maintained by Portfolio and references EngineContext.
Provides unified access to portfolio_id, engine_id, and task_id.
"""

from typing import Optional
from ginkgo.trading.context.engine_context import EngineContext


class PortfolioContext:
    """
    Portfolio-level context - references EngineContext

    Responsibilities:
    - Store portfolio_id (read-only)
    - Reference EngineContext (shared)
    - Auto-proxy all EngineContext attributes via __getattr__

    Design:
    - Portfolio maintains this instance
    - References EngineContext (shared across Portfolios)
    - Only portfolio_id is defined locally; everything else falls through to EngineContext
    """

    def __init__(self, portfolio_id: str, engine_context: EngineContext):
        self._portfolio_id = portfolio_id
        self._engine_context = engine_context

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def __getattr__(self, name):
        """Auto-proxy undefined attributes to EngineContext"""
        return getattr(self._engine_context, name)

    def __repr__(self) -> str:
        return (f"PortfolioContext(portfolio_id={self._portfolio_id[:8]}..., "
                f"engine_id={self.engine_id[:8]}..., "
                f"task_id={self.task_id[:8] if self.task_id else None}...)")

