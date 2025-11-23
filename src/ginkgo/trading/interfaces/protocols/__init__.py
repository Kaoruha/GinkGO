"""
Trading Framework Protocol Interfaces

This module provides Protocol interfaces for the Ginkgo trading framework components.
These interfaces define contracts that ensure type safety and consistent behavior
across different implementations of strategies, risk management systems,
portfolios, and backtest engines.
"""

from .strategy import IStrategy
from .risk_management import IRiskManagement
from .portfolio import IPortfolio
from .engine import IEngine

__all__ = [
    "IStrategy",
    "IRiskManagement",
    "IPortfolio",
    "IEngine"
]