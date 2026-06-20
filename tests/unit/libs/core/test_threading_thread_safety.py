"""
Tests for GinkgoThreadManager thread-safety fixes (#5516).

#5516: add_thread previously cached os.getpid() (the host process pid), so
       kill_thread did os.kill(host_pid, SIGKILL) — killing the entire process
       (suicide footgun). get_thread_status checked psutil.Process(host_pid)
       which is always True for an in-process thread (not actual liveness).

The fixes:
  - add_thread caches the thread ident AND keeps the live Thread handle.
  - get_thread_status uses Thread.is_alive() on the cached handle.
  - kill_thread drops os.kill entirely (in-process threads can't be hard-killed).
"""

import os
import time
import threading
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Mock RedisService. Configured per-test (exists/get_thread_from_cache)."""
    return MagicMock()


@pytest.fixture
def gtm(mock_redis):
    """GTM with injected mock Redis (no real infra)."""
    from ginkgo.libs.core.threading import GinkgoThreadManager
    return GinkgoThreadManager(redis_service=mock_redis)


# ===========================================================================
# #5516 — kill_thread must not signal the host process (tracer bullet)
# ===========================================================================

class TestKillThreadSafety:
    """kill_thread must never os.kill the host process pid."""

    def test_kill_thread_does_not_signal_host_pid(self, gtm, mock_redis):
        """
        Previously add_thread cached os.getpid() and kill_thread did
        os.kill(host_pid, SIGKILL) -> killed the entire process (suicide).
        kill_thread must not signal the host pid at all.
        """
        host_pid = os.getpid()
        # Simulate the buggy cache state: cached value == host pid
        # (what add_thread used to store before the fix).
        mock_redis.exists.return_value = True
        mock_redis.get_thread_from_cache.return_value = str(host_pid)

        with patch("ginkgo.libs.core.threading.os.kill") as mock_kill:
            gtm.kill_thread("worker-a")

        # in-process threads must NEVER be os.kill'd (especially not the host pid)
        mock_kill.assert_not_called()


# ===========================================================================
# #5516 — add_thread must cache the thread ident, not the host pid
# ===========================================================================

class TestAddThreadCachesIdent:
    """add_thread must register the actual thread (ident + handle), not os.getpid()."""

    def test_add_thread_caches_thread_ident_not_host_pid(self, gtm, mock_redis):
        """
        Previously add_thread cached str(os.getpid()) (identical for every thread
        in the process -> impossible to distinguish workers). Must cache the
        started thread's ident instead.
        """
        host_pid = os.getpid()
        mock_redis.exists.return_value = False

        started = threading.Event()

        def target():
            started.set()
            time.sleep(5)

        gtm.add_thread("worker-b", target)
        assert started.wait(2), "target thread did not start"

        mock_redis.set_thread_cache.assert_called_once()
        cached_value = mock_redis.set_thread_cache.call_args.args[1]
        assert cached_value != str(host_pid), "cached host pid, not thread ident"
        assert int(cached_value) > 0  # ident must be a positive integer string


# ===========================================================================
# #5516 — get_thread_status must reflect actual thread liveness
# ===========================================================================

class TestGetThreadStatusLiveness:
    """get_thread_status must report the thread's real liveness (is_alive),
    not the host process (always True for an in-process thread)."""

    def test_live_thread_reports_alive(self, gtm, mock_redis):
        mock_redis.exists.return_value = False
        keep_alive = threading.Event()

        def target():
            keep_alive.wait(5)

        gtm.add_thread("worker-c", target)
        # while the thread is actually running, status must be True
        assert gtm.get_thread_status("worker-c") is True
        keep_alive.set()  # release the thread

    def test_finished_thread_reports_not_alive(self, gtm, mock_redis):
        mock_redis.exists.return_value = False
        done = threading.Event()

        def target():
            done.set()

        gtm.add_thread("worker-d", target)
        assert done.wait(2)
        time.sleep(0.1)  # let the thread exit
        # once the thread has finished, status must be False
        assert gtm.get_thread_status("worker-d") is False
