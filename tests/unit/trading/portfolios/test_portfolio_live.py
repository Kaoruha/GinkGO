"""
Tests for PortfolioLive constructor injection of position_writer and redis_writer.

Verifies that PortfolioLive no longer imports CRUDs directly,
and delegates state persistence to injected services.
"""
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, call

import pytest

from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive


@pytest.fixture
def mock_position_writer():
    """Mock for the injected position persistence service."""
    return MagicMock()


@pytest.fixture
def mock_redis_writer():
    """Mock for the injected Redis status service (duck-typed: has set(key, value))."""
    return MagicMock()


@pytest.fixture
def portfolio(mock_position_writer, mock_redis_writer):
    """PortfolioLive with injected dependencies."""
    p = PortfolioLive(
        position_writer=mock_position_writer,
        redis_writer=mock_redis_writer,
        uuid="test-portfolio-001",
        name="TestLive",
    )
    # minimal setup
    p.add_cash(100000)
    return p


class TestConstructorInjection:
    """PortfolioLive accepts services via constructor, not imports."""

    def test_position_writer_stored(self, mock_position_writer, mock_redis_writer):
        p = PortfolioLive(
            position_writer=mock_position_writer,
            redis_writer=mock_redis_writer,
        )
        assert p._position_writer is mock_position_writer

    def test_redis_writer_stored(self, mock_position_writer, mock_redis_writer):
        p = PortfolioLive(
            position_writer=mock_position_writer,
            redis_writer=mock_redis_writer,
        )
        assert p._redis_writer is mock_redis_writer

    def test_no_crud_imports_in_module(self):
        """Module source should not import PositionCRUD or RedisCRUD."""
        import ginkgo.trading.portfolios.portfolio_live as mod
        import importlib

        importlib.reload(mod)
        source = open(mod.__file__).read()
        assert "PositionCRUD" not in source
        assert "RedisCRUD" not in source


class TestSyncStateToDb:
    """sync_state_to_db delegates to injected position_writer."""

    def test_delegates_to_position_writer(self, portfolio, mock_position_writer):
        from ginkgo.entities import Position

        pos = Position(
            portfolio_id=portfolio.uuid,
            engine_id="test-engine",
            task_id="test-task",
            code="000001.SZ",
            cost=Decimal("10.5"),
            volume=100,
            price=Decimal("11.0"),
        )
        portfolio.add_position(pos)

        result = portfolio.sync_state_to_db()

        assert result is True
        mock_position_writer.save_positions.assert_called_once()
        # Verify positions data passed
        args = mock_position_writer.save_positions.call_args
        assert len(args[0][0]) == 1  # list of positions
        assert args[0][0][0].code == "000001.SZ"

    def test_no_positions_still_succeeds(self, portfolio, mock_position_writer):
        result = portfolio.sync_state_to_db()
        assert result is True
        mock_position_writer.save_positions.assert_called_once_with([])

    def test_writer_failure_returns_false(self, portfolio, mock_position_writer):
        from ginkgo.entities import Position

        pos = Position(
            portfolio_id=portfolio.uuid,
            engine_id="test-engine",
            task_id="test-task",
            code="000001.SZ",
            cost=Decimal("10"),
            volume=100,
            price=Decimal("10"),
        )
        portfolio.add_position(pos)

        mock_position_writer.save_positions.side_effect = Exception("DB error")
        result = portfolio.sync_state_to_db()
        assert result is False


class TestSyncStatusToRedis:
    """_sync_status_to_redis delegates to injected redis_writer."""

    def test_delegates_to_redis_writer(self, portfolio, mock_redis_writer):
        portfolio._sync_status_to_redis(PORTFOLIO_RUNSTATE_TYPES.STOPPING)

        mock_redis_writer.set.assert_called_once()
        args = mock_redis_writer.set.call_args
        assert "portfolio:test-portfolio-001:status" == args[0][0]
        assert args[0][1] == PORTFOLIO_RUNSTATE_TYPES.STOPPING.value

    def test_redis_failure_handled(self, portfolio, mock_redis_writer):
        mock_redis_writer.set.side_effect = Exception("Redis down")

        # Should not raise
        portfolio._sync_status_to_redis(PORTFOLIO_RUNSTATE_TYPES.STOPPING)


class TestNoPositionWriter:
    """Without position_writer, sync_state_to_db gracefully handles."""

    def test_sync_without_writer(self, mock_redis_writer):
        p = PortfolioLive(
            redis_writer=mock_redis_writer,
            uuid="test-no-writer",
        )
        p.add_cash(50000)

        result = p.sync_state_to_db()
        # Should gracefully return False or log warning, not crash
        assert result is False

    def test_status_without_redis_writer(self, mock_position_writer):
        p = PortfolioLive(
            position_writer=mock_position_writer,
            uuid="test-no-redis",
        )
        # Should not raise
        p._sync_status_to_redis(PORTFOLIO_RUNSTATE_TYPES.RUNNING)
