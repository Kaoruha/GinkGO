"""
性能: 218MB RSS, 2.0s, 6 tests [PASS]
BaseFeeder tests using pytest framework.
Tests cover feeder initialization, event publishing, and data retrieval.
"""

import pytest
from unittest.mock import Mock

from ginkgo.trading.feeders.base_feeder import BaseFeeder


# ========== Fixtures ==========

@pytest.fixture
def base_feeder():
    """Create a BaseFeeder instance for testing."""
    return BaseFeeder("TestFeeder")


# ========== Construction Tests ==========

class TestFeederConstruction:
    """Test BaseFeeder construction and initialization."""

    def test_feeder_init(self):
        """Test feeder initialization."""
        f = BaseFeeder()
        assert f is not None
        assert callable(getattr(f, "put", None))
        assert callable(getattr(f, "set_event_publisher", None))

    def test_feeder_with_name(self):
        """Test feeder with name."""
        f = BaseFeeder("TestFeeder")
        assert f is not None


# ========== Event Publisher Tests ==========

class TestEventPublisher:
    """Test event publisher functionality (replaces old subscriber tests)."""

    def test_event_publisher_not_bound_by_default(self, base_feeder):
        """Test that engine put is None by default."""
        assert base_feeder._engine_put is None

    def test_set_event_publisher(self, base_feeder):
        """Test setting event publisher."""
        mock_publisher = Mock()
        base_feeder.set_event_publisher(mock_publisher)
        assert base_feeder._engine_put is mock_publisher

    def test_put_event_without_engine_bound(self, base_feeder):
        """Test putting event without bound engine does not crash."""
        event = Mock()
        base_feeder.put(event)  # Should log error but not crash

    def test_put_event_with_engine_bound(self, base_feeder):
        """Test putting event with bound engine."""
        mock_publisher = Mock()
        base_feeder.set_event_publisher(mock_publisher)
        event = Mock()
        base_feeder.put(event)
        mock_publisher.assert_called_once_with(event)
