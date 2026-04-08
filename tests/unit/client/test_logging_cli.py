"""
性能: 222MB RSS, 1.99s, 19 tests [PASS]
Unit tests for logging_cli.py commands: set-level, get-level, reset-level, whitelist.

Mock strategy:
  - Patch "ginkgo.services.logging.containers.container" for LevelService access.
  - Use ServiceResult.success() / ServiceResult.error() for return values.
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.client import logging_cli
from ginkgo.data.services.base_service import ServiceResult


# ============================================================================
# 1. Help tests (2)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestLoggingCLIHelp:
    """Verify help output for logging commands."""

    def test_root_help_shows_all_commands(self, cli_runner):
        result = cli_runner.invoke(logging_cli.app, ["--help"])
        assert result.exit_code == 0
        for name in ("set-level", "get-level", "reset-level", "whitelist"):
            assert name in result.output

    def test_set_level_help(self, cli_runner):
        result = cli_runner.invoke(logging_cli.app, ["set-level", "--help"])
        assert result.exit_code == 0
        assert "module" in result.output.lower()
        assert "level" in result.output.lower()


# ============================================================================
# 2. Main commands happy path (5)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestSetLevel:
    """Tests for the 'set-level' command."""

    def test_set_level_success(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.set_level.return_value = ServiceResult.success(message="Level set successfully")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "backtest", "DEBUG"])

        assert result.exit_code == 0
        assert "Level set successfully" in result.output or "success" in result.output.lower() or mock_service.set_level.called

    def test_set_level_info(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.set_level.return_value = ServiceResult.success(message="backtest -> INFO")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "backtest", "INFO"])

        assert result.exit_code == 0
        mock_service.set_level.assert_called_once_with("backtest", "INFO")

    def test_set_level_warning(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.set_level.return_value = ServiceResult.success(message="backtest -> WARNING")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "backtest", "WARNING"])

        assert result.exit_code == 0

    def test_set_level_error(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.set_level.return_value = ServiceResult.success(message="backtest -> ERROR")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "data", "ERROR"])

        assert result.exit_code == 0
        mock_service.set_level.assert_called_once_with("data", "ERROR")

    def test_set_level_critical(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.set_level.return_value = ServiceResult.success(message="trading -> CRITICAL")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "trading", "CRITICAL"])

        assert result.exit_code == 0


@pytest.mark.unit
@pytest.mark.cli
class TestGetLevel:
    """Tests for the 'get-level' command."""

    def test_get_level_single_module(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.get_level.return_value = "DEBUG"

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["get-level", "--module", "backtest"])

        assert result.exit_code == 0
        assert "backtest" in result.output

    def test_get_level_all_modules(self, cli_runner):
        mock_service = MagicMock()
        mock_service.get_all_levels.return_value = {
            "backtest": "INFO",
            "trading": "DEBUG",
            "data": "WARNING",
        }

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["get-level"])

        assert result.exit_code == 0
        assert "backtest" in result.output


@pytest.mark.unit
@pytest.mark.cli
class TestResetLevel:
    """Tests for the 'reset-level' command."""

    def test_reset_level_success(self, cli_runner):
        mock_service = MagicMock()
        mock_service.reset_levels.return_value = ServiceResult.success(message="All levels reset")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["reset-level"])

        assert result.exit_code == 0
        mock_service.reset_levels.assert_called_once()


@pytest.mark.unit
@pytest.mark.cli
class TestWhitelist:
    """Tests for the 'whitelist' command."""

    def test_whitelist_shows_modules(self, cli_runner):
        mock_service = MagicMock()
        mock_service.get_whitelist.return_value = ["backtest", "trading", "data", "analysis"]

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["whitelist"])

        assert result.exit_code == 0
        for mod in ("backtest", "trading", "data", "analysis"):
            assert mod in result.output


# ============================================================================
# 3. Validation / errors (5)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestSetLevelValidation:
    """Validation tests for set-level command."""

    def test_set_level_module_not_in_whitelist(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = False
        mock_service.get_whitelist.return_value = ["backtest", "trading", "data", "analysis"]

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "unknown_module", "DEBUG"])

        assert result.exit_code != 0

    def test_set_level_service_error(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = True
        mock_service.set_level.return_value = ServiceResult.error(error="Failed to set level")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["set-level", "backtest", "DEBUG"])

        assert result.exit_code != 0

    def test_get_level_invalid_module(self, cli_runner):
        mock_service = MagicMock()
        mock_service.is_module_allowed.return_value = False

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["get-level", "--module", "invalid"])

        assert result.exit_code != 0

    def test_reset_level_service_error(self, cli_runner):
        mock_service = MagicMock()
        mock_service.reset_levels.return_value = ServiceResult.error(error="Reset failed")

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.level_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["reset-level"])

        assert result.exit_code != 0

    def test_set_level_missing_arguments(self, cli_runner):
        result = cli_runner.invoke(logging_cli.app, ["set-level"])
        assert result.exit_code != 0


# ============================================================================
# 4. Exception handling (3)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestLoggingCLIExceptions:
    """Exception handling tests for logging commands."""

    def test_set_level_service_raises(self, cli_runner):
        mock_container = MagicMock()
        mock_container.level_service.side_effect = Exception("service unavailable")

        with patch("ginkgo.services.logging.containers.container", mock_container):
            result = cli_runner.invoke(logging_cli.app, ["set-level", "backtest", "DEBUG"])

        assert result.exit_code != 0

    def test_get_level_service_raises(self, cli_runner):
        mock_container = MagicMock()
        mock_container.level_service.side_effect = Exception("service unavailable")

        with patch("ginkgo.services.logging.containers.container", mock_container):
            result = cli_runner.invoke(logging_cli.app, ["get-level"])

        assert result.exit_code != 0

    def test_reset_level_service_raises(self, cli_runner):
        mock_container = MagicMock()
        mock_container.level_service.side_effect = Exception("connection lost")

        with patch("ginkgo.services.logging.containers.container", mock_container):
            result = cli_runner.invoke(logging_cli.app, ["reset-level"])

        assert result.exit_code != 0
