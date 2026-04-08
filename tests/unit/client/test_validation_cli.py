"""
性能: 221MB RSS, 1.92s, 15 tests [PASS]
Unit tests for validation_cli.py commands: validate (standalone command).

Validation CLI is registered as a single command on the main app:
  _main_app.command(name="validate")(validate)

The validate function is the default command (name="") on validation_cli.app,
so invocation is: validation_cli.app, ["--option", "value", "file.py"]

Mock strategy:
  - _list_database_strategies imports DatabaseStrategyLoader inside -> patch at import site
  - File-based validation delegates to _validate_single_strategy -> patch it
  - Error paths (invalid type, no source, file not found) are handled before heavy imports
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ginkgo.client import validation_cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def valid_strategy_file(tmp_path):
    """Create a minimal valid strategy file for testing."""
    content = '''
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES

class MyTestStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        return []
'''
    p = tmp_path / "strategy.py"
    p.write_text(content)
    return p


# ============================================================================
# 1. Help tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestHelp:
    """Verify help output for validate command."""

    def test_validate_help_shows_options(self, cli_runner):
        result = cli_runner.invoke(validation_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "--type" in result.output
        assert "--format" in result.output
        assert "--file-id" in result.output
        assert "--list" in result.output

    def test_validate_help_shows_examples(self, cli_runner):
        result = cli_runner.invoke(validation_cli.app, ["--help"])
        assert result.exit_code == 0
        assert "ginkgo validate" in result.output


# ============================================================================
# 2. Validation errors (no source, invalid type, invalid format)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestValidateErrors:
    """Tests for validation error paths."""

    def test_no_source_specified(self, cli_runner):
        result = cli_runner.invoke(validation_cli.app, [])
        assert result.exit_code == 1
        assert "No component source specified" in result.output

    def test_invalid_type(self, cli_runner):
        result = cli_runner.invoke(validation_cli.app, [
            "--type", "invalid_type"
        ])
        assert result.exit_code == 1
        assert "Invalid type" in result.output

    def test_invalid_format(self, cli_runner):
        result = cli_runner.invoke(validation_cli.app, [
            "somefile.py", "--format", "xml"
        ])
        assert result.exit_code == 1
        assert "Invalid format" in result.output

    def test_file_not_found(self, cli_runner):
        result = cli_runner.invoke(validation_cli.app, [
            "nonexistent_file.py"
        ])
        assert result.exit_code == 2
        assert "File not found" in result.output

    def test_multiple_sources_mutually_exclusive(self, cli_runner):
        """Cannot specify both file and --file-id."""
        with patch("ginkgo.trading.evaluation.utils.database_loader.DatabaseStrategyLoader"):
            result = cli_runner.invoke(validation_cli.app, [
                "somefile.py", "--file-id", "uuid-123"
            ])
        assert result.exit_code == 1
        assert "multiple component sources" in result.output


# ============================================================================
# 3. File-based validation happy path
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestFileValidation:
    """Tests for file-based validation."""

    def test_validate_strategy_file(self, cli_runner, valid_strategy_file):
        with patch.object(validation_cli, '_validate_single_strategy') as mock_validate:
            result = cli_runner.invoke(validation_cli.app, [
                str(valid_strategy_file), "--type", "strategy"
            ])
        assert result.exit_code == 0
        mock_validate.assert_called_once()

    def test_validate_with_verbose(self, cli_runner, valid_strategy_file):
        with patch.object(validation_cli, '_validate_single_strategy') as mock_validate:
            result = cli_runner.invoke(validation_cli.app, [
                str(valid_strategy_file), "--verbose"
            ])
        assert result.exit_code == 0
        mock_validate.assert_called_once()
        # Verify verbose flag was passed (4th positional arg)
        call_args = mock_validate.call_args[0]
        assert call_args[4] is True  # verbose is the 5th positional argument


# ============================================================================
# 4. Database-related commands
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestDatabaseValidation:
    """Tests for database-based validation commands."""

    def test_list_strategies_empty(self, cli_runner):
        mock_loader = MagicMock()
        mock_loader.list_strategies.return_value = []
        with patch("ginkgo.trading.evaluation.utils.database_loader.DatabaseStrategyLoader", return_value=mock_loader):
            result = cli_runner.invoke(validation_cli.app, ["--list"])
        assert result.exit_code == 0
        assert "No strategies found" in result.output

    def test_list_strategies_with_data(self, cli_runner):
        mock_loader = MagicMock()
        mock_loader.list_strategies.return_value = [
            {"file_id": "uuid-aaaa-bbbb-cccc", "name": "TestStrategy", "portfolio_count": 2}
        ]
        with patch("ginkgo.trading.evaluation.utils.database_loader.DatabaseStrategyLoader", return_value=mock_loader):
            result = cli_runner.invoke(validation_cli.app, ["--list"])
        assert result.exit_code == 0
        assert "TestStrategy" in result.output
        assert "Total: 1" in result.output


# ============================================================================
# 5. Helper function tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_get_format_extension_text(self):
        assert validation_cli._get_format_extension("text") == "txt"

    def test_get_format_extension_json(self):
        assert validation_cli._get_format_extension("json") == "json"

    def test_get_format_extension_markdown(self):
        assert validation_cli._get_format_extension("markdown") == "md"

    def test_get_format_extension_unknown(self):
        assert validation_cli._get_format_extension("unknown") == "txt"
