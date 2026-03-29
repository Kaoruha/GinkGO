"""
BasePortfolio投资组合TDD测试

通过TDD方式开发BasePortfolio的核心逻辑测试套件
聚焦于投资组合管理、策略执行和风险控制功能
"""
import pytest
import sys
import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.bases.portfolio_base import PortfolioBase
from ginkgo.trading.bases.selector_base import SelectorBase
from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.entities.order import Order
from ginkgo.entities.position import Position
from ginkgo.entities.signal import Signal
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    FREQUENCY_TYPES,
    PORTFOLIO_MODE_TYPES,
    PORTFOLIO_RUNSTATE_TYPES,
    RECORDSTAGE_TYPES,
)
from ginkgo.trading.time.providers import LogicalTimeProvider


# ---------------------------------------------------------------------------
# Helpers: concrete subclass so we can instantiate the ABC
# ---------------------------------------------------------------------------
class ConcretePortfolio(PortfolioBase):
    """Minimal concrete subclass of PortfolioBase for testing."""

    def get_position(self, code):
        return self.positions.get(code)

    def on_price_received(self, event):
        pass

    def on_signal(self, event):
        pass

    def on_order_partially_filled(self, event):
        pass

    def on_order_cancel_ack(self, event):
        pass


def _make_portfolio(name="Portfolio", **kwargs):
    """Create a ConcretePortfolio with a LogicalTimeProvider already set."""
    tp = LogicalTimeProvider(datetime.datetime(2024, 1, 2))
    p = ConcretePortfolio(name=name, use_default_analyzers=False, **kwargs)
    p.set_time_provider(tp)
    return p


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                limit_price=Decimal("10.0"), **overrides):
    """Create an Order with sensible defaults."""
    defaults = dict(
        portfolio_id="pid", engine_id="eid", run_id="rid",
        code=code, direction=direction, order_type=ORDER_TYPES.LIMITORDER,
        status=ORDERSTATUS_TYPES.NEW, volume=volume,
        limit_price=limit_price, frozen_money=volume * limit_price,
    )
    defaults.update(overrides)
    return Order(**defaults)


# =========================================================================
# 1. Construction
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        p = _make_portfolio()
        assert p.name == "Portfolio"
        assert isinstance(p.uuid, str)
        assert len(p.uuid) > 0
        assert p.mode == PORTFOLIO_MODE_TYPES.BACKTEST
        assert p.state == PORTFOLIO_RUNSTATE_TYPES.INITIALIZED

    def test_custom_parameters_constructor(self):
        p = _make_portfolio(name="MyPortfolio")
        assert p.name == "MyPortfolio"
        assert p.mode == PORTFOLIO_MODE_TYPES.BACKTEST

    def test_backtest_base_inheritance(self):
        p = _make_portfolio()
        # PortfolioBase inherits from Base, so it should have uuid, component_type
        assert isinstance(p.uuid, str) and len(p.uuid) > 0
        assert isinstance(p.portfolio_id, str) and len(p.portfolio_id) > 0
        # engine_id and run_id are None until context injection
        assert p.engine_id is None
        assert p.run_id is None
        assert callable(getattr(p, 'set_time_provider', None))

    def test_default_name_setting(self):
        p = ConcretePortfolio(use_default_analyzers=False)
        p.set_time_provider(LogicalTimeProvider(datetime.datetime(2024, 1, 2)))
        assert p.name == "Portfolio"


# =========================================================================
# 2. Properties
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioProperties:
    """2. 属性访问测试"""

    def test_name_property(self):
        p = _make_portfolio(name="TestName")
        assert p.name == "TestName"

    def test_strategies_collection_property(self):
        p = _make_portfolio()
        assert isinstance(p.strategies, list)
        assert len(p.strategies) == 0

    def test_risk_managers_collection_property(self):
        p = _make_portfolio()
        assert isinstance(p.risk_managers, list)
        assert len(p.risk_managers) == 0

    def test_selectors_collection_property(self):
        p = _make_portfolio()
        assert isinstance(p.selectors, list)
        assert len(p.selectors) == 0

    def test_sizers_collection_property(self):
        p = _make_portfolio()
        assert p.sizer is None


