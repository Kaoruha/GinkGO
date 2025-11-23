"""
Trading Framework Interfaces

This module provides interface definitions for the Ginkgo trading framework.
It includes Protocol interfaces for type safety and Mixin classes for
functional enhancement.
"""

from .protocols import (
    IStrategy,
    IRiskManagement,
    IPortfolio,
    IEngine
)

__all__ = [
    "IStrategy",
    "IRiskManagement",
    "IPortfolio",
    "IEngine"
]