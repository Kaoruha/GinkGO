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


class TestSignalTriggersNotification:
    """#6150: 信号→消息通知链路（半手动实盘核心）。

    处理一个产出订单的信号时，必须触发交易信号通知，让用户收到
    code/direction/volume/reason 并手动执行后回报。
    """

    def _wire_minimal(self, portfolio, order):
        """让 is_all_set() 通过，并让 sizer 产出给定订单。

        直接赋 _sizer 绕开 bind_sizer 的 isinstance 守卫——sizer 类型校验
        是 bind_sizer 的职责，不是 _process_signal 的（测行为不测胶水）。
        """
        sizer = MagicMock()
        sizer.cal.return_value = order
        portfolio._sizer = sizer
        portfolio._selectors = [MagicMock()]  # is_all_set 要求 selectors 非空
        portfolio.add_strategy(MagicMock())  # is_all_set 要求 strategies 非空
        # risk_managers 为空：is_all_set 仅 WARN，放行

    def test_long_signal_fires_trading_signal_notification(self, portfolio):
        """一个产出订单的 LONG 信号，必须触发 notify_trading_signal。"""
        from ginkgo.entities import Order, Signal
        from ginkgo.enums import DIRECTION_TYPES

        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        self._wire_minimal(portfolio, order)

        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=1000,
            reason="golden cross",
        )

        with patch(
            "ginkgo.trading.portfolios.portfolio_live.notify_trading_signal",
            create=True,
        ) as mock_notify:
            portfolio._process_signal(signal)

        mock_notify.assert_called_once()
        args, kwargs = mock_notify.call_args
        passed = list(args) + list(kwargs.values())
        # 信号对象与产出的订单必须传给通知器（深模块接口：传对象，内部抽取字段）
        assert signal in passed, "信号对象必须传给 notify_trading_signal"
        assert order in passed, "产出的订单必须传给 notify_trading_signal"
