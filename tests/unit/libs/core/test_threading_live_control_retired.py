"""
Tests for the retired Kafka live-engine launch path (#6118 / #5573).

#6118/#5573: run_live / run_live_daemon referenced a never-existing module
       (ginkgo.trading.engines.live_engine) — a perpetually-broken import that
       failed before #5573's f-string interpolation of an untrusted id could
       even execute. The Kafka live-launch design was superseded by
       livecore/main.py (config + enable_live_engine + get_live_engine).

Disposition: delete run_live / run_live_daemon; the run_live / stop_live
main-control command branches are retired (log a warning pointing at
livecore/main.py) instead of spawning a subprocess or importing the
non-existent engine.
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Create a mock RedisService."""
    return MagicMock()


@pytest.fixture
def gtm(mock_redis):
    """Create a GTM instance with injected mock Redis."""
    from ginkgo.libs.core.threading import GinkgoThreadManager
    return GinkgoThreadManager(redis_service=mock_redis)


# ===========================================================================
# #6118 / #5573 — run_live / stop_live main-control commands are retired
# ===========================================================================

class TestRunLiveCommandRetired:
    """The Kafka live-launch design was superseded by livecore/main.py.
    run_live/stop_live commands must NOT spawn a subprocess or reference the
    never-existing ginkgo.trading.engines.live_engine module."""

    def test_run_live_command_does_not_spawn_subprocess(self, gtm, mock_redis):
        with patch("ginkgo.libs.core.threading.subprocess.run") as mock_run, \
             patch("ginkgo.libs.core.threading.subprocess.Popen") as mock_popen:
            gtm.process_main_control_command({"type": "run_live", "id": "anything"})
        mock_run.assert_not_called()
        mock_popen.assert_not_called()

    def test_stop_live_command_does_not_spawn_subprocess(self, gtm, mock_redis):
        with patch("ginkgo.libs.core.threading.subprocess.run") as mock_run, \
             patch("ginkgo.libs.core.threading.subprocess.Popen") as mock_popen:
            gtm.process_main_control_command({"type": "stop_live", "id": "anything"})
        mock_run.assert_not_called()
        mock_popen.assert_not_called()


# ===========================================================================
# #6118 / #5573 — dead stubs fully removed (refactor guard)
# ===========================================================================

class TestDeadLiveEngineStubsRemoved:
    """The broken run_live/run_live_daemon stubs and the never-existing
    trading.engines.live_engine import must be fully removed from the module."""

    def test_no_dead_live_engine_import_in_source(self):
        import inspect
        import ginkgo.libs.core.threading as mod

        src = inspect.getsource(mod)
        # The never-existing import must not be EXECUTED and LiveEngine must not be
        # instantiated anywhere in code. (Comments may legitimately reference the
        # retired path to explain history, so only check non-comment lines.)
        code_lines = [
            ln for ln in src.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "from ginkgo.trading.engines.live_engine" not in code, (
            "dead import statement still present in code"
        )
        assert "LiveEngine(" not in code, "LiveEngine still instantiated in code"

    def test_run_live_daemon_removed(self, gtm):
        assert not hasattr(gtm, "run_live_daemon"), "run_live_daemon stub still present"
        assert not hasattr(gtm, "run_live"), "run_live stub still present"
