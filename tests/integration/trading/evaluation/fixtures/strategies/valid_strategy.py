"""
Valid strategy for testing evaluation module.
"""

from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES
from typing import List, Dict
from ginkgo.trading.events import EventBase


class ValidTestStrategy(BaseStrategy):
    """A valid test strategy that should pass all evaluation checks."""

    __abstract__ = False

    def __init__(self):
        super().__init__()

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        Calculate trading signals.

        Args:
            portfolio_info: Portfolio information
            event: Price update event

        Returns:
            List of signals (empty for this test strategy)
        """
        return []
