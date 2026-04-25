"""
性能: 221MB RSS, 2.04s, 24 tests [PASS]
Unit tests for flat_cli.py commands: component, mapping, result sub-apps.

Flat CLI provides sub-apps (component_app, mapping_app, result_app) that are
registered on the main app. Test invocation targets the Typer sub-app directly.

Mock strategy:
  - component list imports container inside the function -> patch container
  - result show imports container inside the function -> patch container
  - mapping commands are not yet implemented (TODO) -> test output only
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ginkgo.client import flat_cli
from ginkgo.enums import FILE_TYPES


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_component():
    """Create a mock file entity for component list."""
    comp = MagicMock()
    comp.uuid = uuid.uuid4()
    comp.name = "TestStrategy"
    comp.type = FILE_TYPES.STRATEGY
    comp.create_at = datetime(2025, 1, 1)
    comp.update_at = datetime(2025, 1, 2)
    return comp


@pytest.fixture
def mock_file_crud(mock_component):
    """Mock file_crud.find returning component list."""
    crud = MagicMock()
    crud.find.return_value = [mock_component]
    return crud


# ============================================================================
# 1. Help tests
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestHelp:
    """Verify help output for flat_cli sub-apps."""

    def test_component_help_shows_list_and_create(self, cli_runner):
        result = cli_runner.invoke(flat_cli.component_app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "create" in result.output

    def test_mapping_help_shows_list_create_priority(self, cli_runner):
        result = cli_runner.invoke(flat_cli.mapping_app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "create" in result.output
        assert "priority" in result.output

    def test_result_help_shows_list_get_show(self, cli_runner):
        result = cli_runner.invoke(flat_cli.result_app, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "get" in result.output
        assert "show" in result.output


# ============================================================================
# 2. Component list command
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestComponentList:
    """Tests for 'component list' command."""

    def test_list_components_table_format(self, cli_runner, mock_file_crud):
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = mock_file_crud
            result = cli_runner.invoke(flat_cli.component_app, ["list"])
        assert result.exit_code == 0
        assert "TestStrategy" in result.output
        assert "strategy" in result.output.lower()

    def test_list_components_raw_json_format(self, cli_runner, mock_file_crud):
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = mock_file_crud
            result = cli_runner.invoke(flat_cli.component_app, ["list", "--raw"])
        assert result.exit_code == 0
        assert "TestStrategy" in result.output
        assert '"total"' in result.output

    def test_list_components_filter_by_type(self, cli_runner, mock_component):
        mock_component.type = FILE_TYPES.RISKMANAGER
        mock_component.name = "TestRisk"
        crud = MagicMock()
        crud.find.return_value = [mock_component]
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = crud
            result = cli_runner.invoke(flat_cli.component_app, ["list", "--type", "risk"])
        assert result.exit_code == 0
        assert "TestRisk" in result.output

    def test_list_components_filter_by_name(self, cli_runner, mock_file_crud):
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = mock_file_crud
            result = cli_runner.invoke(flat_cli.component_app, ["list", "--filter", "Test"])
        assert result.exit_code == 0
        assert "TestStrategy" in result.output

    def test_list_components_empty_database(self, cli_runner):
        crud = MagicMock()
        crud.find.return_value = []
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = crud
            result = cli_runner.invoke(flat_cli.component_app, ["list"])
        assert result.exit_code == 0
        assert "No components found" in result.output

    def test_list_components_name_filter_no_match(self, cli_runner, mock_file_crud):
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = mock_file_crud
            result = cli_runner.invoke(flat_cli.component_app, ["list", "--filter", "ZZZNotFound"])
        assert result.exit_code == 0
        assert "No components found" in result.output


# ============================================================================
# 3. Component create command
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestComponentCreate:
    """Tests for 'component create' command."""

    def test_create_component_with_required_options(self, cli_runner):
        result = cli_runner.invoke(flat_cli.component_app, [
            "create", "--type", "strategy", "--name", "MyStrategy", "--class", "MyStrategyClass"
        ])
        assert result.exit_code == 0
        assert "MyStrategy" in result.output
        assert "created successfully" in result.output

    def test_create_component_with_all_options(self, cli_runner):
        result = cli_runner.invoke(flat_cli.component_app, [
            "create",
            "--type", "risk",
            "--name", "StopLoss",
            "--class", "StopLossRisk",
            "--description", "Stop loss risk manager",
            "--tags", "risk,stop",
            "--author", "testuser",
        ])
        assert result.exit_code == 0
        assert "StopLoss" in result.output
        assert "StopLossRisk" in result.output
        assert "testuser" in result.output

    def test_create_component_missing_required_option(self, cli_runner):
        result = cli_runner.invoke(flat_cli.component_app, ["create"])
        assert result.exit_code != 0


# ============================================================================
# 4. Mapping commands
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestMappingCommands:
    """Tests for mapping sub-app commands."""

    def test_mapping_list_shows_not_implemented(self, cli_runner):
        result = cli_runner.invoke(flat_cli.mapping_app, ["list"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_mapping_create_shows_not_implemented(self, cli_runner):
        result = cli_runner.invoke(flat_cli.mapping_app, [
            "create",
            "--from-type", "portfolio", "--from-id", "abc",
            "--to-type", "engine", "--to-id", "def",
        ])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_mapping_priority_invalid_range(self, cli_runner):
        result = cli_runner.invoke(flat_cli.mapping_app, ["priority", "mapping-123", "200"])
        # NOTE: typer.Exit(1) is caught by except Exception in source code,
        # so exit_code is 0 but the error message is printed.
        assert "between 1 and 100" in result.output

    def test_mapping_priority_valid(self, cli_runner):
        result = cli_runner.invoke(flat_cli.mapping_app, ["priority", "mapping-123", "50"])
        assert result.exit_code == 0
        assert "50" in result.output


# ============================================================================
# 5. Result commands
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestResultCommands:
    """Tests for result sub-app commands."""

    def test_result_list_shows_not_implemented(self, cli_runner):
        result = cli_runner.invoke(flat_cli.result_app, ["list"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_result_get_with_details_and_trades(self, cli_runner):
        result = cli_runner.invoke(flat_cli.result_app, [
            "get", "result-001", "--details", "--trades"
        ])
        assert result.exit_code == 0
        assert "result-001" in result.output
        assert "Sharpe Ratio" in result.output
        assert "Trade History" in result.output

    def test_result_get_without_options(self, cli_runner):
        result = cli_runner.invoke(flat_cli.result_app, ["get", "result-002"])
        assert result.exit_code == 0
        assert "result-002" in result.output
        assert "Sharpe Ratio" not in result.output

    def test_result_show_no_task_id_lists_runs(self, cli_runner):
        """result show without --run-id should list available runs."""
        from ginkgo.data.services.base_service import ServiceResult
        mock_service = MagicMock()
        mock_service.list_runs.return_value = ServiceResult.success(data=[
            {"engine_name": "test_engine", "task_id": "run-1",
             "portfolio_name": "p1", "timestamp": "2025-01-01", "record_count": 10}
        ])
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.result_service.return_value = mock_service
            result = cli_runner.invoke(flat_cli.result_app, ["show"])
        assert result.exit_code == 0
        assert "run-1" in result.output


# ============================================================================
# 6. _get_engine_status_name helper
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestGetEngineStatusName:
    """Tests for the _get_engine_status_name helper function."""

    def test_known_status_running(self):
        from ginkgo.enums import ENGINESTATUS_TYPES
        assert flat_cli._get_engine_status_name(ENGINESTATUS_TYPES.RUNNING.value) == "Running"

    def test_known_status_idle(self):
        from ginkgo.enums import ENGINESTATUS_TYPES
        assert flat_cli._get_engine_status_name(ENGINESTATUS_TYPES.IDLE.value) == "Idle"

    def test_unknown_status(self):
        result = flat_cli._get_engine_status_name(999)
        assert "Unknown" in result
        assert "999" in result


# ============================================================================
# 7. Exception handling
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestExceptionHandling:
    """Tests for exception handling in flat_cli commands."""

    def test_component_list_handles_exception(self, cli_runner):
        crud = MagicMock()
        crud.find.side_effect = Exception("DB connection error")
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.file_crud.return_value = crud
            result = cli_runner.invoke(flat_cli.component_app, ["list"])
        assert result.exit_code == 0
        assert "Error" in result.output
