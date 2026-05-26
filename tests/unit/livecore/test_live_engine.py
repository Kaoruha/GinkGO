"""Smoke tests for livecore.live_engine -- #3870"""
import pytest
from unittest.mock import patch, MagicMock

try:
    from ginkgo.livecore.live_engine import LiveEngine
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="LiveEngine not available")
class TestLiveEngine:
    def test_instantiation(self):
        engine = LiveEngine()
        assert engine is not None

    def test_initial_state(self):
        engine = LiveEngine()
        assert engine.is_running() is False

    def test_get_component_status(self):
        engine = LiveEngine()
        status = engine.get_component_status()
        assert isinstance(status, dict)

    @patch('ginkgo.livecore.live_engine.container')
    def test_initialize_no_accounts(self, mock_container):
        mock_container.live_account_service.return_value.get_active_accounts.return_value = []
        engine = LiveEngine()
        result = engine.initialize()
        assert isinstance(result, bool)
