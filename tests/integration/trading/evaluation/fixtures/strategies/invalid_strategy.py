"""
Invalid strategy for testing evaluation module.
This strategy has multiple issues that should be detected.
"""

from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.trading.enums import DIRECTION_TYPES
from typing import List, Dict
from ginkgo.trading.events import EventBase


class InvalidTestStrategy:
    """An invalid test strategy - does not inherit from BaseStrategy."""

    def __init__(self):
        # Missing super().__init__() call
        pass

    def cal(self, portfolio_info, event):
        # Missing type hints
        # Returns None instead of List[Signal]
        return None