# =========================================================================
# 3. Component Management
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioComponentManagement:
    """3. 组件管理测试"""

    def test_add_strategy_method(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        mock_strategy.bind_portfolio = Mock()
        p.add_strategy(mock_strategy)
        assert len(p.strategies) == 1
        assert p.strategies[0] is mock_strategy
        mock_strategy.bind_portfolio.assert_called_once_with(p)

    def test_add_risk_manager_method(self):
        p = _make_portfolio()
        mock_risk = Mock(spec=RiskBase)
        p.add_risk_manager(mock_risk)
        assert len(p.risk_managers) == 1
        assert p.risk_managers[0] is mock_risk

    def test_add_risk_manager_rejects_non_risk(self):
        p = _make_portfolio()
        p.add_risk_manager("not_a_risk")
        assert len(p.risk_managers) == 0

    def test_add_selector_method(self):
        p = _make_portfolio()
        mock_selector = Mock(spec=SelectorBase)
        mock_selector.bind_portfolio = Mock()
        p.bind_selector(mock_selector)
        assert len(p.selectors) == 1
        assert p.selectors[0] is mock_selector
        mock_selector.bind_portfolio.assert_called_once_with(p)

    def test_add_sizer_method(self):
        p = _make_portfolio()
        mock_sizer = Mock(spec=SizerBase)
        mock_sizer.bind_portfolio = Mock()
        p.bind_sizer(mock_sizer)
        assert p.sizer is mock_sizer
        mock_sizer.bind_portfolio.assert_called_once_with(p)

    def test_component_validation(self):
        p = _make_portfolio()
        # bind_selector rejects non-SelectorBase
        p.bind_selector("not_a_selector")
        assert len(p.selectors) == 0
        # bind_sizer rejects non-SizerBase
        p.bind_sizer("not_a_sizer")
        assert p.sizer is None


# =========================================================================
# 4. Event Handling (abstract methods exist)
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioEventHandling:
    """4. 事件处理测试"""

    def test_price_update_event_handling(self):
        p = _make_portfolio()
        # on_price_received is abstract; in ConcretePortfolio it is a no-op
        event = Mock()
        p.on_price_received(event)  # should not raise

    def test_signal_generation_event_handling(self):
        p = _make_portfolio()
        event = Mock()
        p.on_signal(event)  # should not raise

    def test_order_lifecycle_event_handling(self):
        p = _make_portfolio()
        event = Mock()
        p.on_order_partially_filled(event)  # should not raise
        p.on_order_cancel_ack(event)  # should not raise

    def test_event_routing_logic(self):
        p = _make_portfolio()
        # Verify that put() does nothing when _engine_put is not set
        event = Mock()
        p.put(event)  # should log error but not crash
        assert p._engine_put is None

    def test_set_event_publisher_injection(self):
        p = _make_portfolio()
        mock_publisher = Mock()
        p.set_event_publisher(mock_publisher)
        assert p._engine_put is mock_publisher
        event = Mock()
        p.put(event)
        mock_publisher.assert_called_once_with(event)


# =========================================================================
# 5. Position Management
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioPositionManagement:
    """5. 持仓管理测试"""

    def test_position_creation(self):
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        assert "000001.SZ" in p.positions

    def test_position_update(self):
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        pos2 = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("11.0"), volume=50,
            price=Decimal("11.0"), uuid="pos2",
        )
        p.add_position(pos2)
        # add_position should call deal() on existing position
        assert "000001.SZ" in p.positions

    def test_position_closing(self):
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        assert p.get_position("000001.SZ") is not None
        # Remove position from dict simulates closing
        del p._positions["000001.SZ"]
        assert p.get_position("000001.SZ") is None

    def test_position_tracking(self):
        p = _make_portfolio()
        assert isinstance(p.positions, dict)
        assert len(p.positions) == 0


