"""
Tests for strategy parameter validation.

Verifies that validate_parameters catches invalid params at binding time
instead of silently accepting them and failing at runtime.
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy


# ===========================================================================
# Tracer bullet: RandomSignalStrategy parameter validation
# ===========================================================================


class TestRandomSignalValidation:
    """Verify RandomSignalStrategy.validate_parameters rejects invalid inputs."""

    def test_rejects_negative_buy_probability(self):
        strategy = RandomSignalStrategy()
        result = strategy.validate_parameters({
            "buy_probability": -0.5,
            "sell_probability": 0.3,
        })
        assert result is False

    def test_rejects_buy_probability_above_one(self):
        strategy = RandomSignalStrategy()
        result = strategy.validate_parameters({
            "buy_probability": 1.5,
            "sell_probability": 0.3,
        })
        assert result is False

    def test_rejects_negative_sell_probability(self):
        strategy = RandomSignalStrategy()
        result = strategy.validate_parameters({
            "buy_probability": 0.3,
            "sell_probability": -0.1,
        })
        assert result is False

    def test_accepts_valid_probabilities(self):
        strategy = RandomSignalStrategy()
        result = strategy.validate_parameters({
            "buy_probability": 0.3,
            "sell_probability": 0.3,
        })
        assert result is True

    def test_accepts_default_params(self):
        strategy = RandomSignalStrategy()
        result = strategy.validate_parameters({})
        assert result is True

    def test_rejects_non_numeric_probability(self):
        strategy = RandomSignalStrategy()
        result = strategy.validate_parameters({
            "buy_probability": "not_a_number",
        })
        assert result is False


# ===========================================================================
# Binding-time validation: ComponentLoader calls validate_parameters
# ===========================================================================


class TestBindingTimeValidation:
    """Verify validate_parameters is callable and usable for pre-instantiation checks."""

    def test_validate_before_instantiate_rejects_invalid(self):
        """Caller can use validate_parameters to check params before constructing."""
        strategy = RandomSignalStrategy()
        raw_params = {"buy_probability": "not_a_number", "sell_probability": 0.3}
        assert strategy.validate_parameters(raw_params) is False

    def test_validate_before_instantiate_accepts_valid(self):
        strategy = RandomSignalStrategy()
        raw_params = {"buy_probability": 0.5, "sell_probability": 0.2}
        assert strategy.validate_parameters(raw_params) is True

    def test_validate_with_string_numeric(self):
        """String numerics like '0.3' should be accepted (DB stores as strings)."""
        strategy = RandomSignalStrategy()
        raw_params = {"buy_probability": "0.3", "sell_probability": "0.2"}
        assert strategy.validate_parameters(raw_params) is True
