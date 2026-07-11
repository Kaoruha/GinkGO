"""Smoke + behavior tests for livecore.data_manager -- #3870, #6695"""
import threading

import pytest
from unittest.mock import patch, MagicMock

try:
    from ginkgo.livecore.data_manager import DataManager
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="DataManager not available")
class TestDataManager:
    def test_instantiation(self):
        dm = DataManager()
        assert dm is not None

    def test_instantiation_custom_feeders(self):
        dm = DataManager(feeder_types=["eastmoney"])
        assert dm is not None

    def test_get_status_returns_dict_or_raises(self):
        dm = DataManager()
        # get_status may fail if GCONF/Kafka not configured
        try:
            status = dm.get_status()
            assert isinstance(status, dict)
        except (AttributeError, TypeError):
            pass  # Expected if no Kafka configured


@pytest.mark.skipif(not HAS_MODULE, reason="DataManager not available")
class TestDataManagerStartContract:
    """#6695: start() must honor threading.Thread contract (super().start()),
    not self-recurse. Synchronous setup lives in initialize()."""

    @staticmethod
    def _make_dm_with_mock_feeder(mock_feeder):
        """Build a DataManager whose feeder is a MagicMock, bypassing real
        feeder construction (network/heavy deps)."""
        def fake_init_feeder(self_dm, feeder_type, config=None):
            self_dm._feeders[feeder_type] = mock_feeder
            return True
        with patch.object(DataManager, "_initialize_feeder", fake_init_feeder):
            return DataManager(feeder_types=["eastmoney"])

    def test_initialize_sets_up_producer_and_feeders_without_starting_thread(self):
        """initialize() performs synchronous setup (producer, feeders,
        restore_subscriptions) and does NOT launch the background thread."""
        mock_feeder = MagicMock()
        with patch("ginkgo.livecore.data_manager.GinkgoProducer") as MockProducer, \
             patch.object(DataManager, "restore_subscriptions") as mock_restore:
            dm = self._make_dm_with_mock_feeder(mock_feeder)
            dm.initialize()

            # producer constructed
            assert MockProducer.called
            # feeder initialized, wired, and started
            mock_feeder.initialize.assert_called_once()
            mock_feeder.set_event_publisher.assert_called_once()
            mock_feeder.start.assert_called_once()
            # subscriptions restored
            mock_restore.assert_called_once()
            # thread NOT launched yet
            assert dm.is_alive() is False

    def test_start_launches_thread_that_enters_run(self):
        """start() must spawn the background thread via super().start() so
        run() actually executes. Regression guard for the self.start()
        recursion that previously swallowed RecursionError (#6695)."""
        run_entered = threading.Event()
        mock_feeder = MagicMock()
        with patch("ginkgo.livecore.data_manager.GinkgoProducer"), \
             patch.object(DataManager, "restore_subscriptions"), \
             patch("ginkgo.notifier.core.notification_service.notify"):
            dm = self._make_dm_with_mock_feeder(mock_feeder)
            # Replace run() with a signal stub (avoids real Kafka consumers).
            dm.run = lambda: run_entered.set()
            dm.initialize()
            dm.start()
            try:
                assert run_entered.wait(2.0), "run() was never entered"
                assert dm.is_alive() is False or run_entered.is_set()
            finally:
                dm.join(timeout=2.0)

    def test_start_does_not_swallow_programming_errors(self):
        """A programming/runtime error on the startup path must propagate,
        not be swallowed by a broad except Exception (#6695). The old code
        masked RecursionError and returned False silently."""
        mock_feeder = MagicMock()
        with patch("ginkgo.livecore.data_manager.GinkgoProducer"), \
             patch.object(DataManager, "restore_subscriptions"), \
             patch("ginkgo.notifier.core.notification_service.notify"):
            dm = self._make_dm_with_mock_feeder(mock_feeder)
            dm.initialize()
            # super().start() raising simulates a startup-path error.
            with patch.object(threading.Thread, "start", side_effect=RuntimeError("boom")):
                with pytest.raises(RuntimeError):
                    dm.start()

    def test_start_source_honors_thread_contract(self):
        """Regression guard (source inspection): start() must delegate to
        super().start() and must never self-recurse (#6695)."""
        import inspect
        src = inspect.getsource(DataManager.start)
        assert "self.start()" not in src, "start() must not self-recurse"
        assert "super().start()" in src, "start() must call super().start()"

    def test_livecore_start_data_manager_calls_initialize_before_start(self):
        """LiveCore._start_data_manager must call initialize() before start()
        so synchronous setup runs before the thread launches (#6695)."""
        import inspect
        try:
            from ginkgo.livecore.main import LiveCore
        except Exception:
            pytest.skip("LiveCore import unavailable in this env")
        src = inspect.getsource(LiveCore._start_data_manager)
        init_idx = src.find(".initialize()")
        start_idx = src.find(".start()")
        assert init_idx != -1, "_start_data_manager must call initialize()"
        assert start_idx != -1, "_start_data_manager must call start()"
        assert init_idx < start_idx, "initialize() must run before start()"
