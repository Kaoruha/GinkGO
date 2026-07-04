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
from ginkgo.data.services.base_service import ServiceResult


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
        """#5357: 名称/UUID 均未命中时给清晰中文提示，不再误报 'File not found'。"""
        mock_container = _mock_file_container_for_name("nonexistent_file.py", [])
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.trading.evaluation.utils.database_loader.DatabaseStrategyLoader") as MockLoader:
            MockLoader.return_value.load_by_file_id.side_effect = FileNotFoundError("not in db")
            result = cli_runner.invoke(validation_cli.app, [
                "nonexistent_file.py"
            ])
        assert result.exit_code == 2
        assert "未找到组件" in result.output
        assert "File not found" not in result.output

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


# ============================================================================
# 6. Component name / UUID resolution (#5357)
# ============================================================================


def _mock_file_container_for_name(name, files):
    """Build a mock container whose file_service().get_by_name(name) returns
    a real ServiceResult wrapping the given ORM-like file objects."""
    mock_container = MagicMock()
    mock_file_service = MagicMock()
    mock_file_service.get_by_name.return_value = ServiceResult.success(
        data={"files": files, "count": len(files)},
        message=f"Found {len(files)} files with name '{name}'",
    )
    mock_container.file_service.return_value = mock_file_service
    return mock_container


@pytest.mark.unit
@pytest.mark.cli
class TestComponentNameUuidResolution:
    """#5357: validate <name> / <uuid> should resolve from DB, not just file paths."""

    def test_validate_by_component_name_resolves_from_db(self, cli_runner):
        """validate momentum (momentum in DB) → resolves to file_id, loads, validates.
        Must NOT print 'File not found'."""
        mock_file = MagicMock()
        mock_file.uuid = "abc123def4567890abcdef1234567890"
        mock_container = _mock_file_container_for_name("momentum", [mock_file])

        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.trading.evaluation.utils.database_loader.DatabaseStrategyLoader") as MockLoader, \
             patch.object(validation_cli, "_validate_single_strategy") as mock_validate:
            mock_loader = MockLoader.return_value
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value = Path("/tmp/resolved_momentum.py")
            mock_cm.__exit__.return_value = False
            mock_loader.load_by_file_id.return_value = mock_cm

            result = cli_runner.invoke(validation_cli.app, ["momentum", "--type", "strategy"])

        assert result.exit_code == 0, result.output
        assert "File not found" not in result.output, f"误报 File not found:\n{result.output}"
        # 名称命中 → 用 get_by_name 返回的 uuid 加载
        mock_loader.load_by_file_id.assert_called_once_with("abc123def4567890abcdef1234567890")
        mock_validate.assert_called_once()

    def test_validate_by_uuid_falls_back_when_name_misses(self, cli_runner):
        """validate <uuid> (uuid 不在 name 表但有效) → name 未命中后按 uuid 加载。"""
        # 名称查不到（count=0）
        mock_container = _mock_file_container_for_name("deadbeefdeadbeefdeadbeefdeadbeef", [])
        with patch("ginkgo.data.containers.container", mock_container), \
             patch("ginkgo.trading.evaluation.utils.database_loader.DatabaseStrategyLoader") as MockLoader, \
             patch.object(validation_cli, "_validate_single_strategy") as mock_validate:
            mock_loader = MockLoader.return_value
            mock_cm = MagicMock()
            mock_cm.__enter__.return_value = Path("/tmp/resolved_uuid.py")
            mock_cm.__exit__.return_value = False
            mock_loader.load_by_file_id.return_value = mock_cm

            result = cli_runner.invoke(
                validation_cli.app, ["deadbeefdeadbeefdeadbeefdeadbeef", "--type", "strategy"]
            )

        assert result.exit_code == 0, result.output
        # name 未命中 → 用原始 uuid 输入加载
        mock_loader.load_by_file_id.assert_called_once_with("deadbeefdeadbeefdeadbeefdeadbeef")
        mock_validate.assert_called_once()


