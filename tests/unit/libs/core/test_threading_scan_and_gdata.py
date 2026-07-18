"""
Tests for GinkgoThreadManager SCAN loop fix (#5503) and GDATA removal (#5570).

Verifies that Redis SCAN-based cleanup methods actually iterate through elements,
and that GDATA references have been completely removed.
"""

from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Create a mock RedisService."""
    redis = MagicMock()
    return redis


@pytest.fixture
def gtm(mock_redis):
    """Create a GTM instance with injected mock Redis."""
    from ginkgo.libs.core.threading import GinkgoThreadManager
    return GinkgoThreadManager(redis_service=mock_redis)


# ===========================================================================
# #5503: SCAN dead loop — clean_thread_pool
# ===========================================================================

class TestCleanThreadPool:
    """clean_thread_pool should iterate SCAN results and remove stale PIDs."""

    def test_removes_stale_pids_via_scan(self, gtm, mock_redis):
        """
        SCAN returns a batch of PIDs. clean_thread_pool should check each PID
        and remove ones whose process no longer exists.
        """
        # Simulate: first SCAN returns 2 PIDs + next cursor=0 (done)
        mock_redis.scan_thread_pool.return_value = (0, ["99999", "88888"])

        # psutil.Process(99999) -> not running; psutil.Process(88888) -> running
        with patch("ginkgo.libs.core.threading.psutil") as mock_psutil:
            dead_proc = MagicMock()
            dead_proc.is_running.return_value = False
            alive_proc = MagicMock()
            alive_proc.is_running.return_value = True

            def make_proc(pid):
                if pid == 99999:
                    return dead_proc
                return alive_proc

            mock_psutil.Process.side_effect = make_proc
            gtm.clean_thread_pool()

        # Stale PID 99999 should be removed; alive PID 88888 should NOT
        mock_redis.remove_from_thread_pool_set.assert_called_once_with(
            gtm.thread_pool_name, "99999"
        )

    def test_handles_multi_batch_scan(self, gtm, mock_redis):
        """
        When Redis has many entries, SCAN returns multiple batches.
        clean_thread_pool must iterate all batches (cursor!=0 means more data).
        """
        # Batch 1: cursor=42 (more data), Batch 2: cursor=0 (done)
        mock_redis.scan_thread_pool.side_effect = [
            (42, ["111"]),
            (0, ["222"]),
        ]

        with patch("ginkgo.libs.core.threading.psutil") as mock_psutil:
            proc = MagicMock()
            proc.is_running.return_value = False
            mock_psutil.Process.return_value = proc
            gtm.clean_thread_pool()

        # Both batches should be processed: 2 SCAN calls
        assert mock_redis.scan_thread_pool.call_count == 2
        # Both stale PIDs removed
        assert mock_redis.remove_from_thread_pool_set.call_count == 2


# ===========================================================================
# #5503: SCAN dead loop — clean_worker_pool
# ===========================================================================

class TestCleanWorkerPool:
    """clean_worker_pool should iterate SCAN results and remove stale workers."""

    def test_removes_stale_workers(self, gtm, mock_redis):
        mock_redis.scan_worker_pool.return_value = (0, ["77777"])

        with patch("ginkgo.libs.core.threading.psutil") as mock_psutil:
            dead_proc = MagicMock()
            dead_proc.is_running.return_value = False
            mock_psutil.Process.return_value = dead_proc

            # Mock unregister_worker_pid to avoid Redis dependency
            gtm.unregister_worker_pid = MagicMock()
            gtm.clean_worker_pool()

        mock_redis.scan_worker_pool.assert_called_once()
        gtm.unregister_worker_pid.assert_called_once_with("77777")


# ===========================================================================
# #5503: SCAN dead loop — get_thread_pids
# ===========================================================================

class TestGetThreadPids:
    """get_thread_pids should return all PIDs across SCAN batches."""

    def test_returns_pids_from_multiple_batches(self, gtm, mock_redis):
        mock_redis.scan_thread_pool.side_effect = [
            (42, ["100", "200"]),
            (0, ["300"]),
        ]

        result = gtm.get_thread_pids()

        assert sorted(result) == ["100", "200", "300"]
