"""
EventEngine tests using pytest framework.
Tests cover event registration, handler management, threading, and event processing.
"""

import pytest
import threading
import time
from datetime import datetime
from queue import Queue
from unittest.mock import Mock, patch

from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.enums import EVENT_TYPES
from ginkgo.trading.events import EventCapitalUpdate


# ========== Fixtures ==========

@pytest.fixture
def event_engine():
    """Create an EventEngine instance for testing."""
    engine = EventEngine("test_event_engine")
    yield engine
    # Cleanup - ensure engine is stopped
    if hasattr(engine, 'stop'):
        try:
            engine.stop()
        except:
            pass


@pytest.fixture
def test_time():
    """Create a test datetime."""
    return datetime(2024, 1, 1, 10, 0, 0)


@pytest.fixture
def event_engine_with_time(event_engine, test_time):
    """Create an EventEngine with time set."""
    event_engine.on_time_goes_by(test_time)
    return event_engine


# ========== Construction Tests ==========

class TestEventEngineConstruction:
    """Test EventEngine construction and initialization."""

    def test_event_engine_init(self):
        """Test event engine initialization."""
        engine = EventEngine("test_event_engine")
        assert engine is not None

    def test_default_initialization(self):
        """Test default initialization."""
        engine = EventEngine()
        assert engine._name == "EventEngine"
        assert engine._timer_interval == 1

    def test_custom_timer_interval(self):
        """Test custom timer interval."""
        engine = EventEngine("test", timer_interval=5)
        assert engine._timer_interval == 5

    def test_inheritance_from_base_engine(self):
        """Test inheritance from BaseEngine."""
        from ginkgo.trading.engines.base_engine import BaseEngine

        engine = EventEngine("test")
        assert isinstance(engine, BaseEngine)

        # Verify inherited attributes and methods
        assert hasattr(engine, "start")
        assert hasattr(engine, "pause")
        assert hasattr(engine, "stop")
        assert hasattr(engine, "status")
        assert hasattr(engine, "is_active")


# ========== Engine Lifecycle Tests ==========

class TestEngineLifecycle:
    """Test engine lifecycle management."""

    def test_engine_start(self, event_engine):
        """Test engine start."""
        assert event_engine.is_active is False
        event_engine.start()
        assert event_engine.is_active is True
        event_engine.stop()

    def test_engine_stop(self, event_engine):
        """Test engine stop."""
        assert event_engine.is_active is False
        event_engine.start()
        assert event_engine.is_active is True
        time.sleep(0.1)
        event_engine.stop()
        assert event_engine.is_active is False


# ========== Event Registration Tests ==========

class TestEventRegistration:
    """Test event handler registration."""

    def test_engine_register(self, event_engine):
        """Test event registration."""
        def test_handler():
            print("test")

        assert event_engine.handler_count == 0
        event_engine.register(EVENT_TYPES.OTHER, test_handler)
        assert event_engine.handler_count == 1
        event_engine.stop()

    def test_engine_unregister(self, event_engine):
        """Test event unregistration."""
        def test_handler():
            print("test")

        assert event_engine.handler_count == 0
        event_engine.register(EVENT_TYPES.OTHER, test_handler)
        assert event_engine.handler_count == 1

        # Unregister different event type should not affect count
        event_engine.unregister(EVENT_TYPES.CAPITALUPDATE, test_handler)
        assert event_engine.handler_count == 1

        # Unregister correct event type
        event_engine.unregister(EVENT_TYPES.OTHER, test_handler)
        assert event_engine.handler_count == 0
        event_engine.stop()


# ========== General Handler Tests ==========

class TestGeneralHandlers:
    """Test general handler registration."""

    def test_engine_register_general(self, event_engine):
        """Test general handler registration."""
        def test_handler():
            print("test")

        assert event_engine.general_count == 0
        event_engine.register_general(test_handler)
        assert event_engine.general_count == 1
        event_engine.stop()

    def test_engine_unregister_general(self, event_engine):
        """Test general handler unregistration."""
        def test_handler():
            print("test")

        assert event_engine.general_count == 0
        event_engine.register_general(test_handler)
        assert event_engine.general_count == 1
        event_engine.unregister_general(test_handler)
        assert event_engine.general_count == 0
        event_engine.stop()


# ========== Timer Handler Tests ==========

class TestTimerHandlers:
    """Test timer handler registration."""

    def test_engine_register_timer(self, event_engine):
        """Test timer registration."""
        def test_handler():
            print("test")

        assert event_engine.timer_count == 0
        event_engine.register_timer(test_handler)
        assert event_engine.timer_count == 1
        event_engine.stop()

    def test_engine_unregister_timer(self, event_engine):
        """Test timer unregistration."""
        def test_handler():
            print("test")

        assert event_engine.timer_count == 0
        event_engine.register_timer(test_handler)
        assert event_engine.timer_count == 1
        event_engine.unregister_timer(test_handler)
        assert event_engine.timer_count == 0
        event_engine.stop()

    def test_engine_timer_process(self, event_engine):
        """Test timer processing."""
        engine = EventEngine(timer_interval=0.01)

        test_counter = 0

        def test_handle():
            nonlocal test_counter
            test_counter += 1

        engine.register_timer(test_handle)
        engine.start()
        time.sleep(0.5)
        engine.stop()
        assert test_counter > 2


# ========== Event Processing Tests ==========

