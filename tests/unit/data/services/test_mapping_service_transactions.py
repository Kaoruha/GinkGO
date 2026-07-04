from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.mapping_service import MappingService


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


def _make_service(session):
    with patch("ginkgo.libs.GLOG"):
        engine_portfolio = MagicMock()
        engine_portfolio.get_session.side_effect = lambda: _session_manager(session)
        handler = MagicMock()
        handler.get_session.side_effect = lambda: _session_manager(session)
        return MappingService(engine_portfolio, MagicMock(), handler, MagicMock())


@pytest.mark.unit
def test_cleanup_by_names_does_not_commit_inside_managed_session():
    session = MagicMock()
    session.execute.side_effect = [MagicMock(rowcount=1), MagicMock(rowcount=2), MagicMock(rowcount=3)]
    service = _make_service(session)

    result = service.cleanup_by_names()

    assert result.success
    assert session.execute.call_count == 3
    session.commit.assert_not_called()


@pytest.mark.unit
def test_cleanup_orphaned_handler_mappings_does_not_commit_inside_managed_session():
    session = MagicMock()
    session.execute.side_effect = [MagicMock(rowcount=1), MagicMock(rowcount=2)]
    service = _make_service(session)

    result = service.cleanup_orphaned_handler_mappings()

    assert result.success
    assert session.execute.call_count == 2
    session.commit.assert_not_called()


@pytest.mark.unit
def test_cleanup_handler_mappings_by_names_does_not_commit_inside_managed_session():
    session = MagicMock()
    session.execute.return_value = MagicMock(rowcount=4)
    service = _make_service(session)

    result = service.cleanup_handler_mappings_by_names()

    assert result.success
    session.execute.assert_called_once()
    session.commit.assert_not_called()
