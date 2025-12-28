"""
Core enumerations for the evaluation module.

This module defines the fundamental enums used throughout the evaluation system:
- ComponentType: Types of Ginkgo components that can be evaluated
- EvaluationLevel: Evaluation depth levels (basic, standard, strict)
- EvaluationSeverity: Severity levels for evaluation issues
"""

from enum import Enum
from typing import List


class ComponentType(str, Enum):
    """
    Ginkgo component types supported for evaluation.

    Attributes:
        STRATEGY: Trading strategy components
        SELECTOR: Candidate selector components (future)
        SIZER: Position sizer components (future)
        RISK_MANAGER: Risk management components (future)
    """

    STRATEGY = "strategy"
    SELECTOR = "selector"
    SIZER = "sizer"
    RISK_MANAGER = "risk_manager"

    @classmethod
    def all(cls) -> List["ComponentType"]:
        """Get all component types."""
        return list(cls)

    @classmethod
    def supported(cls) -> List["ComponentType"]:
        """Get currently supported component types for evaluation."""
        return [cls.STRATEGY]

    def is_supported(self) -> bool:
        """Check if this component type is currently supported."""
        return self in self.supported()


class EvaluationLevel(str, Enum):
    """
    Evaluation depth levels.

    Each level includes all checks from previous levels plus additional checks:
    - BASIC: Structural checks (inheritance, required methods)
    - STANDARD: Basic + logical checks (signal fields, time provider)
    - STRICT: Standard + best practice checks (decorators, logging, error handling)

    Attributes:
        BASIC: Basic structural validation only
        STANDARD: Structural + logical validation
        STRICT: Complete validation including best practices
    """

    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"

    @classmethod
    def all(cls) -> List["EvaluationLevel"]:
        """Get all evaluation levels."""
        return list(cls)

    def includes(self, other: "EvaluationLevel") -> bool:
        """
        Check if this level includes all checks from another level.

        Args:
            other: The evaluation level to check against

        Returns:
            True if this level is equal to or higher than the other level
        """
        level_order = {EvaluationLevel.BASIC: 1, EvaluationLevel.STANDARD: 2, EvaluationLevel.STRICT: 3}
        return level_order[self] >= level_order[other]


class EvaluationSeverity(str, Enum):
    """
    Severity levels for evaluation issues.

    Attributes:
        ERROR: Critical issue that must be fixed (validation will fail)
        WARNING: Recommended fix but not blocking (validation may pass)
        INFO: Informative suggestion for improvement
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @classmethod
    def all(cls) -> List["EvaluationSeverity"]:
        """Get all severity levels."""
        return list(cls)

    def blocks_validation(self) -> bool:
        """Check if issues with this severity block validation from passing."""
        return self == EvaluationSeverity.ERROR

    def rank(self) -> int:
        """Get numeric rank for sorting (higher = more severe)."""
        return {EvaluationSeverity.INFO: 1, EvaluationSeverity.WARNING: 2, EvaluationSeverity.ERROR: 3}[self]
