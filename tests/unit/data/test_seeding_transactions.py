from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, mock_open, patch

import pytest

from ginkgo.data.seeding import DataSeeder


def _session_manager(session):
    @contextmanager
    def _manager():
        yield session

    return _manager()


@pytest.mark.unit
def test_create_example_engine_does_not_commit_inside_managed_session():
    seeder = DataSeeder()
    session = MagicMock()
    session.execute.return_value = MagicMock(rowcount=1)
    engine_crud = MagicMock()
    engine_crud.get_session.side_effect = lambda: _session_manager(session)
    engine_service = MagicMock()
    engine_service.add.return_value = SimpleNamespace(success=False, error="boom")

    with patch("ginkgo.data.crud.engine_crud.EngineCRUD", return_value=engine_crud), \
         patch("ginkgo.data.seeding.container.engine_service", return_value=engine_service):
        seeder._create_example_engine()

    session.commit.assert_not_called()


@pytest.mark.unit
def test_create_example_files_does_not_commit_inside_managed_session():
    seeder = DataSeeder()
    session = MagicMock()
    session.execute.return_value = MagicMock(rowcount=1)
    file_crud = MagicMock()
    file_crud.get_session.side_effect = lambda: _session_manager(session)
    file_service = MagicMock()
    file_service.add.return_value = SimpleNamespace(success=True, data={"file_info": {"uuid": "f-1"}})

    with patch("ginkgo.data.crud.file_crud.FileCRUD", return_value=file_crud), \
         patch("ginkgo.data.seeding.container.file_service", return_value=file_service), \
         patch("ginkgo.libs.core.config.GinkgoConfig.WORKING_PATH", new_callable=PropertyMock, return_value="/tmp/work"), \
         patch("ginkgo.data.seeding.os.path.isdir", return_value=True), \
         patch("ginkgo.data.seeding.os.listdir", return_value=["alpha.py"]), \
         patch("builtins.open", mock_open(read_data=b"print('x')")):
        count = seeder._create_example_files()

    assert count == 5
    session.commit.assert_not_called()


@pytest.mark.unit
def test_create_single_portfolio_does_not_commit_inside_managed_session():
    seeder = DataSeeder()
    session = MagicMock()
    session.execute.return_value = MagicMock(rowcount=1)
    portfolio_crud = MagicMock()
    portfolio_crud.get_session.side_effect = lambda: _session_manager(session)
    portfolio_service = MagicMock()
    portfolio_service.add.return_value = SimpleNamespace(success=False, error="boom")

    with patch("ginkgo.data.crud.portfolio_crud.PortfolioCRUD", return_value=portfolio_crud):
        seeder._create_single_portfolio(portfolio_service, "present_portfolio", is_live=False)

    session.commit.assert_not_called()
