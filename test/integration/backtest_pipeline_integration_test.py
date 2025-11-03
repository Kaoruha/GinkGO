"""
End-to-end backtest pipeline integration tests.

These tests exercise the engine assembly service with lightweight stubs to
verify that a price update flows through selector → strategy → sizer → risk
manager → broker matchmaking while analyzers are invoked.
"""

from __future__ import annotations

import datetime
from typing import Any, Callable, Dict, List, Optional

from ginkgo.enums import (
    DIRECTION_TYPES,
    EVENT_TYPES,
    FREQUENCY_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    RECORDSTAGE_TYPES,
    SOURCE_TYPES,
)
from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.trading.events.order_related import EventOrderRelated
from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
from ginkgo.trading.strategy.risk_managements.base_risk import BaseRiskManagement
from ginkgo.trading.strategy.selectors.base_selector import BaseSelector
from ginkgo.trading.strategy.sizers.base_sizer import BaseSizer
from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy


class DummyLogger:
    """Simple logger that captures log messages for assertions."""

    def __init__(self) -> None:
        self.messages: List[tuple[str, str]] = []

    def DEBUG(self, msg: str) -> None:  # noqa: N802 - mirror logger signature
        self.messages.append(("DEBUG", msg))

    def INFO(self, msg: str) -> None:  # noqa: N802
        self.messages.append(("INFO", msg))

    def WARN(self, msg: str) -> None:  # noqa: N802
        self.messages.append(("WARN", msg))

    def ERROR(self, msg: str) -> None:  # noqa: N802
        self.messages.append(("ERROR", msg))

    def CRITICAL(self, msg: str) -> None:  # noqa: N802
        self.messages.append(("CRITICAL", msg))


class DummyMatchmaking:
    """Captures order submissions and price updates routed by the engine."""

    def __init__(self) -> None:
        self.engine: Optional[DummyEngine] = None
        self.event_publisher: Optional[Callable[[Any], None]] = None
        self.received_orders: List[Order] = []
        self.received_prices: List[EventPriceUpdate] = []

    def bind_engine(self, engine: "DummyEngine") -> None:
        self.engine = engine

    def set_event_publisher(self, publisher: Callable[[Any], None]) -> None:
        self.event_publisher = publisher

    def on_order_received(self, event: EventOrderRelated, *args, **kwargs) -> None:
        self.received_orders.append(event.value)

    def on_price_received(self, event: EventPriceUpdate, *args, **kwargs) -> None:
        self.received_prices.append(event)


class DummyFeeder:
    """Minimal feeder stub used to verify wiring."""

    def __init__(self) -> None:
        self.logger: Optional[DummyLogger] = None
        self.event_publisher: Optional[Callable[[Any], None]] = None
        self.engine: Optional[DummyEngine] = None

    def add_logger(self, logger: DummyLogger) -> None:
        self.logger = logger

    def set_event_publisher(self, publisher: Callable[[Any], None]) -> None:
        self.event_publisher = publisher

    def bind_engine(self, engine: "DummyEngine") -> None:
        self.engine = engine


class DummyEngine(BacktestBase):
    """Engine stub that mimics event registration, publishing, and binding."""

    def __init__(self, name: str, engine_id: str, run_id: str | None = None) -> None:
        super().__init__(name=name, engine_id=engine_id, run_id=run_id)
        self.portfolios: List[DummyPortfolio] = []
        self.matchmaking: Optional[DummyMatchmaking] = None
        self._handlers: Dict[EVENT_TYPES, List[Callable[[Any], None]]] = {}
        self.events: List[Any] = []
        self.data_feeder: Optional[DummyFeeder] = None
        self.start_date: Optional[datetime.date] = None
        self.end_date: Optional[datetime.date] = None
        self.started = False

    def bind_matchmaking(self, matchmaking: DummyMatchmaking) -> None:
        self.matchmaking = matchmaking
        matchmaking.bind_engine(self)

    def register(self, event_type: EVENT_TYPES, handler: Callable[[Any], None]) -> bool:
        handlers = self._handlers.setdefault(event_type, [])
        handlers.append(handler)
        return True

    def start(self) -> bool:
        self.started = True
        return True

    def bind_portfolio(self, portfolio: "DummyPortfolio") -> None:
        if portfolio in self.portfolios:
            return
        self.portfolios.append(portfolio)
        portfolio.bind_engine(self)
        if portfolio.engine_put is None:
            portfolio.set_event_publisher(self.put)

    def put(self, event: Any) -> None:
        self.events.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)

    def set_data_feeder(self, feeder: DummyFeeder) -> None:
        self.data_feeder = feeder
        feeder.bind_engine(self)


