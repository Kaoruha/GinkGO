import pytest
from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES


@pytest.mark.tdd
class TestOfflineState:
    def test_offline_value_is_7(self):
        assert PORTFOLIO_RUNSTATE_TYPES.OFFLINE.value == 7

    def test_offline_exists_in_enum(self):
        assert hasattr(PORTFOLIO_RUNSTATE_TYPES, "OFFLINE")

    def test_other_values_unchanged(self):
        assert PORTFOLIO_RUNSTATE_TYPES.RUNNING.value == 1
        assert PORTFOLIO_RUNSTATE_TYPES.PAUSED.value == 2
        assert PORTFOLIO_RUNSTATE_TYPES.STOPPED.value == 4