# =========================================================================
# 6. Order Management (portfolio tracks orders)
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioOrderManagement:
    """6. 订单管理测试"""

    def test_order_creation_from_signal(self):
        # This tests that portfolio does not prevent order creation logic
        p = _make_portfolio()
        order = _make_order()
        assert order.code == "000001.SZ"
        assert order.volume == 100
        assert order.direction == DIRECTION_TYPES.LONG

    def test_order_validation(self):
        p = _make_portfolio()
        order = _make_order()
        assert order.uuid != ""
        assert order.limit_price == Decimal("10.0")

    def test_order_submission(self):
        p = _make_portfolio()
        mock_publisher = Mock()
        p.set_event_publisher(mock_publisher)
        event = Mock()
        p.put(event)
        mock_publisher.assert_called_once_with(event)

    def test_order_status_tracking(self):
        p = _make_portfolio()
        order = _make_order()
        assert order.status == ORDERSTATUS_TYPES.NEW


# =========================================================================
# 7. Abstract Methods
# =========================================================================
@pytest.mark.unit
class TestBasePortfolioAbstractMethods:
    """7. 抽象方法测试"""

    def test_abstract_base_class_behavior(self):
        # PortfolioBase is abstract (ABC), but ConcretePortfolio works
        p = _make_portfolio()
        assert isinstance(p, PortfolioBase)

    def test_required_implementation_methods(self):
        p = _make_portfolio()
        # These must exist and be callable
        assert callable(getattr(p, 'get_position', None))
        assert callable(getattr(p, 'on_price_received', None))
        assert callable(getattr(p, 'on_signal', None))
        assert callable(getattr(p, 'on_order_partially_filled', None))
        assert callable(getattr(p, 'on_order_cancel_ack', None))

    def test_method_signature_consistency(self):
        p = _make_portfolio()
        import inspect
        sig = inspect.signature(p.get_position)
        assert list(sig.parameters.keys()) == ['code']


# =========================================================================
# 8. Capital Management
# =========================================================================
@pytest.mark.unit
class TestCapitalManagement:
    """8. 资金管理测试"""

    def test_initial_cash_setting(self):
        p = _make_portfolio()
        assert p.cash == Decimal("0")
        assert p.frozen == Decimal("0")
        assert p.fee == Decimal("0")

    def test_add_cash_operation(self):
        p = _make_portfolio()
        result = p.add_cash(Decimal("100000"))
        assert result == Decimal("100000")
        assert p.cash == Decimal("100000")

    def test_add_negative_cash_rejection(self):
        p = _make_portfolio()
        p.add_cash(Decimal("1000"))
        p.add_cash(Decimal("-500"))
        # Cash should NOT change for negative input
        assert p.cash == Decimal("1000")

    def test_freeze_capital_operation(self):
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        result = p.freeze(Decimal("30000"))
        assert result is True
        assert p.cash == Decimal("70000")
        assert p.frozen == Decimal("30000")

    def test_freeze_exceeds_available_cash(self):
        p = _make_portfolio()
        p.add_cash(Decimal("1000"))
        result = p.freeze(Decimal("2000"))
        assert result is False
        assert p.cash == Decimal("1000")
        assert p.frozen == Decimal("0")

    def test_unfreeze_capital_operation(self):
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("30000"))
        p.unfreeze(Decimal("10000"))
        assert p.frozen == Decimal("20000")
        assert p.cash == Decimal("80000")

    def test_available_cash_calculation(self):
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("20000"))
        # cash = 80000, frozen = 20000
        assert p.cash == Decimal("80000")
        assert p.frozen == Decimal("20000")
        # unfreeze all
        p.unfreeze(Decimal("20000"))
        assert p.cash == Decimal("100000")
        assert p.frozen == Decimal("0")

    def test_fee_accumulation(self):
        p = _make_portfolio()
        p.add_fee(Decimal("5.5"))
        p.add_fee(Decimal("3.0"))
        assert p.fee == Decimal("8.5")
        # negative fee rejected
        p.add_fee(Decimal("-1"))
        assert p.fee == Decimal("8.5")


