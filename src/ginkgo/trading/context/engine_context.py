"""
EngineContext - Engine-level context management.

This class is maintained by BaseEngine and shared across all Portfolios.
Provides read-only access to engine_id and run_id.
"""

from typing import Optional


class EngineContext:
    """
    Engine-level context - shared by all Portfolios

    Responsibilities:
    - Store engine_id (read-only, updatable by Engine)
    - Store run_id (read-only, updatable by Engine)
    - Provide read-only property access

    Design:
    - Engine maintains this instance
    - All Portfolios reference the same EngineContext instance
    - Only Engine can update engine_id and run_id
    """

    def __init__(self, engine_id: str):
        """
        Initialize EngineContext

        Args:
            engine_id: Unique engine identifier
        """
        self._engine_id = engine_id
        self._run_id: Optional[str] = None

    @property
    def engine_id(self) -> str:
        """Read-only: Engine ID"""
        return self._engine_id

    @property
    def run_id(self) -> Optional[str]:
        """Read-only: Current run session ID"""
        return self._run_id

    def set_engine_id(self, engine_id: str) -> None:
        """
        Update engine_id (only Engine should call this)

        Args:
            engine_id: New engine identifier
        """
        self._engine_id = engine_id

    def set_run_id(self, run_id: str) -> None:
        """
        Update run_id (only Engine should call this)

        Args:
            run_id: New run session ID
        """
        self._run_id = run_id

    def __repr__(self) -> str:
        return f"EngineContext(engine_id={self._engine_id[:8]}..., run_id={self._run_id[:8] if self._run_id else None}...)"
