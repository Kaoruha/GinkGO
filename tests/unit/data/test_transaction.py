from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from ginkgo.data.transaction import get_transaction_session, transaction_scope


@pytest.mark.unit
class TestTransactionScope:
    def test_nested_scope_reuses_active_session(self):
        session = MagicMock()
        factory_calls = 0

        @contextmanager
        def factory():
            nonlocal factory_calls
            factory_calls += 1
            yield session
            session.commit()

        @contextmanager
        def fail_factory():
            raise AssertionError("nested transaction should reuse active session")
            yield

        with transaction_scope("mysql", factory) as outer:
            assert outer is session
            assert get_transaction_session("mysql") is session

            with transaction_scope("mysql", fail_factory) as inner:
                assert inner is session

        assert factory_calls == 1
        session.commit.assert_called_once()
        assert get_transaction_session("mysql") is None