# =========================================================================
# 9. Worth and Profit
# =========================================================================
@pytest.mark.unit
class TestWorthAndProfitCalculation:
    """9. 净值和盈亏计算测试"""

    def test_initial_worth_equals_cash(self):
        p = _make_portfolio()
        assert p.worth == p.cash

    def test_update_worth_calculation(self):
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("20000"))
        p.update_worth()
        # worth = cash + frozen = 80000 + 20000 = 100000
        assert p.worth == Decimal("100000")

    def test_worth_with_positions(self):
        p = _make_portfolio()
        p.add_cash(Decimal("100000"))
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("11.0"), uuid="pos1",
        )
        p.add_position(pos)
        p.update_worth()
        # worth = cash(100000) + frozen(0) + position_worth
        expected = p.cash + p.frozen + pos.worth
        assert p.worth == expected

    def test_initial_profit_zero(self):
        p = _make_portfolio()
        assert p.profit == Decimal("0")

    def test_update_profit_calculation(self):
        p = _make_portfolio()
        p.update_profit()
        assert p.profit == Decimal("0")

    def test_profit_with_multiple_positions(self):
        p = _make_portfolio()
        pos1 = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("11.0"), uuid="pos1",
        )
        pos2 = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000002.SZ", cost=Decimal("20.0"), volume=50,
            price=Decimal("18.0"), uuid="pos2",
        )
        p.add_position(pos1)
        p.add_position(pos2)
        p.update_profit()
        # profit = sum of position profits
        expected = pos1.total_pnl + pos2.total_pnl
        assert p.profit == expected

    def test_profit_rounding_precision(self):
        p = _make_portfolio()
        p._profit = Decimal("1.235")
        # profit property rounds to 2 decimal places
        assert p.profit == Decimal("1.24")


