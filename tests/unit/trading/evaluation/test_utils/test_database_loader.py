"""
Unit tests for DatabaseStrategyLoader (T097-T099).

Tests for loading strategies from database with automatic cleanup.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ginkgo.data.models import MFile, MPortfolioFileMapping
from ginkgo.enums import FILE_TYPES
from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader


@pytest.mark.unit
@pytest.mark.tdd
class TestDatabaseStrategyLoaderLoadByFileId:
    """Unit tests for DatabaseStrategyLoader.load_by_file_id() (T097)."""

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_load_by_file_id_success(self, mock_container):
        """
        Test loading strategy by file_id (T097).

        Expected: Should create temp file with decoded content.
        """
        # Mock strategy code
        strategy_code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from typing import List, Dict

class TestStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info: Dict, event) -> List[Signal]:
        return []
"""

        # Mock MFile record
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "test-file-uuid-1234"
        mock_file.name = "test_strategy.py"
        mock_file.data = strategy_code.encode("utf-8")
        mock_file.type = FILE_TYPES.STRATEGY

        # Mock file_crud
        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]
        mock_container.file_crud.return_value = mock_file_crud

        # Create loader and load strategy
        loader = DatabaseStrategyLoader()
        with loader.load_by_file_id("test-file-uuid") as temp_path:
            # Verify temp file was created
            assert temp_path.exists()
            assert temp_path.suffix == ".py"

            # Verify content matches
            content = temp_path.read_text(encoding="utf-8")
            assert "class TestStrategy" in content
            assert "BaseStrategy" in content

        # Verify temp file was cleaned up after context exit
        assert not temp_path.exists()

        # Verify CRUD was called correctly
        mock_file_crud.find.assert_called_once_with(
            filters={"uuid": "test-file-uuid"}, page_size=1
        )

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_load_by_file_id_not_found(self, mock_container):
        """
        Test loading non-existent file_id (T097).

        Expected: Should raise FileNotFoundError.
        """
        # Mock file_crud to return empty list
        mock_file_crud = Mock()
        mock_file_crud.find.return_value = []
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="File not found in database"):
            with loader.load_by_file_id("non-existent-uuid"):
                pass

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_load_by_file_id_decode_error(self, mock_container):
        """
        Test loading file with invalid UTF-8 data (T097).

        Expected: Should raise ValueError for decode errors.
        """
        # Mock MFile with invalid UTF-8 data
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "test-file-uuid"
        mock_file.name = "test.py"
        mock_file.data = b"\xff\xfe invalid utf-8"
        mock_file.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        # Should raise ValueError
        with pytest.raises(ValueError, match="Failed to decode file data"):
            with loader.load_by_file_id("test-file-uuid"):
                pass


@pytest.mark.unit
@pytest.mark.tdd
class TestDatabaseStrategyLoaderLoadByPortfolioId:
    """Unit tests for DatabaseStrategyLoader.load_by_portfolio_id() (T098)."""

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_load_by_portfolio_id_success(self, mock_container):
        """
        Test loading strategy by portfolio_id (T098).

        Expected: Should resolve file_id from mapping and load strategy.
        """
        # Mock strategy code
        strategy_code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
class PortfolioStrategy(BaseStrategy):
    __abstract__ = False
    def cal(self, portfolio_info, event):
        return []
