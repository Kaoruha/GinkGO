"""
Portfolio module tests using pytest framework.
Tests cover BasePortfolio functionality including strategy management,
position management, analyzer integration, and financial operations.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

from ginkgo.libs import GLOG
from ginkgo.libs.data.normalize import datetime_normalize
from ginkgo.trading.entities.order import Order
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.libs.data.math import cal_fee
from ginkgo.enums import (
    DIRECTION_TYPES, FREQUENCY_TYPES, RECORDSTAGE_TYPES,
    ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
)
from ginkgo.trading.engines import BaseEngine, EventEngine
from ginkgo.trading.bases.portfolio_base import PortfolioBase as BasePortfolio
from ginkgo.trading.portfolios import PortfolioT1Backtest
from ginkgo.trading.entities import Position
from ginkgo.trading.events import EventPriceUpdate, EventSignalGeneration
from ginkgo.trading.entities import Signal
from ginkgo.trading.selectors import FixedSelector
from ginkgo.trading.analysis.analyzers import BaseAnalyzer
from ginkgo.trading.entities import Bar
from ginkgo.trading.sizers import BaseSizer, FixedSizer
from ginkgo.trading.risk_management import BaseRiskManagement
from ginkgo.trading.feeders.base_feeder import BaseFeeder


# ========== Fixtures ==========

@pytest.fixture
def portfolio():
    """Create a PortfolioT1Backtest instance for testing."""
    return PortfolioT1Backtest()


@pytest.fixture
def sample_position(portfolio):
    """Create a sample position for testing."""
    return Position(
        portfolio_id=portfolio.portfolio_id,
        engine_id=portfolio.engine_id,
        code="test_code",
        cost=Decimal("10"),
        volume=1000,
        frozen_volume=0,
        frozen_money=Decimal("0"),
        price=Decimal("10"),
        fee=Decimal("0"),
    )


@pytest.fixture
def sample_strategy():
    """Create a sample strategy for testing."""
    return BaseStrategy()


# ========== Construction Tests ==========

class TestPortfolioConstruction:
    """Test portfolio construction and initialization."""

    def test_portfolio_init(self):
        """Test portfolio initialization."""
        p = PortfolioT1Backtest()
        assert p is not None
        assert isinstance(p, BasePortfolio)

    def test_abstract_base_class_contract(self):
        """Test BasePortfolio abstract class contract."""
        # BasePortfolio is abstract, cannot be instantiated directly
        with pytest.raises(TypeError):
            BasePortfolio()

    def test_concrete_implementation_works(self):
        """Test concrete implementation works correctly."""
        portfolio = PortfolioT1Backtest()
        assert portfolio is not None
        assert isinstance(portfolio, BasePortfolio)


# ========== Strategy Management Tests ==========

class TestStrategyManagement:
    """Test strategy addition and management."""

    def test_portfolio_addstrategy(self, portfolio):
        """Test adding strategies to portfolio."""
        s = BaseStrategy()
        portfolio.add_strategy(s)
        assert len(portfolio.strategies) == 1

        s2 = BaseStrategy()
        portfolio.add_strategy(s2)
        assert len(portfolio.strategies) == 2

    @pytest.mark.parametrize("num_strategies", [1, 2, 5, 10])
    def test_add_multiple_strategies(self, portfolio, num_strategies):
        """Test adding multiple strategies."""
        for _ in range(num_strategies):
            portfolio.add_strategy(BaseStrategy())
        assert len(portfolio.strategies) == num_strategies


# ========== Position Management Tests ==========

class TestPositionManagement:
    """Test position management functionality."""

    def test_portfolio_addposition(self, portfolio, sample_position):
        """Test adding position to portfolio."""
        portfolio.add_position(sample_position)
        r = portfolio.positions["test_code"]
        assert r.code == "test_code"
        assert r.price == Decimal("10")
        assert r.cost == Decimal("10")
        assert r.volume == 1000

    def test_portfolio_add_multiple_positions(self, portfolio):
        """Test adding multiple positions."""
        pos1 = Position(
            portfolio_id=portfolio.portfolio_id,
            engine_id=portfolio.engine_id,
            code="test_code",
            cost=Decimal("10"),
            volume=1000,
            frozen_volume=0,
            frozen_money=Decimal("0"),
            price=Decimal("10"),
            fee=Decimal("0"),
        )
        portfolio.add_position(pos1)
        assert len(portfolio.positions) == 1

        pos2 = Position(
            portfolio_id=portfolio.portfolio_id,
            engine_id=portfolio.engine_id,
            code="test_code2",
            cost=Decimal("10"),
            volume=1000,
            frozen_volume=0,
            frozen_money=Decimal("0"),
            price=Decimal("10"),
            fee=Decimal("0"),
        )
        portfolio.add_position(pos2)
        assert len(portfolio.positions) == 2

    @pytest.mark.parametrize("code,volume,price", [
        ("000001.SZ", 1000, Decimal("10.5")),
        ("600000.SH", 500, Decimal("25.8")),
        ("000002.SZ", 2000, Decimal("5.2")),
    ])
    def test_add_position_with_different_params(self, portfolio, code, volume, price):
        """Test adding positions with different parameters."""
        pos = Position(
            portfolio_id=portfolio.portfolio_id,
            engine_id=portfolio.engine_id,
            code=code,
            cost=price,
            volume=volume,
            frozen_volume=0,
            frozen_money=Decimal("0"),
            price=price,
            fee=Decimal("0"),
        )
        portfolio.add_position(pos)
        assert code in portfolio.positions
        assert portfolio.positions[code].volume == volume


# ========== Financial Operations Tests ==========

class TestFinancialOperations:
    """Test portfolio financial operations."""

    def test_portfolio_financial_operations(self, portfolio):
        """Test portfolio cash and fee operations."""
        # Test initial state
        initial_cash = portfolio.cash
        assert initial_cash > 0

        # Test adding cash
        added_cash = Decimal("5000")
        new_cash = portfolio.add_cash(added_cash)
        assert new_cash == initial_cash + added_cash

        # Test adding fee
        fee = Decimal("100")
        total_fee = portfolio.add_fee(fee)
        assert total_fee == fee

    def test_invalid_cash_operation(self, portfolio):
        """Test invalid cash operation logs error."""
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_cash(-1000)
            mock_log.assert_called_with("ERROR", pytest.ANY)

    def test_invalid_fee_operation(self, portfolio):
        """Test invalid fee operation logs error."""
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_fee(-50)
            mock_log.assert_called_with("ERROR", pytest.ANY)


# ========== Analyzer Hook Mechanism Tests ==========

class TestAnalyzerHooks:
    """Test analyzer registration and hook mechanism."""

    def test_analyzer_registration_and_hook_creation(self, portfolio):
        """Test analyzer registration and hook creation."""
        # Create test analyzer
        class TestAnalyzer(BaseAnalyzer):
            def __init__(self, name):
                super().__init__(name)
                self.activation_calls = []
                self.record_calls = []
                self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
                self.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
                self.set_record_stage(RECORDSTAGE_TYPES.ORDERFILLED)

            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                self.activation_calls.append((stage, portfolio_info.copy()))

            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                self.record_calls.append((stage, portfolio_info.copy()))

        analyzer = TestAnalyzer("test_analyzer")

        # Register analyzer
        portfolio.add_analyzer(analyzer)

        # Verify analyzer registration
        assert "test_analyzer" in portfolio.analyzers
        assert portfolio.analyzers["test_analyzer"] == analyzer

        # Verify analyzer properties set
        assert analyzer.portfolio_id == portfolio.portfolio_id
        assert analyzer.engine_id == portfolio.engine_id

        # Verify hooks created
        assert len(portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY]) > 0
        assert len(portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.SIGNALGENERATION]) > 0
        assert len(portfolio._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERFILLED]) > 0

    def test_hook_lambda_closure_fix(self, portfolio):
        """Test hook mechanism lambda closure fix."""
        analyzers = []
        for i in range(3):
            class TestAnalyzer(BaseAnalyzer):
                def __init__(self, name, test_id):
                    super().__init__(name)
                    self.test_id = test_id
                    self.activation_calls = []
                    self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
                    self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)

                def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                    self.activation_calls.append(self.test_id)

                def _do_record(self, stage, portfolio_info, *args, **kwargs):
                    pass

            analyzer = TestAnalyzer(f"analyzer_{i}", i)
            analyzers.append(analyzer)
            portfolio.add_analyzer(analyzer)

        # Execute hooks
        portfolio_info = {"worth": 10000, "cash": 5000}

        for hook_func in portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY]:
            hook_func(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # Verify each analyzer called correctly
        for i, analyzer in enumerate(analyzers):
            assert len(analyzer.activation_calls) == 1
            assert analyzer.activation_calls[0] == i

    def test_analyzer_hook_error_handling(self, portfolio):
        """Test analyzer hook error handling."""
        # Create error analyzer
        class ErrorAnalyzer(BaseAnalyzer):
            def __init__(self, name):
                super().__init__(name)
                self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                raise ValueError("Test error in analyzer")

            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        error_analyzer = ErrorAnalyzer("error_analyzer")
        portfolio._handle_analyzer_error = Mock()

        portfolio.add_analyzer(error_analyzer)

        portfolio_info = {"worth": 10000}

        # Execute hook should handle error
        hook_func = portfolio._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY][0]
        result = hook_func(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # Verify error handled
        assert result is False
        portfolio._handle_analyzer_error.assert_called_once()


# ========== Analyzer Management Tests ==========

class TestAnalyzerManagement:
    """Test analyzer management and retrieval."""

    def test_duplicate_analyzer_registration_prevention(self, portfolio):
        """Test preventing duplicate analyzer registration."""
        class TestAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        analyzer1 = TestAnalyzer("duplicate_name")
        analyzer2 = TestAnalyzer("duplicate_name")

        # First registration should succeed
        portfolio.add_analyzer(analyzer1)
        assert "duplicate_name" in portfolio.analyzers
        assert portfolio.analyzers["duplicate_name"] == analyzer1

        # Second registration should be rejected
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_analyzer(analyzer2)
            mock_log.assert_called_with("WARN", pytest.ANY)

        # Analyzer should still be first one
        assert portfolio.analyzers["duplicate_name"] == analyzer1

    def test_analyzer_retrieval(self, portfolio):
        """Test analyzer retrieval."""
        class TestAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        analyzer = TestAnalyzer("retrieval_test")
        portfolio.add_analyzer(analyzer)

        # Get existing analyzer
        retrieved = portfolio.analyzer("retrieval_test")
        assert retrieved == analyzer

        # Get non-existent analyzer
        with patch.object(portfolio, 'log') as mock_log:
            result = portfolio.analyzer("nonexistent")
            mock_log.assert_called_with("ERROR", pytest.ANY)
            assert result is None

    def test_analyzer_properties_binding(self, portfolio):
        """Test analyzer properties binding."""
        portfolio._engine_id = "test_engine_123"

        class TestAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        analyzer = TestAnalyzer("property_binding_test")

        # Before adding, analyzer shouldn't have these properties
        initial_portfolio_id = getattr(analyzer, 'portfolio_id', None)
        initial_engine_id = getattr(analyzer, 'engine_id', None)

        portfolio.add_analyzer(analyzer)

        # After adding, properties should be set
        assert analyzer.portfolio_id == portfolio.portfolio_id
        assert analyzer.engine_id == portfolio.engine_id


# ========== Portfolio Configuration Tests ==========

class TestPortfolioConfiguration:
    """Test portfolio configuration and validation."""

    def test_portfolio_configuration_validation(self, portfolio):
        """Test portfolio configuration validation."""
        # Without required components should return False
        assert not portfolio.is_all_set()

        # Set required components
        portfolio.bind_sizer(FixedSizer())
        portfolio.bind_selector(FixedSelector())
        portfolio.add_strategy(BaseStrategy())

        # Should now return True
        assert portfolio.is_all_set()


# ========== Engine Integration Tests ==========

class TestEngineIntegration:
    """Test engine binding and event handling."""

    def test_engine_binding_and_event_handling(self, portfolio):
        """Test engine binding and event handling."""
        mock_engine = Mock()
        mock_put_func = Mock()

        # Bind engine
        portfolio.bind_engine(mock_engine)
        portfolio._engine_put = mock_put_func

        # Test event sending
        test_event = Mock()
        portfolio.put(test_event)
        mock_put_func.assert_called_once_with(test_event)

        # Test error handling without engine
        portfolio._engine_put = None
        with patch.object(portfolio, 'log') as mock_log:
            portfolio.put(test_event)
            mock_log.assert_called_with("ERROR", pytest.ANY)


# ========== Edge Cases and Error Handling ==========

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_analyzer_without_activate_method(self, portfolio):
        """Test handling analyzer without activate method."""
        # Create invalid analyzer
        class InvalidAnalyzer:
            def __init__(self, name):
                self.name = name

        invalid_analyzer = InvalidAnalyzer("invalid")

        with patch.object(portfolio, 'log') as mock_log:
            portfolio.add_analyzer(invalid_analyzer)
            mock_log.assert_called_with("WARN", pytest.ANY)

        # Analyzer should not be added
        assert "invalid" not in portfolio.analyzers