class DummyPortfolio(BacktestBase):
    """Portfolio stub that chains strategy → sizer → risk → analyzer."""

    def __init__(self, name: str = "dummy_portfolio") -> None:
        super().__init__(name=name)
        self.cash = 100_000
        self.strategies: List[DummyStrategy] = []
        self.selector: Optional[DummySelector] = None
        self.sizer: Optional[DummySizer] = None
        self.risk_managers: List[DummyRiskManager] = []
        self.analyzers: List[DummyAnalyzer] = []
        self.engine: Optional[DummyEngine] = None
        self.engine_put: Optional[Callable[[Any], None]] = None
        self.feeder: Optional[DummyFeeder] = None
        self.event_log: List[tuple[str, Any]] = []
        self.generated_orders: List[Order] = []

    def set_portfolio_name(self, value: str) -> None:
        self.set_name(value)

    def set_portfolio_id(self, value: str) -> str:
        self.set_backtest_ids(portfolio_id=value)
        return value

    def bind_engine(self, engine: DummyEngine) -> None:
        self.engine = engine
        self.set_backtest_ids(engine_id=engine.engine_id, run_id=engine.run_id)

    def set_event_publisher(self, publisher: Callable[[Any], None]) -> None:
        self.engine_put = publisher

    def bind_data_feeder(self, feeder: DummyFeeder, *args, **kwargs) -> None:
        self.feeder = feeder

    def add_strategy(self, strategy: "DummyStrategy") -> None:
        self.strategies.append(strategy)

    def bind_selector(self, selector: "DummySelector") -> None:
        self.selector = selector

    def bind_sizer(self, sizer: "DummySizer") -> None:
        self.sizer = sizer

    def add_risk_manager(self, risk_manager: "DummyRiskManager") -> None:
        self.risk_managers.append(risk_manager)

    def add_analyzer(self, analyzer: "DummyAnalyzer") -> None:
        self.analyzers.append(analyzer)

    def get_info(self) -> Dict[str, Any]:
        ids = self.get_id_dict()
        return {
            "portfolio_id": ids.get("portfolio_id"),
            "engine_id": ids.get("engine_id"),
            "run_id": ids.get("run_id"),
            "cash": self.cash,
        }

    def _submit_order(self, order: Order) -> None:
        self.generated_orders.append(order)
        event = EventOrderRelated(order)
        event.set_type(EVENT_TYPES.ORDERSUBMITTED)
        if self.engine_put is not None:
            self.engine_put(event)

    def on_price_received(self, event: EventPriceUpdate, *args, **kwargs) -> None:
        self.event_log.append(("price", event))
        if self.selector is None or self.sizer is None:
            return
        portfolio_info = self.get_info()
        picked = self.selector.pick(event)
        for strategy in self.strategies:
            for signal in strategy.cal(portfolio_info, event, selections=picked):
                order = self.sizer.cal(portfolio_info, signal)
                for risk_manager in self.risk_managers:
                    order = risk_manager.cal(portfolio_info, order)
                    if order is None:
                        break
                if order is not None:
                    self._submit_order(order)
        for analyzer in self.analyzers:
            analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

    def on_signal(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("signal", event))

    def on_order_ack(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_ack", event))

    def on_order_partially_filled(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_partial", event))

    def on_order_rejected(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_reject", event))

    def on_order_expired(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_expired", event))

    def on_order_cancel_ack(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_cancel_ack", event))

    def on_order_canceled(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_canceled", event))

    def on_order_filled(self, event: Any, *args, **kwargs) -> None:
        self.event_log.append(("order_filled", event))


class DummyStrategy(BaseStrategy):
    """Strategy stub that emits a single LONG signal for each price update."""

    def __init__(self, name: str = "dummy_strategy") -> None:
        super().__init__(name=name)
        self.calls: List[Dict[str, Any]] = []

    def cal(self, portfolio_info: Dict[str, Any], event: EventPriceUpdate, *args, **kwargs) -> List[Signal]:
        self.calls.append({"portfolio": portfolio_info, "event": event})
        ids = self.get_id_dict()
        signal = Signal(
            portfolio_id=ids.get("portfolio_id") or portfolio_info["portfolio_id"],
            engine_id=ids.get("engine_id") or portfolio_info["engine_id"],
            run_id=ids.get("run_id") or portfolio_info["run_id"],
            timestamp=event.timestamp,
            code=event.code,
            direction=DIRECTION_TYPES.LONG,
            reason="dummy-signal",
            source=SOURCE_TYPES.STRATEGY,
            strength=1.0,
            confidence=1.0,
        )
        return [signal]


class DummySelector(BaseSelector):
    """Selector stub that always returns the incoming event's code."""

    def __init__(self, name: str = "dummy_selector") -> None:
        super().__init__(name=name)
        self.calls: List[EventPriceUpdate] = []

    def pick(self, event: EventPriceUpdate, *args, **kwargs) -> List[str]:
        self.calls.append(event)
        return [event.code]


class DummySizer(BaseSizer):
    """Sizer stub that converts signals into fixed-size limit orders."""

    def __init__(self, name: str = "dummy_sizer") -> None:
        super().__init__(name=name)
        self.calls: List[Dict[str, Any]] = []

    def cal(self, portfolio_info: Dict[str, Any], signal: Signal, *args, **kwargs) -> Order:
        self.calls.append({"portfolio": portfolio_info, "signal": signal})
        return Order(
            portfolio_id=signal.portfolio_id,
            engine_id=signal.engine_id,
            run_id=signal.run_id,
            code=signal.code,
            direction=signal.direction,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=10.0,
            timestamp=signal.timestamp,
        )


class DummyRiskManager(BaseRiskManagement):
    """Risk manager stub that records invocations and approves orders."""

    def __init__(self, name: str = "dummy_risk") -> None:
        super().__init__(name=name)
        self.calls: List[Dict[str, Any]] = []

    def cal(self, portfolio_info: Dict[str, Any], order: Order):
        self.calls.append({"portfolio": portfolio_info, "order": order})
        return order


class DummyAnalyzer(BaseAnalyzer):
    """Analyzer stub that captures record invocations."""

    def __init__(self, name: str = "dummy_analyzer") -> None:
        super().__init__(name=name)
        self.record_calls: List[Dict[str, Any]] = []
        self.activate_calls: List[Dict[str, Any]] = []

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: Dict[str, Any], *args, **kwargs) -> None:
        self.activate_calls.append({"stage": stage, "portfolio": portfolio_info})

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: Dict[str, Any], *args, **kwargs) -> None:
        self.record_calls.append({"stage": stage, "portfolio": portfolio_info})


class TestableEngineAssemblyService(EngineAssemblyService):
    """Engine assembly with stubs to avoid external dependencies."""

    def _create_base_engine(self, engine_data: Dict[str, Any], engine_id: str, logger: DummyLogger) -> DummyEngine:
        engine = DummyEngine(name=engine_data["name"], engine_id=engine_id, run_id=engine_data.get("run_id"))
        engine.add_logger(logger)
        return engine

    def _setup_engine_infrastructure(
        self, engine: DummyEngine, logger: DummyLogger, engine_data: Dict[str, Any] | None = None
    ) -> bool:
        matchmaking = DummyMatchmaking()
        engine.bind_matchmaking(matchmaking)
        matchmaking.set_event_publisher(engine.put)
        engine.register(EVENT_TYPES.ORDERSUBMITTED, matchmaking.on_order_received)
        engine.register(EVENT_TYPES.PRICEUPDATE, matchmaking.on_price_received)

        feeder = DummyFeeder()
        feeder.add_logger(logger)
        feeder.set_event_publisher(engine.put)
        engine.set_data_feeder(feeder)
        return True

    def _create_portfolio_instance(self, portfolio_config: Dict[str, Any], logger: DummyLogger) -> DummyPortfolio:
        portfolio = DummyPortfolio(portfolio_config["name"])
        portfolio.add_logger(logger)
        return portfolio


def build_component_bundle() -> Dict[str, List[BacktestBase]]:
    """Utility to create a fresh set of stub trading components."""

    return {
        "strategies": [DummyStrategy()],
        "selectors": [DummySelector()],
        "sizers": [DummySizer()],
        "risk_managers": [DummyRiskManager()],
        "analyzers": [DummyAnalyzer()],
    }


def assemble_engine_with_components(component_bundle: Dict[str, List[BacktestBase]]):
    """Helper that assembles a dummy engine and returns context objects."""

    service = TestableEngineAssemblyService()
    engine_id = "engine-assembly"
    portfolio_id = "portfolio-alpha"
    run_id = "run-001"
    engine_data = {"name": "DummyEngine", "run_id": run_id}
    portfolio_config = {
        "uuid": portfolio_id,
        "name": "DummyPortfolio",
        "backtest_start_date": "2020-01-01",
        "backtest_end_date": "2020-12-31",
    }

    result = service.assemble_backtest_engine(
        engine_id=engine_id,
        engine_data=engine_data,
        portfolio_mappings=[{"portfolio_id": portfolio_id}],
        portfolio_configs={portfolio_id: portfolio_config},
        portfolio_components={portfolio_id: component_bundle},
        logger=DummyLogger(),
    )
    assert result.success, result.error or "engine assembly failed"
    engine = result.data
    portfolio = engine.portfolios[0]
    return engine, portfolio, engine_id, portfolio_id, run_id


def test_engine_assembly_wires_components_and_handlers():
    """Engine assembly should inject IDs, bind components, and register handlers."""

    components = build_component_bundle()
    engine, portfolio, engine_id, portfolio_id, run_id = assemble_engine_with_components(components)

    assert engine.started is True
    assert engine.matchmaking is not None
    assert engine.data_feeder is not None
    assert len(engine.portfolios) == 1

    # Engine handlers should include price updates and order submissions.
    assert EVENT_TYPES.PRICEUPDATE in engine._handlers
    assert EVENT_TYPES.ORDERSUBMITTED in engine._handlers

    # Portfolio should retain assigned identifiers.
    assert portfolio.get_id_dict()["engine_id"] == engine_id
    assert portfolio.get_id_dict()["portfolio_id"] == portfolio_id
    assert portfolio.get_id_dict()["run_id"] == run_id

    # Every component receives backtest identifiers.
    for component_type in ("strategies", "selectors", "sizers", "risk_managers", "analyzers"):
        for component in components[component_type]:
            id_dict = component.get_id_dict()
            assert id_dict["engine_id"] == engine_id
            assert id_dict["portfolio_id"] == portfolio_id
            assert id_dict["run_id"] == run_id


def test_price_event_triggers_full_pipeline_flow():
    """A price update should traverse the full component chain and reach the broker."""

    components = build_component_bundle()
    engine, portfolio, engine_id, portfolio_id, run_id = assemble_engine_with_components(components)

    strategy: DummyStrategy = components["strategies"][0]
    selector: DummySelector = components["selectors"][0]
    sizer: DummySizer = components["sizers"][0]
    risk_manager: DummyRiskManager = components["risk_managers"][0]
    analyzer: DummyAnalyzer = components["analyzers"][0]

    event_time = datetime.datetime(2020, 1, 2, tzinfo=datetime.timezone.utc)
    bar = Bar(
        code="000001.SZ",
        open=10,
        high=11,
        low=9,
        close=10.5,
        volume=1000,
        amount=1000,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=event_time,
    )
    price_event = EventPriceUpdate(bar)
    price_event.engine_id = engine_id
    price_event.portfolio_id = portfolio_id
    price_event.run_id = run_id

    engine.put(price_event)

    assert portfolio.generated_orders, "portfolio should emit order submissions"
    order = portfolio.generated_orders[0]
    assert order.portfolio_id == portfolio_id
    assert order.engine_id == engine_id
    assert order.run_id == run_id

    # Matchmaking should receive submitted orders.
    assert engine.matchmaking is not None
    assert engine.matchmaking.received_orders == [order]

    # Component call stacks verify the chain execution.
    assert strategy.calls, "strategy should be invoked"
    assert selector.calls, "selector should be invoked"
    assert sizer.calls, "sizer should be invoked"
    assert risk_manager.calls, "risk manager should be invoked"
    assert analyzer.record_calls, "analyzer should record outputs"
    assert analyzer.record_calls[0]["stage"] is RECORDSTAGE_TYPES.NEWDAY

    # Engine should have recorded both the incoming price event and the submitted order event.
    assert [e.event_type for e in engine.events] == [EVENT_TYPES.PRICEUPDATE, EVENT_TYPES.ORDERSUBMITTED]
