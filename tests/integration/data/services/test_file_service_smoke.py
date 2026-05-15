"""
FileService smoke test.

Verifies the core file lifecycle through real services:
query existing → count → type listing

Run: pytest tests/integration/data/services/test_file_service_smoke.py -v -s
"""

import pytest

from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES
from ginkgo.libs import GCONF


@pytest.fixture(scope="module", autouse=True)
def ensure_debug():
    GCONF.set_debug(True)


@pytest.fixture(scope="module")
def file_svc():
    return container.file_service()


class TestFileServiceSmoke:
    """Core FileService query smoke test."""

    def test_get_strategies(self, file_svc):
        result = file_svc.get(file_type=FILE_TYPES.STRATEGY)
        assert result.is_success()
        assert "files" in result.data
        assert result.data["count"] >= 0

    def test_get_by_name(self, file_svc):
        result = file_svc.get_by_name("random_signal_strategy", FILE_TYPES.STRATEGY)
        assert result.is_success()
        files = result.data["files"]
        assert len(files) > 0
        assert files[0].name == "random_signal_strategy"

    def test_count(self, file_svc):
        result = file_svc.count()
        assert result.is_success()
        assert result.data["count"] >= 0

    def test_get_available_types(self, file_svc):
        result = file_svc.get_available_types()
        assert result.is_success()
        assert result.data["count"] > 0

    def test_get_content(self, file_svc):
        # Get a known strategy, then fetch its content
        get_result = file_svc.get_by_name("no_risk", FILE_TYPES.RISKMANAGER)
        assert get_result.is_success()
        files = get_result.data["files"]
        if not files:
            pytest.skip("no_risk not found in database")
        file_id = files[0].uuid

        content_result = file_svc.get_content(file_id)
        assert content_result.is_success()
        assert content_result.data is not None
        assert len(content_result.data) > 0

    def test_exists_known_file(self, file_svc):
        result = file_svc.exists(name="random_signal_strategy")
        assert result.is_success()
        assert result.data is True
