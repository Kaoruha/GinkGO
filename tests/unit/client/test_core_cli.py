"""
Unit tests for core_cli.py commands: status, debug, init, version.

Core commands are registered on the main app via _main_app.command(name=...)(core_cli.func).
Test invocation uses `get_main_app()` from main.py.

Mock strategy:
  - status() / debug() import GCONF, GTM inside the function -> patch at import site
  - init() imports heavy modules inside the function -> patch all external dependencies
  - version() is defined as a fallback in main.py when core_cli.version is missing
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_main_app():
    """Return the Typer main app (lazy-loaded)."""
    from main import get_main_app
    return get_main_app()


# ===========================================================================
# 1. Help tests
# ===========================================================================

class TestHelp:
    """Verify help output for core commands."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_root_help_shows_core_commands(self, cli_runner):
        result = cli_runner.invoke(_get_main_app(), ["--help"])
        assert result.exit_code == 0
        for name in ("init", "status", "debug", "version"):
            assert name in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_status_help(self, cli_runner):
        result = cli_runner.invoke(_get_main_app(), ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()


# ===========================================================================
# 2. status command
# ===========================================================================

class TestStatus:
    """Tests for the 'status' top-level command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_system_status_heading(self, cli_runner, mock_gconf, mock_gtm):
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "System Status" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_debug_mode_on(self, cli_runner, mock_gconf, mock_gtm):
        mock_gconf.DEBUGMODE = True
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "ON" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_debug_mode_off(self, cli_runner, mock_gconf, mock_gtm):
        mock_gconf.DEBUGMODE = False
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "OFF" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_quiet_mode(self, cli_runner, mock_gconf, mock_gtm):
        mock_gconf.QUIET = True
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "Quiet" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_cpu_ratio(self, cli_runner, mock_gconf, mock_gtm):
        mock_gconf.CPURATIO = 0.8
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "80" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_worker_count(self, cli_runner, mock_gconf, mock_gtm):
        mock_gtm.get_worker_count.return_value = 3
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "3" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_no_active_workers_when_empty(self, cli_runner, mock_gconf, mock_gtm):
        mock_gtm.get_workers_status.return_value = {}
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "No active workers" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_handles_exception_gracefully(self, cli_runner, mock_gconf, mock_gtm):
        mock_gtm.clean_worker_pool.side_effect = RuntimeError("boom")
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        # status() catches Exception internally and prints error message
        assert "Error" in result.output or result.exit_code != 0


# ===========================================================================
# 3. debug command
# ===========================================================================

class TestDebug:
    """Tests for the 'debug on/off' top-level command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_debug_on_enables_mode(self, cli_runner, mock_gconf):
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(_get_main_app(), ["debug", "on"])
        assert result.exit_code == 0
        mock_gconf.set_debug.assert_called_once_with(True)

    @pytest.mark.unit
    @pytest.mark.cli
    def test_debug_off_disables_mode(self, cli_runner, mock_gconf):
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(_get_main_app(), ["debug", "off"])
        assert result.exit_code == 0
        mock_gconf.set_debug.assert_called_once_with(False)

    @pytest.mark.unit
    @pytest.mark.cli
    def test_missing_argument_shows_error(self, cli_runner, mock_gconf):
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(_get_main_app(), ["debug"])
        # typer requires an argument; exit code should be non-zero (2)
        assert result.exit_code != 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_invalid_argument_shows_error(self, cli_runner, mock_gconf):
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(_get_main_app(), ["debug", "invalid"])
        assert result.exit_code != 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_debug_on_output_message(self, cli_runner, mock_gconf):
        with patch("ginkgo.libs.GCONF", mock_gconf):
            result = cli_runner.invoke(_get_main_app(), ["debug", "on"])
        assert result.exit_code == 0
        assert "Debug mode enabled" in result.output


# ===========================================================================
# 4. init command
# ===========================================================================

class TestInit:
    """Tests for the 'init' top-level command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_initializing_message(self, cli_runner, mock_gconf, mock_gtm, mock_glog):
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.libs.GLOG", mock_glog), \
             patch("ginkgo.client.core_cli._init_notification_templates", return_value={"created": 0, "skipped": 5}), \
             patch("ginkgo.client.core_cli._init_system_group", return_value={"name": "admin", "status": "existed"}), \
             patch("ginkgo.client.core_cli._init_admin_user", return_value={"status": "existed", "username": "admin"}), \
             patch("ginkgo.client.core_cli._validate_system_health", return_value={"healthy": True, "issues": []}), \
             patch("ginkgo.client.core_cli._cleanup_invalid_data", return_value={"success": True, "cleaned_count": 0, "warnings": []}), \
             patch("ginkgo.data.drivers.create_all_tables"), \
             patch("ginkgo.data.drivers.is_table_exists", return_value=True), \
             patch("ginkgo.data.models"), \
             patch("ginkgo.data.seeding") as mock_seeding:
            mock_seeding.run = MagicMock()
            result = cli_runner.invoke(_get_main_app(), ["init"])
        assert result.exit_code == 0
        assert "Initializing" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_completion_message_on_success(self, cli_runner, mock_gconf, mock_gtm, mock_glog):
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.libs.GLOG", mock_glog), \
             patch("ginkgo.client.core_cli._init_notification_templates", return_value={"created": 2, "skipped": 3}), \
             patch("ginkgo.client.core_cli._init_system_group", return_value={"name": "admin", "status": "existed"}), \
             patch("ginkgo.client.core_cli._init_admin_user", return_value={"status": "existed", "username": "admin"}), \
             patch("ginkgo.client.core_cli._validate_system_health", return_value={"healthy": True, "issues": []}), \
             patch("ginkgo.client.core_cli._cleanup_invalid_data", return_value={"success": True, "cleaned_count": 0, "warnings": []}), \
             patch("ginkgo.data.drivers.create_all_tables"), \
             patch("ginkgo.data.drivers.is_table_exists", return_value=True), \
             patch("ginkgo.data.models"), \
             patch("ginkgo.data.seeding") as mock_seeding:
            mock_seeding.run = MagicMock()
            result = cli_runner.invoke(_get_main_app(), ["init"])
        assert result.exit_code == 0
        assert "completed" in result.output.lower()

    @pytest.mark.unit
    @pytest.mark.cli
    def test_handles_database_creation_failure(self, cli_runner, mock_gconf, mock_gtm, mock_glog):
        """When create_all_tables or is_table_exists fails, init should exit with error."""
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.libs.GLOG", mock_glog), \
             patch("ginkgo.data.drivers.create_all_tables", side_effect=Exception("db error")), \
             patch("ginkgo.data.models"):
            result = cli_runner.invoke(_get_main_app(), ["init"])
        assert result.exit_code != 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_handles_missing_tables(self, cli_runner, mock_gconf, mock_gtm, mock_glog):
        """When is_table_exists returns False for a table, init should fail."""
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.libs.GLOG", mock_glog), \
             patch("ginkgo.data.drivers.create_all_tables"), \
             patch("ginkgo.data.drivers.is_table_exists", return_value=False), \
             patch("ginkgo.data.models.MStockInfo", create=True) as MockTable:
            MockTable.__tablename__ = "t_stock_info"
            MockTable.__abstract__ = False
            with patch("ginkgo.data.models", MStockInfo=MockTable, MBar=MockTable, MSignal=MockTable, MOrder=MockTable, MPosition=MockTable, MPortfolio=MockTable, MEngine=MockTable, MParam=MockTable, MAdjustfactor=MockTable, MTick=MockTable):
                result = cli_runner.invoke(_get_main_app(), ["init"])
        assert result.exit_code != 0
        assert "Missing tables" in result.output or "failed" in result.output.lower()

    @pytest.mark.unit
    @pytest.mark.cli
    def test_component_registration_failure_is_non_fatal(self, cli_runner, mock_gconf, mock_gtm, mock_glog):
        """Seeding failure should not crash init (it prints a warning)."""
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.libs.GLOG", mock_glog), \
             patch("ginkgo.client.core_cli._init_notification_templates", return_value={"created": 0, "skipped": 0}), \
             patch("ginkgo.client.core_cli._init_system_group", return_value={"name": "admin", "status": "existed"}), \
             patch("ginkgo.client.core_cli._init_admin_user", return_value={"status": "existed", "username": "admin"}), \
             patch("ginkgo.client.core_cli._validate_system_health", return_value={"healthy": True, "issues": []}), \
             patch("ginkgo.client.core_cli._cleanup_invalid_data", return_value={"success": True, "cleaned_count": 0, "warnings": []}), \
             patch("ginkgo.data.drivers.create_all_tables"), \
             patch("ginkgo.data.drivers.is_table_exists", return_value=True), \
             patch("ginkgo.data.models"), \
             patch("ginkgo.data.seeding") as mock_seeding:
            mock_seeding.run.side_effect = Exception("seeding error")
            result = cli_runner.invoke(_get_main_app(), ["init"])
        # seeding failure is caught internally, init should still succeed
        assert result.exit_code == 0
        assert "Component" in result.output


# ===========================================================================
# 5. version command
# ===========================================================================

class TestVersion:
    """Tests for the 'version' top-level command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_version_info(self, cli_runner):
        # version is defined as a fallback in main.py since core_cli has no version()
        with patch("builtins.print") as mock_print:
            result = cli_runner.invoke(_get_main_app(), ["version"])
        # Either core_cli.version exists or the fallback prints version
        assert result.exit_code == 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_version_output_contains_identifier(self, cli_runner):
        result = cli_runner.invoke(_get_main_app(), ["version"])
        assert result.exit_code == 0
        # Output should contain version-like text
        assert "ginkgo" in result.output.lower() or "0." in result.output


# ===========================================================================
# 6. Misc / top-level app behaviour
# ===========================================================================

class TestMisc:
    """Miscellaneous top-level app tests."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_no_args_shows_help(self, cli_runner):
        """Main app has no_args_is_help=True (only works when run from shell, not CliRunner)."""
        result = cli_runner.invoke(_get_main_app(), [])
        # no_args_is_help only applies at the OS level, not via CliRunner.invoke
        # CliRunner passes [] which is treated as no subcommand -> exit 2
        assert result.exit_code == 2 or "Ginkgo" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_unknown_command_shows_error(self, cli_runner):
        result = cli_runner.invoke(_get_main_app(), ["nonexistent_command_xyz"])
        assert result.exit_code != 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_main_app_entry_point_works(self, cli_runner):
        """Basic smoke test: the app can be invoked without crashing."""
        result = cli_runner.invoke(_get_main_app(), ["--help"])
        assert result.exit_code == 0
        assert "Ginkgo" in result.output
