"""Smoke tests for livecore.main -- #3870"""
import pytest

try:
    from ginkgo.livecore.main import LiveCore
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="LiveCore not available")
class TestLiveCore:
    def test_instantiation(self):
        core = LiveCore()
        assert core is not None

    def test_instantiation_with_config(self):
        core = LiveCore(config={"test": True})
        assert core is not None

    def test_instantiation_disable_live(self):
        core = LiveCore(enable_live_engine=False)
        assert core is not None
