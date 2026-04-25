# Upstream: BaseEngine (创建并维护唯一实例)
# Downstream: ContextMixin/PortfolioContext (所有引擎绑定组件读取 engine_id/task_id/source_type)
# Role: 引擎级上下文对象，持有 engine_id、task_id、source_type，由引擎维护，Portfolio 只读共享






"""
EngineContext - Engine-level context management.

This class is maintained by BaseEngine and shared across all Portfolios.
Provides read-only access to engine_id and task_id.
"""

from typing import Optional

from ginkgo.enums import SOURCE_TYPES


class EngineContext:
    """
    Engine-level context - shared by all Portfolios

    Responsibilities:
    - Store engine_id (read-only, updatable by Engine)
    - Store task_id (read-only, updatable by Engine)
    - Store source_type (marks BACKTEST / PAPER_REPLAY / PAPER_LIVE)
    - Provide read-only property access

    Design:
    - Engine maintains this instance
    - All Portfolios reference the same EngineContext instance
    - Only Engine can update engine_id and task_id
    """

    def __init__(self, engine_id: str):
        """
        Initialize EngineContext

        Args:
            engine_id: Unique engine identifier
        """
        self._engine_id = engine_id
        self._task_id: Optional[str] = None
        self._source_type: int = SOURCE_TYPES.OTHER

    @property
    def engine_id(self) -> str:
        """Read-only: Engine ID"""
        return self._engine_id

    @property
    def task_id(self) -> Optional[str]:
        """Read-only: Current run session ID"""
        return self._task_id

    @property
    def source_type(self) -> int:
        """Read-only: Current source type (SOURCE_TYPES enum value)"""
        return self._source_type

    def set_engine_id(self, engine_id: str) -> None:
        """
        Update engine_id (only Engine should call this)

        Args:
            engine_id: New engine identifier
        """
        self._engine_id = engine_id

    def set_task_id(self, task_id: str) -> None:
        """
        Update task_id (only Engine should call this)

        Args:
            task_id: New run session ID
        """
        self._task_id = task_id

    def set_source_type(self, source_type) -> None:
        """
        Update source_type (only Engine should call this)

        Args:
            source_type: SOURCE_TYPES enum value
        """
        self._source_type = source_type

    def __repr__(self) -> str:
        return f"EngineContext(engine_id={self._engine_id[:8]}..., task_id={self._task_id[:8] if self._task_id else None}...)"
