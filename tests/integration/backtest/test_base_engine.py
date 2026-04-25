"""
Tests for BaseEngine - the abstract base class for trading engines.

Tests use ConcreteTestEngine, a minimal concrete subclass that satisfies
the abstract method requirements (run, handle_event).
"""

import unittest
from unittest.mock import patch, Mock
import threading

from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.enums import ENGINESTATUS_TYPES, EXECUTION_MODE


class ConcreteTestEngine(BaseEngine):
    """Minimal concrete subclass for testing the abstract BaseEngine."""

    def run(self):
        return None

    def handle_event(self, event):
        pass


class BaseEngineTest(unittest.TestCase):
    """
    Test BaseEngine module - only tests BaseEngine behaviour via ConcreteTestEngine.
    """

    def setUp(self):
        self.engine = ConcreteTestEngine("test_engine")

    # ------------------------------------------------------------------
    # Construction / Initialization
    # ------------------------------------------------------------------

    def test_construction_basic(self):
        """Engine can be created with a name."""
        engine = ConcreteTestEngine("test_engine")
        self.assertIsNotNone(engine)
        self.assertEqual(engine.name, "test_engine")

    def test_construction_defaults(self):
        """Default name is 'BaseEngine'."""
        engine = ConcreteTestEngine()
        self.assertEqual(engine.name, "BaseEngine")

    def test_construction_has_uuid(self):
        """Every engine gets a unique uuid string."""
        engine = ConcreteTestEngine("e1")
        self.assertTrue(hasattr(engine, "uuid"))
        self.assertIsInstance(engine.uuid, str)
        self.assertEqual(len(engine.uuid), 36)  # UUID hex format

    def test_construction_has_engine_id(self):
        """Every engine gets an engine_id (read-only property)."""
        engine = ConcreteTestEngine("e1")
        self.assertTrue(hasattr(engine, "engine_id"))
        self.assertIsInstance(engine.engine_id, str)

    def test_construction_mode_defaults_to_backtest(self):
        engine = ConcreteTestEngine("e1")
        self.assertEqual(engine.mode, EXECUTION_MODE.BACKTEST)

    def test_construction_mode_can_be_overridden(self):
        engine = ConcreteTestEngine("e1", mode=EXECUTION_MODE.LIVE)
        self.assertEqual(engine.mode, EXECUTION_MODE.LIVE)

    def test_construction_engine_id_can_be_passed(self):
        engine = ConcreteTestEngine("e1", engine_id="my-custom-id")
        self.assertEqual(engine.engine_id, "my-custom-id")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_name_property(self):
        self.assertEqual(self.engine.name, "test_engine")

    def test_mode_property(self):
        self.assertEqual(self.engine.mode, EXECUTION_MODE.BACKTEST)

    def test_mode_setter(self):
        self.engine.mode = EXECUTION_MODE.LIVE
        self.assertEqual(self.engine.mode, EXECUTION_MODE.LIVE)

    # ------------------------------------------------------------------
    # Status / State
    # ------------------------------------------------------------------

    def test_initial_status_is_idle(self):
        self.assertEqual(self.engine.status, "idle")
        self.assertEqual(self.engine.state, ENGINESTATUS_TYPES.IDLE)

    def test_is_active_initially_false(self):
        self.assertFalse(self.engine.is_active)

    # ------------------------------------------------------------------
    # start()
    # ------------------------------------------------------------------

    def test_start_from_idle(self):
        result = self.engine.start()
        self.assertTrue(result)
        self.assertEqual(self.engine.status, "running")
        self.assertTrue(self.engine.is_active)

    def test_start_generates_task_id(self):
        self.assertIsNone(self.engine.task_id)
        self.engine.start()
        self.assertIsNotNone(self.engine.task_id)

    def test_start_from_stopped_generates_new_task_id(self):
        self.engine.start()
        first_task_id = self.engine.task_id
        self.engine.stop()
        # stop() clears trace_id but does NOT clear task_id
        # generate_task_id() without force=True is a no-op when task_id is set
        self.assertEqual(self.engine.task_id, first_task_id)
        # Use force=True to actually get a new task_id
        new_task_id = self.engine.generate_task_id(force=True)
        self.assertIsNotNone(new_task_id)
        self.assertNotEqual(new_task_id, first_task_id)
        self.assertEqual(self.engine.run_sequence, 2)

    def test_start_from_paused_keeps_task_id(self):
        self.engine.start()
        task_id = self.engine.task_id
        self.engine.pause()
        self.engine.start()
        self.assertEqual(self.engine.task_id, task_id)

    def test_start_from_running_returns_false(self):
        self.engine.start()
        result = self.engine.start()
        self.assertFalse(result)
        self.assertEqual(self.engine.status, "running")

    # ------------------------------------------------------------------
    # pause()
    # ------------------------------------------------------------------

    def test_pause_from_running(self):
        self.engine.start()
        result = self.engine.pause()
        self.assertTrue(result)
        self.assertEqual(self.engine.status, "paused")
        self.assertFalse(self.engine.is_active)

    def test_pause_from_idle_returns_false(self):
        result = self.engine.pause()
        self.assertFalse(result)
        self.assertEqual(self.engine.status, "idle")

    def test_pause_from_stopped_returns_false(self):
        self.engine.start()
        self.engine.stop()
        result = self.engine.pause()
        self.assertFalse(result)
        self.assertEqual(self.engine.status, "stopped")

    # ------------------------------------------------------------------
    # stop()
    # ------------------------------------------------------------------

    def test_stop_from_running(self):
        self.engine.start()
        result = self.engine.stop()
        self.assertTrue(result)
        self.assertEqual(self.engine.status, "stopped")
        self.assertFalse(self.engine.is_active)

    def test_stop_from_paused(self):
        self.engine.start()
        self.engine.pause()
        result = self.engine.stop()
        self.assertTrue(result)
        self.assertEqual(self.engine.status, "stopped")

    def test_stop_from_idle_returns_false(self):
        result = self.engine.stop()
        self.assertFalse(result)
        self.assertEqual(self.engine.status, "idle")

    def test_stop_from_stopped_returns_false(self):
        self.engine.start()
        self.engine.stop()
        result = self.engine.stop()
        self.assertFalse(result)
        self.assertEqual(self.engine.status, "stopped")

    # ------------------------------------------------------------------
    # set_engine_id()
    # ------------------------------------------------------------------

    def test_set_engine_id_from_idle(self):
        self.engine.set_engine_id("new-id")
        self.assertEqual(self.engine.engine_id, "new-id")

    def test_set_engine_id_from_running_raises(self):
        self.engine.start()
        with self.assertRaises(RuntimeError, msg="Cannot change engine_id after engine has started"):
            self.engine.set_engine_id("new-id")

    def test_set_engine_id_from_paused_raises(self):
        self.engine.start()
        self.engine.pause()
        with self.assertRaises(RuntimeError):
            self.engine.set_engine_id("new-id")

    # ------------------------------------------------------------------
    # engine_id is read-only
    # ------------------------------------------------------------------

    def test_engine_id_no_direct_setter(self):
        """engine_id has no setter; only set_engine_id() works."""
        with self.assertRaises(AttributeError):
            self.engine.engine_id = "hack"

    # ------------------------------------------------------------------
    # set_task_id()
    # ------------------------------------------------------------------

    def test_set_task_id_from_idle(self):
        self.engine.set_task_id("custom-run-id")
        self.assertEqual(self.engine.task_id, "custom-run-id")

    def test_set_task_id_from_running_raises(self):
        self.engine.start()
        with self.assertRaises(RuntimeError):
            self.engine.set_task_id("custom-run-id")

    # ------------------------------------------------------------------
    # generate_task_id()
    # ------------------------------------------------------------------

    def test_generate_task_id(self):
        task_id = self.engine.generate_task_id()
        self.assertIsNotNone(task_id)
        self.assertEqual(task_id, self.engine.task_id)

    def test_generate_task_id_does_not_overwrite(self):
        first = self.engine.generate_task_id()
        second = self.engine.generate_task_id()
        self.assertEqual(first, second)

    def test_generate_task_id_force(self):
        first = self.engine.generate_task_id()
        second = self.engine.generate_task_id(force=True)
        self.assertNotEqual(first, second)
        self.assertEqual(self.engine.run_sequence, 2)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def test_full_lifecycle(self):
        # idle -> running
        self.assertTrue(self.engine.start())
        self.assertEqual(self.engine.status, "running")

        # running -> paused
        self.assertTrue(self.engine.pause())
        self.assertEqual(self.engine.status, "paused")

        # paused -> running (resume)
        self.assertTrue(self.engine.start())
        self.assertEqual(self.engine.status, "running")

        # running -> stopped
        self.assertTrue(self.engine.stop())
        self.assertEqual(self.engine.status, "stopped")

        # stopped -> running (new session)
        self.assertTrue(self.engine.start())
        self.assertEqual(self.engine.status, "running")

    def test_multiple_start_calls(self):
        """Extra start() calls while running are no-ops returning False."""
        self.assertTrue(self.engine.start())
        self.assertFalse(self.engine.start())
        self.assertTrue(self.engine.is_active)

    def test_multiple_pause_calls(self):
        """Extra pause() calls while not running return False."""
        self.engine.start()
        self.assertTrue(self.engine.pause())
        self.assertFalse(self.engine.pause())
        self.assertEqual(self.engine.status, "paused")

    # ------------------------------------------------------------------
    # __repr__
    # ------------------------------------------------------------------

    def test_repr(self):
        r = repr(self.engine)
        self.assertIsInstance(r, str)
        self.assertIn("ConcreteTestEngine", r)
        self.assertIn("name=test_engine", r)

    def test_repr_different_states(self):
        r1 = repr(self.engine)
        self.engine.start()
        r2 = repr(self.engine)
        self.engine.pause()
        r3 = repr(self.engine)
        # All should be strings containing the class name
        for r in (r1, r2, r3):
            self.assertIn("ConcreteTestEngine", r)

    # ------------------------------------------------------------------
    # Portfolio management
    # ------------------------------------------------------------------

    def test_add_portfolio(self):
        portfolio = Mock()
        portfolio.name = "p1"
        self.engine.add_portfolio(portfolio)
        self.assertEqual(len(self.engine.portfolios), 1)

    def test_add_duplicate_portfolio_ignored(self):
        portfolio = Mock()
        portfolio.name = "p1"
        self.engine.add_portfolio(portfolio)
        self.engine.add_portfolio(portfolio)  # duplicate
        self.assertEqual(len(self.engine.portfolios), 1)

    def test_add_portfolio_without_name_raises(self):
        portfolio = Mock(spec=[])  # no attributes at all
        with self.assertRaises(AttributeError, msg="Portfolio must have 'name' attribute"):
            self.engine.add_portfolio(portfolio)

    def test_add_portfolio_calls_bind_engine(self):
        portfolio = Mock()
        portfolio.name = "p1"
        self.engine.add_portfolio(portfolio)
        portfolio.bind_engine.assert_called_once_with(self.engine)

    def test_remove_portfolio(self):
        portfolio = Mock()
        portfolio.name = "p1"
        self.engine.add_portfolio(portfolio)
        self.engine.remove_portfolio(portfolio)
        self.assertEqual(len(self.engine.portfolios), 0)

    # ------------------------------------------------------------------
    # get_engine_summary / get_engine_status
    # ------------------------------------------------------------------

    def test_get_engine_summary(self):
        summary = self.engine.get_engine_summary()
        self.assertEqual(summary["name"], "test_engine")
        self.assertEqual(summary["status"], "idle")
        self.assertFalse(summary["is_active"])
        self.assertEqual(summary["portfolios_count"], 0)
        self.assertIn("engine_id", summary)
        self.assertIn("uuid", summary)
        self.assertIn("mode", summary)

    def test_get_engine_status(self):
        status = self.engine.get_engine_status()
        self.assertEqual(status["engine_name"], "test_engine")
        self.assertEqual(status["status"], "idle")
        self.assertFalse(status["is_active"])

    # ------------------------------------------------------------------
    # get_engine_context
    # ------------------------------------------------------------------

    def test_get_engine_context(self):
        ctx = self.engine.get_engine_context()
        self.assertIsNotNone(ctx)

    # ------------------------------------------------------------------
    # set_data_feeder
    # ------------------------------------------------------------------

    def test_set_data_feeder(self):
        feeder = Mock()
        feeder.name = "test_feeder"
        self.engine.set_data_feeder(feeder)
        self.assertEqual(self.engine._datafeeder, feeder)

    # ------------------------------------------------------------------
    # run_sequence
    # ------------------------------------------------------------------

    def test_run_sequence_initial(self):
        self.assertEqual(self.engine.run_sequence, 0)

    def test_run_sequence_increments(self):
        self.engine.generate_task_id()
        self.assertEqual(self.engine.run_sequence, 1)
        self.engine.generate_task_id(force=True)
        self.assertEqual(self.engine.run_sequence, 2)

    # ------------------------------------------------------------------
    # Component type
    # ------------------------------------------------------------------

    def test_component_type(self):
        from ginkgo.enums import COMPONENT_TYPES
        self.assertEqual(self.engine.component_type, COMPONENT_TYPES.ENGINE)

    # ------------------------------------------------------------------
    # Concurrent operations
    # ------------------------------------------------------------------

    def test_concurrent_state_operations(self):
        """Concurrent operations should not raise exceptions."""
        results = []

        def worker(operation_name):
            try:
                getattr(self.engine, operation_name)()
                results.append((operation_name, self.engine.is_active, self.engine.status))
            except Exception as e:
                results.append((operation_name, "ERROR", str(e)))

        threads = []
        for op in ["start", "pause", "start", "stop", "start"]:
            t = threading.Thread(target=worker, args=(op,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=2.0)

        error_results = [r for r in results if r[1] == "ERROR"]
        self.assertEqual(len(error_results), 0, f"Errors: {error_results}")

    # ------------------------------------------------------------------
    # Memory / cleanup
    # ------------------------------------------------------------------

    def test_multiple_instances_independent(self):
        """Multiple engines have independent state."""
        e1 = ConcreteTestEngine("e1")
        e2 = ConcreteTestEngine("e2")

        e1.start()
        self.assertTrue(e1.is_active)
        self.assertFalse(e2.is_active)

        e2.start()
        e2.stop()
        self.assertTrue(e1.is_active)
        self.assertFalse(e2.is_active)

    # ------------------------------------------------------------------
    # Abstract method enforcement
    # ------------------------------------------------------------------

    def test_cannot_instantiate_abstract_base(self):
        """BaseEngine itself cannot be instantiated (abstract methods)."""
        with self.assertRaises(TypeError):
            BaseEngine("direct")

    def test_concrete_subclass_is_instance_of_base(self):
        self.assertIsInstance(self.engine, BaseEngine)