class TestEventProcessing:
    """Test event processing functionality."""

    def test_engine_put(self, event_engine):
        """Test event queuing."""
        e = EventCapitalUpdate()
        event_engine.put(e)
        assert event_engine.todo_count == 1
        event_engine.put(e)
        assert event_engine.todo_count == 2
        event_engine.stop()

    def test_engine_process(self, event_engine):
        """Test event processing."""
        test_counter = 0

        def test_handle(event):
            nonlocal test_counter
            test_counter += 1

        event_engine.register(EVENT_TYPES.CAPITALUPDATE, test_handle)
        e = EventCapitalUpdate()
        event_engine._process(e)
        assert test_counter == 1
        event_engine._process(e)
        assert test_counter == 2
        event_engine._process(e)
        assert test_counter == 3
        event_engine.stop()

    def test_engine_general_process(self, event_engine):
        """Test general event processing."""
        test_counter = 0

        def test_handle(event):
            nonlocal test_counter
            test_counter += 1

        def test_general(event):
            nonlocal test_counter
            test_counter += 2

        event_engine.register(EVENT_TYPES.CAPITALUPDATE, test_handle)
        event_engine.register_general(test_general)
        e = EventCapitalUpdate()
        event_engine._process(e)
        assert test_counter == 3
        event_engine._process(e)
        assert test_counter == 6
        event_engine._process(e)
        assert test_counter == 9
        event_engine.stop()


# ========== Threading Tests ==========

class TestThreading:
    """Test threading functionality."""

    def test_threading_attributes(self, event_engine_with_time):
        """Test thread related attributes."""
        # Check thread flags
        assert hasattr(event_engine_with_time, "_main_flag")
        assert isinstance(event_engine_with_time._main_flag, threading.Event)

        assert hasattr(event_engine_with_time, "_timer_flag")
        assert isinstance(event_engine_with_time._timer_flag, threading.Event)

        # Check thread objects
        assert hasattr(event_engine_with_time, "_main_thread")
        assert isinstance(event_engine_with_time._main_thread, threading.Thread)

        assert hasattr(event_engine_with_time, "_timer_thread")
        assert isinstance(event_engine_with_time._timer_thread, threading.Thread)

    def test_thread_lifecycle(self, event_engine_with_time):
        """Test thread lifecycle management."""
        # Check initial state
        assert not event_engine_with_time._main_thread.is_alive()
        assert not event_engine_with_time._timer_thread.is_alive()

        # Start engine should start threads
        event_engine_with_time.start()
        time.sleep(0.1)

        # Stop engine
        event_engine_with_time.stop()


# ========== Attribute Tests ==========

class TestEventEngineAttributes:
    """Test EventEngine attributes and structure."""

    def test_event_handling_attributes(self, event_engine_with_time):
        """Test event handling attributes."""
        # Check event handlers
        assert hasattr(event_engine_with_time, "_handlers")
        assert isinstance(event_engine_with_time._handlers, dict)

        assert hasattr(event_engine_with_time, "_general_handlers")
        assert isinstance(event_engine_with_time._general_handlers, list)

        assert hasattr(event_engine_with_time, "_timer_handlers")
        assert isinstance(event_engine_with_time._timer_handlers, list)

        assert hasattr(event_engine_with_time, "_time_hooks")
        assert isinstance(event_engine_with_time._time_hooks, list)

    def test_queue_attribute(self, event_engine_with_time):
        """Test event queue attribute."""
        assert hasattr(event_engine_with_time, "_queue")
        assert isinstance(event_engine_with_time._queue, Queue)

    def test_count_properties(self, event_engine_with_time):
        """Test count properties."""
        assert hasattr(event_engine_with_time, "handler_count")
        assert hasattr(event_engine_with_time, "general_count")
        assert hasattr(event_engine_with_time, "timer_count")
        assert hasattr(event_engine_with_time, "todo_count")

    def test_main_loop_method_exists(self, event_engine_with_time):
        """Test main loop method exists."""
        assert hasattr(event_engine_with_time, "main_loop")
        assert callable(event_engine_with_time.main_loop)

    def test_timer_loop_method_exists(self, event_engine_with_time):
        """Test timer loop method exists."""
        assert hasattr(event_engine_with_time, "timer_loop")
        assert callable(event_engine_with_time.timer_loop)


# ========== Concurrent Processing Tests ==========

class TestConcurrentProcessing:
    """Test concurrent event handling."""

    def test_concurrent_event_handling(self, event_engine):
        """Test concurrent event handling."""
        results = []

        def test_handler(event):
            results.append(event.event_type)

        event_engine.register(EVENT_TYPES.CAPITALUPDATE, test_handler)

        # Put multiple events concurrently
        for i in range(5):
            e = EventCapitalUpdate()
            event_engine.put(e)

        # Process events directly
        while event_engine.todo_count > 0:
            try:
                event_obj = event_engine._queue.get_nowait()
                event_engine._process(event_obj)
            except Exception:
                break

        event_engine.stop()

        assert len(results) > 0


# ========== Error Handling Tests ==========

class TestErrorHandling:
    """Test error handling in event processing."""

    def test_error_handling_in_handlers(self, event_engine):
        """Test error handling in handlers."""
        def error_handler(event):
            raise ValueError("Test error")

        def normal_handler(event):
            pass

        event_engine.register(EVENT_TYPES.CAPITALUPDATE, error_handler)
        event_engine.register(EVENT_TYPES.CAPITALUPDATE, normal_handler)

        e = EventCapitalUpdate()
        # Current implementation doesn't handle errors in handlers
        with pytest.raises(ValueError):
            event_engine._process(e)

        event_engine.stop()