# ============================================================================
# 7. Runtime crash detection (#5317)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestRuntimeCrashDetection:
    """#5317: validate --show-trace must distinguish a strategy that crashes in
    cal() (FAILED) from one that legitimately returns [] (PASSED).

    Before: cal() exceptions were swallowed into signals=[] and only printed
    under --verbose, so a crashing strategy reported 'Validation PASSED'.
    """

    def test_signal_trace_report_has_cal_exceptions_field(self):
        """SignalTraceReport exposes a cal_exceptions list (default empty)."""
        from ginkgo.trading.evaluation.core.evaluation_result import SignalTraceReport

        report = SignalTraceReport(strategy_name="s", strategy_file="s.py")
        assert report.cal_exceptions == []

    def test_signal_trace_report_add_cal_exception(self):
        """add_cal_exception appends a structured record (type/message/traceback)."""
        from ginkgo.trading.evaluation.core.evaluation_result import SignalTraceReport

        report = SignalTraceReport(strategy_name="s", strategy_file="s.py")
        report.add_cal_exception(
            exception_type="AttributeError",
            message="'SimpleDataFeeder' has no get_historical_data",
            traceback_str="Traceback ...",
        )
        assert len(report.cal_exceptions) == 1
        rec = report.cal_exceptions[0]
        assert rec["exception_type"] == "AttributeError"
        assert "get_historical_data" in rec["message"]
        assert rec["traceback_str"] == "Traceback ..."

    def test_run_signal_tracing_captures_cal_exceptions(self, tmp_path):
        """A strategy whose cal() raises → _run_signal_tracing records each
        crash in report.cal_exceptions (previously swallowed silently)."""
        from datetime import datetime
        from decimal import Decimal

        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES

        crash_file = tmp_path / "crash.py"
        crash_file.write_text(
            "from ginkgo.trading.strategies.strategy_base import BaseStrategy\n"
            "class CrashStrategy(BaseStrategy):\n"
            "    def cal(self, portfolio_info, event):\n"
            "        raise AttributeError(\"'SimpleDataFeeder' object has no attribute 'get_historical_data'\")\n"
        )

        bar = MBar(
            code="000001.SZ",
            timestamp=datetime(2023, 1, 3, 9, 30),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.2"),
            volume=1000000,
            amount=Decimal("10200000.0"),
            frequency=FREQUENCY_TYPES.DAY,
        )

        mock_container = MagicMock()
        mock_bar_service = MagicMock()
        mock_bar_service.get.return_value = ServiceResult.success(
            data=[bar], message="ok"
        )
        mock_container.bar_service.return_value = mock_bar_service

        with patch("ginkgo.data.containers.container", mock_container):
            report = validation_cli._run_signal_tracing(
                crash_file, "000001.SZ", 0, verbose=False
            )

        assert report is not None
        assert len(report.cal_exceptions) >= 1
        rec = report.cal_exceptions[0]
        assert rec["exception_type"] == "AttributeError"
        assert "get_historical_data" in rec["message"]
        assert "Traceback" in rec["traceback_str"]

    def test_validate_crashing_strategy_reports_failed(self, cli_runner, tmp_path):
        """#5317 验收: ginkgo validate --show-trace on a crashing strategy must
        exit non-zero and print FAILED + exception info (previously: PASSED)."""
        from datetime import datetime
        from decimal import Decimal

        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES

        crash_file = tmp_path / "crash.py"
        crash_file.write_text(
            "from ginkgo.trading.strategies.strategy_base import BaseStrategy\n"
            "class CrashStrategy(BaseStrategy):\n"
            "    def cal(self, portfolio_info, event):\n"
            "        if event:\n"
            "            raise AttributeError(\"no get_historical_data\")\n"
            "        return []\n"
        )

        bar = MBar(
            code="000001.SZ",
            timestamp=datetime(2023, 1, 3, 9, 30),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.2"),
            volume=1000000,
            amount=Decimal("10200000.0"),
            frequency=FREQUENCY_TYPES.DAY,
        )

        mock_container = MagicMock()
        mock_bar_service = MagicMock()
        mock_bar_service.get.return_value = ServiceResult.success(
            data=[bar], message="ok"
        )
        mock_container.bar_service.return_value = mock_bar_service

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(
                validation_cli.app,
                [str(crash_file), "--show-trace"],
            )

        assert result.exit_code == 1, f"expected FAILED (exit 1), got {result.exit_code}\n{result.output}"
        assert "FAILED" in result.output
        assert "AttributeError" in result.output
        assert "PASSED" not in result.output

    def test_validate_legitimate_empty_strategy_still_passes(self, cli_runner, tmp_path):
        """#5317 回归保护: 策略主动 return [] (无崩溃) → 仍 PASSED。
        修复不能误伤合法的零信号策略。"""
        from datetime import datetime
        from decimal import Decimal

        from ginkgo.data.models import MBar
        from ginkgo.enums import FREQUENCY_TYPES

        quiet_file = tmp_path / "quiet.py"
        quiet_file.write_text(
            "from ginkgo.trading.strategies.strategy_base import BaseStrategy\n"
            "class QuietStrategy(BaseStrategy):\n"
            "    def cal(self, portfolio_info, event):\n"
            "        return []\n"
        )

        bar = MBar(
            code="000001.SZ",
            timestamp=datetime(2023, 1, 3, 9, 30),
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.2"),
            volume=1000000,
            amount=Decimal("10200000.0"),
            frequency=FREQUENCY_TYPES.DAY,
        )

        mock_container = MagicMock()
        mock_bar_service = MagicMock()
        mock_bar_service.get.return_value = ServiceResult.success(
            data=[bar], message="ok"
        )
        mock_container.bar_service.return_value = mock_bar_service

        with patch("ginkgo.data.containers.container", mock_container):
            result = cli_runner.invoke(
                validation_cli.app,
                [str(quiet_file), "--show-trace"],
            )

        assert result.exit_code == 0, f"expected PASSED (exit 0), got {result.exit_code}\n{result.output}"
        assert "PASSED" in result.output
        assert "FAILED" not in result.output
        assert "RUNTIME_CAL_CRASH" not in result.output
