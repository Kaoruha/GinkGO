"""Smoke tests for livecore.data_sync_service -- #3870"""
import pytest
from unittest.mock import MagicMock

try:
    from ginkgo.livecore.data_sync_service import DataSyncService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="DataSyncService not available")
class TestDataSyncService:
    def test_instantiation(self):
        svc = DataSyncService()
        assert svc is not None

    def test_get_sync_status_invalid(self):
        svc = DataSyncService()
        result = svc.get_sync_status("nonexistent-uuid")
        # Should return None for unknown broker
        assert result is None

    def test_full_sync_check_invalid(self):
        svc = DataSyncService()
        result = svc.full_sync_check("nonexistent-uuid")
        assert isinstance(result, bool)

    def test_stop_all_sync(self):
        svc = DataSyncService()
        svc.stop_all_sync()  # Should not raise
