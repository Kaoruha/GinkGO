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


@pytest.mark.unit
@pytest.mark.cli
class TestViewErrors:
    """Tests for the 'errors' command."""

    def test_errors_default_labels_all_history(self, cli_runner):
        mock_service = MagicMock()
        mock_service.query_backtest_logs.return_value = [
            {"timestamp": "2026-05-06 12:00:00", "event_type": "BACKTEST", "message": "boom"}
        ]

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.log_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["errors"])

        assert result.exit_code == 0
        assert "all history" in result.output
        assert "boom" in result.output
        call_kwargs = mock_service.query_backtest_logs.call_args.kwargs
        assert "start_time" not in call_kwargs

    def test_errors_hours_filters_and_labels_time_window(self, cli_runner):
        mock_service = MagicMock()
        mock_service.query_backtest_logs.return_value = []

        with patch("ginkgo.services.logging.containers.container") as mock_container:
            mock_container.log_service.return_value = mock_service
            result = cli_runner.invoke(logging_cli.app, ["errors", "--hours", "24"])

        assert result.exit_code == 0
        assert "last 24h" in result.output
        call_kwargs = mock_service.query_backtest_logs.call_args.kwargs
        assert call_kwargs["start_time"] is not None
        assert call_kwargs["end_time"] is not None


@pytest.mark.unit
@pytest.mark.cli
class TestViewLogsRendering:
    """Tests for the 'logs' command row rendering (#5293).

    回归: ``view_logs`` 曾对每条日志 ``table.add_row(...)`` 连续调用两次,
    导致有日志时每行在表格里渲染两遍。本测试 mock ``Table.add_row`` 计数,
    断言 N 条日志恰好 N 次 add_row。
    """

    def _make_log(self, ts: str, msg: str) -> dict:
        return {"timestamp": ts, "level": "INFO", "event_type": "BACKTEST",
                "symbol": "", "message": msg}

    def test_logs_no_duplicate_rows(self, cli_runner):
        mock_service = MagicMock()
        mock_service.query_backtest_logs.return_value = [
            self._make_log("2026-05-06 12:00:00", "first"),
            self._make_log("2026-05-06 13:00:00", "second"),
        ]

        with patch("ginkgo.services.logging.containers.container") as mock_container, \
             patch("ginkgo.client.logging_cli.Table") as mock_table_cls:
            mock_container.log_service.return_value = mock_service
            table_instance = mock_table_cls.return_value
            result = cli_runner.invoke(logging_cli.app, ["logs", "--task", "abc"])

        assert result.exit_code == 0
        assert table_instance.add_row.call_count == 2, (
            f"每条日志应渲染 1 行, 2 条日志期望 add_row 调用 2 次, "
            f"实际 {table_instance.add_row.call_count} 次 —— #5293 add_row 重复回归"
        )

    def test_logs_empty_shows_no_logs_message(self, cli_runner):
        mock_service = MagicMock()
        mock_service.query_backtest_logs.return_value = []

        with patch("ginkgo.services.logging.containers.container") as mock_container, \
             patch("ginkgo.client.logging_cli.Table") as mock_table_cls:
            mock_container.log_service.return_value = mock_service
            table_instance = mock_table_cls.return_value
            result = cli_runner.invoke(logging_cli.app, ["logs", "--task", "abc"])

        assert result.exit_code == 0
        assert "no logs found" in result.output.lower()
        assert table_instance.add_row.call_count == 0


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