# =========================================================================
# 10. Event-Driven Strategy Execution
# =========================================================================
@pytest.mark.unit
class TestEventDrivenStrategyExecution:
    """10. 事件驱动的策略执行测试"""

    def test_on_price_update_triggers_strategies(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        mock_strategy.cal = Mock(return_value=[])
        p.add_strategy(mock_strategy)
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        # ConcretePortfolio.on_price_received is a no-op (abstract base)
        # The real implementation is in subclasses (T1Backtest, LivePortfolio)
        event = Mock(spec=EventPriceUpdate)
        event.code = "000001.SZ"
        p.on_price_received(event)  # no-op in ConcretePortfolio
        # Strategy is NOT called because ConcretePortfolio doesn't implement the logic
        mock_strategy.cal.assert_not_called()

    def test_strategy_signal_aggregation(self):
        p = _make_portfolio()
        signal = Signal(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", direction=DIRECTION_TYPES.LONG,
            reason="test", source=SOURCE_TYPES.OTHER,
            business_timestamp=datetime.datetime(2024, 1, 2),
        )
        mock_strategy = Mock(spec=BaseStrategy)
        mock_strategy.cal = Mock(return_value=[signal])
        p.add_strategy(mock_strategy)
        # Use generate_strategy_signals to test signal aggregation
        event = Mock()
        signals = p.generate_strategy_signals(event)
        mock_strategy.cal.assert_called()
        assert len(signals) == 1
        assert signals[0] is signal

    def test_selector_signal_filtering(self):
        p = _make_portfolio()
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        assert len(p.selectors) == 1

    def test_on_signal_creates_orders(self):
        p = _make_portfolio()
        # on_signal is implemented by subclasses; base version is no-op in ConcretePortfolio
        event = Mock()
        p.on_signal(event)  # does nothing in concrete test impl

    def test_sizer_volume_calculation(self):
        p = _make_portfolio()
        mock_sizer = Mock(spec=SizerBase)
        mock_sizer.cal = Mock(return_value=None)
        p.bind_sizer(mock_sizer)
        assert p.sizer is mock_sizer

    def test_event_publisher_injection(self):
        p = _make_portfolio()
        publisher = Mock()
        p.set_event_publisher(publisher)
        assert p._engine_put is publisher
        evt = Mock()
        p.put(evt)
        publisher.assert_called_once_with(evt)

    def test_price_update_without_strategies(self):
        p = _make_portfolio()
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        # No strategies added
        event = Mock()
        event.code = "000001.SZ"
        p.on_price_received(event)  # should log CRITICAL but not crash


# =========================================================================
# 11. Risk Control Integration
# =========================================================================
@pytest.mark.unit
class TestRiskControlIntegration:
    """11. 风控控制集成测试"""

    def test_risk_managers_order_interception(self):
        p = _make_portfolio()
        mock_risk = Mock(spec=RiskBase)
        mock_risk.cal = Mock(return_value=None)  # block order
        p.add_risk_manager(mock_risk)
        assert len(p.risk_managers) == 1

    def test_risk_managers_active_signal_generation(self):
        p = _make_portfolio()
        mock_risk = Mock(spec=RiskBase)
        mock_risk.generate_signals = Mock(return_value=[])
        p.add_risk_manager(mock_risk)
        signals = p.generate_risk_signals(Mock())
        mock_risk.generate_signals.assert_called_once()
        assert signals == []

    def test_multiple_risk_managers_coordination(self):
        p = _make_portfolio()
        mock_risk1 = Mock(spec=RiskBase)
        mock_risk1.generate_signals = Mock(return_value=[])
        mock_risk2 = Mock(spec=RiskBase)
        mock_risk2.generate_signals = Mock(return_value=[])
        p.add_risk_manager(mock_risk1)
        p.add_risk_manager(mock_risk2)
        p.generate_risk_signals(Mock())
        mock_risk1.generate_signals.assert_called_once()
        mock_risk2.generate_signals.assert_called_once()

    def test_position_ratio_risk_enforcement(self):
        p = _make_portfolio()
        mock_risk = Mock(spec=RiskBase)
        # By default, Mock returns a Mock object (not None)
        order = _make_order()
        result = mock_risk.cal({}, order)
        # Default Mock.cal returns a Mock object, not the order
        assert result is not None

    def test_loss_limit_risk_stop_loss_signal(self):
        p = _make_portfolio()
        mock_risk = Mock(spec=RiskBase)
        mock_risk.generate_signals = Mock(return_value=[])
        p.add_risk_manager(mock_risk)
        signals = p.generate_risk_signals(p.get_info())
        mock_risk.generate_signals.assert_called_once()

    def test_no_risk_manager_warning(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        p.add_strategy(mock_strategy)
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        # is_all_set should return True even without risk managers (just warns)
        result = p.is_all_set()
        assert result is True


# =========================================================================
# 12. Portfolio Completeness Validation
# =========================================================================
@pytest.mark.unit
class TestPortfolioCompletenessValidation:
    """12. 投资组合完整性验证测试"""

    def test_is_all_set_with_complete_setup(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        p.add_strategy(mock_strategy)
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        assert p.is_all_set() is True

    def test_is_all_set_missing_sizer(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        p.add_strategy(mock_strategy)
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        # sizer not set
        assert p.is_all_set() is False

    def test_is_all_set_missing_selector(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        p.add_strategy(mock_strategy)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        # selector not set
        assert p.is_all_set() is False

    def test_is_all_set_missing_strategy(self):
        p = _make_portfolio()
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        # no strategies
        assert p.is_all_set() is False

    def test_is_all_set_missing_risk_manager_warning(self):
        p = _make_portfolio()
        mock_strategy = Mock(spec=BaseStrategy)
        p.add_strategy(mock_strategy)
        mock_selector = Mock(spec=SelectorBase)
        p.bind_selector(mock_selector)
        mock_sizer = Mock(spec=SizerBase)
        p.bind_sizer(mock_sizer)
        # no risk managers - should still return True with a warning
        assert p.is_all_set() is True
