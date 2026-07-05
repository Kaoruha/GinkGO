from unittest.mock import MagicMock

import pytest

from ginkgo.data.crud import BarCRUD


@pytest.mark.unit
class TestBaseCRUDTransactionBehavior:
    def test_remove_with_provided_session_does_not_commit_or_close(self):
        crud = BarCRUD()
        session = MagicMock()
        session.execute.return_value.rowcount = 1

        crud.remove(filters={"code": "000001.SZ"}, session=session)

        session.execute.assert_called_once()
        session.commit.assert_not_called()
        session.close.assert_not_called()


    def test_replace_reuses_single_transaction_session_for_all_steps(self):
        crud = BarCRUD()
        transaction_session = object()
        existing = [MagicMock()]
        inserted = [MagicMock()]
        seen_sessions = []

        from contextlib import contextmanager

        @contextmanager
        def fake_scope(session=None):
            assert session is None
            yield transaction_session

        def fake_find(*args, **kwargs):
            seen_sessions.append(("find", kwargs.get("session")))
            return existing

        def fake_remove(*args, **kwargs):
            seen_sessions.append(("remove", kwargs.get("session")))
            return len(existing)

        def fake_add_batch(*args, **kwargs):
            seen_sessions.append(("add_batch", kwargs.get("session")))
            return inserted

        crud._session_scope = fake_scope
        crud.find = fake_find
        crud.remove = fake_remove
        crud.add_batch = fake_add_batch

        result = crud.replace(filters={"code": "000001.SZ"}, new_items=[MagicMock(spec=crud.model_class)])

        assert result is inserted
        assert seen_sessions == [
            ("find", transaction_session),
            ("remove", transaction_session),
            ("add_batch", transaction_session),
        ]