"""

        # Mock MFile record
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "file-id-from-portfolio"
        mock_file.name = "portfolio_strategy.py"
        mock_file.data = strategy_code.encode("utf-8")
        mock_file.type = FILE_TYPES.STRATEGY

        # Mock MPortfolioFileMapping record
        mock_mapping = Mock(spec=MPortfolioFileMapping)
        mock_mapping.portfolio_id = "test-portfolio-uuid"
        mock_mapping.file_id = "file-id-from-portfolio"

        # Mock CRUDs
        mock_mapping_crud = Mock()
        mock_mapping_crud.find.return_value = [mock_mapping]

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]

        mock_container.portfolio_file_mapping_crud.return_value = mock_mapping_crud
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        # Load by portfolio_id
        with loader.load_by_portfolio_id("test-portfolio-uuid") as temp_path:
            # Verify temp file was created
            assert temp_path.exists()
            content = temp_path.read_text(encoding="utf-8")
            assert "class PortfolioStrategy" in content

        # Verify mapping CRUD was called
        mock_mapping_crud.find.assert_called_once_with(
            filters={"portfolio_id": "test-portfolio-uuid"}, page_size=1
        )

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_load_by_portfolio_id_not_found(self, mock_container):
        """
        Test loading with non-existent portfolio_id (T098).

        Expected: Should raise FileNotFoundError.
        """
        mock_mapping_crud = Mock()
        mock_mapping_crud.find.return_value = []
        mock_container.portfolio_file_mapping_crud.return_value = mock_mapping_crud

        loader = DatabaseStrategyLoader()

        with pytest.raises(FileNotFoundError, match="Portfolio not found in database"):
            with loader.load_by_portfolio_id("non-existent-portfolio"):
                pass


@pytest.mark.unit
@pytest.mark.tdd
class TestDatabaseStrategyLoaderTempFileCleanup:
    """Unit tests for temporary file cleanup (T099)."""

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_temp_file_cleanup_on_success(self, mock_container):
        """
        Test temp file cleanup after successful loading (T099).

        Expected: Temp file should be deleted after context exit.
        """
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "cleanup-test"
        mock_file.name = "cleanup_strategy.py"
        mock_file.data = "print('cleanup test')".encode("utf-8")
        mock_file.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        temp_path = None
        with loader.load_by_file_id("cleanup-test") as path:
            temp_path = path
            # File should exist inside context
            assert temp_path.exists()

        # File should be deleted after context exit
        assert not temp_path.exists()

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_temp_file_cleanup_on_exception(self, mock_container):
        """
        Test temp file cleanup even when exception occurs (T099).

        Expected: Temp file should be deleted even on error.
        """
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "exception-test"
        mock_file.name = "exception_strategy.py"
        mock_file.data = "invalid python code {{{".encode("utf-8")
        mock_file.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        temp_path = None
        try:
            with loader.load_by_file_id("exception-test") as path:
                temp_path = path
                # Raise exception inside context
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass

        # File should still be cleaned up
        if temp_path:
            assert not temp_path.exists()

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_temp_file_cleanup_with_contextmanager(self, mock_container):
        """
        Test that @contextmanager ensures cleanup in finally block (T099).

        Expected: Cleanup should happen regardless of how context exits.
        """
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "finally-test"
        mock_file.name = "finally_strategy.py"
        mock_file.data = "class Test: pass".encode("utf-8")
        mock_file.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        # Test normal exit
        with loader.load_by_file_id("finally-test") as path:
            temp_path = path
            assert temp_path.exists()
        assert not temp_path.exists()

        # Test with break
        for _ in range(1):
            with loader.load_by_file_id("finally-test") as path:
                temp_path = path
                assert temp_path.exists()
                break
        assert not temp_path.exists()

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_temp_file_in_temp_directory(self, mock_container):
        """
        Test temp file is created in system temp directory (T099).

        Expected: Temp file should be in /tmp or equivalent.
        """
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "location-test"
        mock_file.name = "location_strategy.py"
        mock_file.data = "# test".encode("utf-8")
        mock_file.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()

        with loader.load_by_file_id("location-test") as temp_path:
            # Should be in temp directory
            temp_dir = Path(tempfile.gettempdir())
            assert temp_path.parent == temp_dir or str(temp_dir) in str(temp_path)


@pytest.mark.unit
@pytest.mark.tdd
class TestDatabaseStrategyLoaderListStrategies:
    """Unit tests for DatabaseStrategyLoader.list_strategies()."""

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_list_strategies_empty(self, mock_container):
        """Test listing strategies when database is empty."""
        mock_file_crud = Mock()
        mock_file_crud.find.return_value = []
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()
        strategies = loader.list_strategies()
        assert strategies == []

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_list_strategies_with_data(self, mock_container):
        """Test listing strategies returns correct info."""
        # Create mock files
        mock_file1 = Mock(spec=MFile)
        mock_file1.uuid = "strategy-1-uuid"
        mock_file1.name = "FirstStrategy.py"
        mock_file1.type = FILE_TYPES.STRATEGY

        mock_file2 = Mock(spec=MFile)
        mock_file2.uuid = "strategy-2-uuid"
        mock_file2.name = "SecondStrategy.py"
        mock_file2.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file1, mock_file2]

        mock_mapping_crud = Mock()
        mock_mapping_crud.find.return_value = []

        mock_container.file_crud.return_value = mock_file_crud
        mock_container.portfolio_file_mapping_crud.return_value = mock_mapping_crud

        loader = DatabaseStrategyLoader()
        strategies = loader.list_strategies()

        assert len(strategies) == 2
        assert strategies[0]["file_id"] == "strategy-1-uuid"
        assert strategies[0]["name"] == "FirstStrategy.py"
        assert strategies[0]["portfolio_count"] == 0
        assert strategies[1]["file_id"] == "strategy-2-uuid"
        assert strategies[1]["name"] == "SecondStrategy.py"

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_list_strategies_with_filter(self, mock_container):
        """Test name filter works correctly."""
        mock_file1 = Mock(spec=MFile)
        mock_file1.uuid = "test-1"
        mock_file1.name = "MyTestStrategy.py"
        mock_file1.type = FILE_TYPES.STRATEGY

        mock_file2 = Mock(spec=MFile)
        mock_file2.uuid = "test-2"
        mock_file2.name = "OtherStrategy.py"
        mock_file2.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file1, mock_file2]

        mock_mapping_crud = Mock()
        mock_mapping_crud.find.return_value = []

        mock_container.file_crud.return_value = mock_file_crud
        mock_container.portfolio_file_mapping_crud.return_value = mock_mapping_crud

        loader = DatabaseStrategyLoader()

        # Filter for "Test"
        strategies = loader.list_strategies(name_filter="Test")

        assert len(strategies) == 1
        assert strategies[0]["name"] == "MyTestStrategy.py"


@pytest.mark.unit
@pytest.mark.tdd
class TestDatabaseStrategyLoaderGetStrategyInfo:
    """Unit tests for DatabaseStrategyLoader.get_strategy_info()."""

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_get_strategy_info_success(self, mock_container):
        """Test getting strategy info returns correct data."""
        mock_file = Mock(spec=MFile)
        mock_file.uuid = "info-test-uuid"
        mock_file.name = "InfoStrategy.py"
        mock_file.type = FILE_TYPES.STRATEGY

        mock_file_crud = Mock()
        mock_file_crud.find.return_value = [mock_file]

        mock_mapping_crud = Mock()
        mock_mapping_crud.find.return_value = []

        mock_container.file_crud.return_value = mock_file_crud
        mock_container.portfolio_file_mapping_crud.return_value = mock_mapping_crud

        loader = DatabaseStrategyLoader()
        info = loader.get_strategy_info("info-test-uuid")

        assert info is not None
        assert info["file_id"] == "info-test-uuid"
        assert info["name"] == "InfoStrategy.py"
        assert info["type"] == FILE_TYPES.STRATEGY
        assert info["portfolio_count"] == 0

    @patch("ginkgo.trading.evaluation.utils.database_loader.container")
    def test_get_strategy_info_not_found(self, mock_container):
        """Test getting info for non-existent strategy returns None."""
        mock_file_crud = Mock()
        mock_file_crud.find.return_value = []
        mock_container.file_crud.return_value = mock_file_crud

        loader = DatabaseStrategyLoader()
        info = loader.get_strategy_info("non-existent")
        assert info is None
