from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.drivers import add, add_all
from ginkgo.data.models import MBar


def _make_bar(code: str, day: int) -> MBar:
    return MBar(
        code=code,
        timestamp=datetime(2023, 12, day, 9, 30),
        open=Decimal("100.0"),
        close=Decimal("101.0"),
        high=Decimal("102.0"),
        low=Decimal("99.0"),
        volume=1000000,
        amount=Decimal("101000000.0"),
        frequency=1,
    )


@pytest.mark.unit
class TestTransactionAwareDriverHelpers:
    def test_add_reuses_provided_session(self):
        session = MagicMock()
        bar = _make_bar("ADD.SZ", 1)

        with patch("ginkgo.data.drivers.get_db_connection", side_effect=AssertionError("should not open a new session")):
            result = add(bar, session=session)

        assert result is bar
        session.add.assert_called_once_with(bar)
        session.flush.assert_called_once()
        session.refresh.assert_called_once_with(bar)
        session.expunge.assert_called_once_with(bar)

    def test_add_all_reuses_provided_session_for_clickhouse_batch(self):
        session = MagicMock()
        bars = [_make_bar("BATCH.SZ", 1), _make_bar("BATCH.SZ", 2)]

        with patch(
            "ginkgo.data.drivers.get_click_connection",
            side_effect=AssertionError("should not open a new ClickHouse session"),
        ):
            click_count, mysql_count = add_all(bars, session=session)

        assert click_count == 2
        assert mysql_count == 0
        session.bulk_insert_mappings.assert_called_once()
