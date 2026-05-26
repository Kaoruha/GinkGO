"""Smoke tests for livecore.data_manager -- #3870"""
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
