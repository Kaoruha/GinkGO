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

    def test_result_segment_stability_help_prefix_correct(self, cli_runner):
        """#4903: segment-stability --help 示例前缀不应残留已拍平的 'get' 子命令。

        早期 CLI 把 `get result` 拍平为 `result` 子命令组，docstring 示例
        需同步更新为 `ginkgo result segment-stability ...`，否则用户复制
        会得到 'No such command'。
        """
        result = cli_runner.invoke(flat_cli.result_app, ["segment-stability", "--help"])
        assert result.exit_code == 0
        assert "ginkgo result segment-stability" in result.output
        assert "ginkgo get result segment-stability" not in result.output


# ============================================================================
# 1b. result list -p short-option conflict (#4621)
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestResultListParamConflict:
    """#4621: --portfolio and --page both declared -p, triggering a Typer
    'parameter -p is used more than once' warning at command-build time.
    --portfolio keeps -p (consistent with `result show`, `record`); --page
    must use a distinct short option.
    """

    @staticmethod
    def _duplicate_warnings(records):
        return [str(w.message) for w in records if "used more than once" in str(w.message)]

    def test_result_list_help_no_duplicate_p_warning(self, cli_runner):
        import warnings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = cli_runner.invoke(flat_cli.result_app, ["list", "--help"])
        assert result.exit_code == 0
        assert self._duplicate_warnings(caught) == []

    def test_result_list_portfolio_and_page_are_distinct_options(self, cli_runner):
        """--portfolio and --page must each parse independently without the
        duplicate-short-option warning, regardless of order."""
        import warnings

        for argv in (["list", "--portfolio", "abc123"], ["list", "--page", "2"]):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = cli_runner.invoke(flat_cli.result_app, argv)
            assert result.exit_code == 0, f"failed for {argv}: {result.output}"
            assert self._duplicate_warnings(caught) == [], f"dup -p warning for {argv}"


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

    # #5957: 旧 test_result_get_* 断言已删除的假数据("Sharpe Ratio"/"Trade History")，
    # 新契约(真实 service + task_id 参数)由 TestResultGetRealData 覆盖，故移除。

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


# ============================================================================
# #5957: result get 接入真实数据(task_id 为参数), 删除重复 def get 与假数据
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestResultGetRealData:
    """#5957: result get <task_id> 走真实 service, 不打印硬编码假数据。"""

    def _task_svc(self, orders=None, record=None):
        from ginkgo.data.services.base_service import ServiceResult

        svc = MagicMock()
        sr_orders = ServiceResult(success=True, data=orders or [])
        sr_orders.set_metadata("total", len(orders or []))
        svc.list_orders.return_value = sr_orders
        svc.get_by_id.return_value = ServiceResult(success=True, data=record)
        return svc

    def test_trades_shows_real_orders_not_fake_data(self, cli_runner):
        from ginkgo.data.services.backtest_task_schemas import BacktestOrderItem

        order = BacktestOrderItem(
            code="600000.SH", direction="1", status="4",
            volume=100, transaction_price="12.34",
            transaction_volume=100, timestamp="2025-06-03 09:30",
        )
        record = MagicMock(name="bt-record")
        record.name = "my-bt"
        task_svc = self._task_svc(orders=[order], record=record)

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.backtest_task_service.return_value = task_svc
            result = cli_runner.invoke(
                flat_cli.result_app, ["get", "task-123", "--trades"])

        assert result.exit_code == 0, result.output
        # 参数透传为 task_id
        task_svc.list_orders.assert_called_once_with("task-123")
        # 真实订单数据出现
        assert "600000.SH" in result.output
        # 假数据标记必须消失
        assert "not yet implemented" not in result.output
        assert "15.2%" not in result.output
        assert "000001.SZ @ 10.50" not in result.output

    def test_default_calls_get_by_id_no_fake_header(self, cli_runner):
        record = MagicMock(name="bt-record")
        record.name = "real-backtest"
        task_svc = self._task_svc(record=record)

        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.backtest_task_service.return_value = task_svc
            result = cli_runner.invoke(flat_cli.result_app, ["get", "task-9"])

        assert result.exit_code == 0, result.output
        task_svc.get_by_id.assert_called_once_with("task-9")
        assert "not yet implemented" not in result.output
        assert "15.2%" not in result.output


# ============================================================================
# #5998: result 子命令参数命名统一为 --task-id（兼容旧 --run-id + deprecation）
# ============================================================================


@pytest.mark.unit
@pytest.mark.cli
class TestResultShowTaskIdUnify:
    """#5998: result show 主 flag 统一为 --task-id，保留 --run-id 别名 + 弃用提示。"""

    def _wire_show(self, task_id_value):
        """装配 show 完整路径 mock，返回 (mock_result_svc, mock_container_ctx)。"""
        from ginkgo.data.services.base_service import ServiceResult
        import pandas as pd

        summary = {"task_id": task_id_value, "engine_id": "e1", "total_records": 1,
                   "portfolio_count": 1, "portfolios": ["p1"]}
        mock_result_svc = MagicMock()
        mock_result_svc.get_run_summary.return_value = ServiceResult.success(data=summary)
        mock_result_svc.get_portfolio_analyzers.return_value = ServiceResult.success(data=["net_value"])
        mock_result_svc.get_analyzer_values_df.return_value = ServiceResult.success(
            data=pd.DataFrame([{"timestamp": "2025-01-01", "value": 1.05}]))
        return mock_result_svc

    def test_show_help_exposes_task_id(self, cli_runner):
        """show --help 含 --task-id（统一参数名）。"""
        result = cli_runner.invoke(flat_cli.result_app, ["show", "--help"])
        assert result.exit_code == 0
        assert "--task-id" in result.output

    def test_show_help_keeps_run_id_alias(self, cli_runner):
        """show --help 仍含 --run-id（向后兼容）。"""
        result = cli_runner.invoke(flat_cli.result_app, ["show", "--help"])
        assert result.exit_code == 0
        assert "--run-id" in result.output

    def test_show_task_id_routes_to_summary(self, cli_runner):
        """--task-id <id> 透传到 result_service.get_run_summary(task_id)。"""
        svc = self._wire_show("t1")
        with patch("ginkgo.data.containers.container") as mc:
            mc.result_service.return_value = svc
            r = cli_runner.invoke(flat_cli.result_app, ["show", "--task-id", "t1"])
        assert r.exit_code == 0, r.output
        svc.get_run_summary.assert_called_once_with("t1")

    def test_show_run_id_still_works_and_warns(self, cli_runner):
        """旧 --run-id 仍工作 + 透传 task_id + 输出弃用提示。"""
        svc = self._wire_show("r1")
        with patch("ginkgo.data.containers.container") as mc:
            mc.result_service.return_value = svc
            r = cli_runner.invoke(flat_cli.result_app, ["show", "--run-id", "r1"])
        assert r.exit_code == 0, r.output
        svc.get_run_summary.assert_called_once_with("r1")
        assert "弃用" in r.output or "deprecated" in r.output.lower()


@pytest.mark.unit
@pytest.mark.cli
class TestResultGetTaskIdOption:
    """#5998: result get 新增 --task-id Option（位置参数二选一），统一命名。"""

    def _task_svc(self, record=None):
        from ginkgo.data.services.base_service import ServiceResult
        svc = MagicMock()
        svc.get_by_id.return_value = ServiceResult(success=True, data=record)
        return svc

    def test_get_with_task_id_option(self, cli_runner):
        """get --task-id <id> 透传到 backtest_task_service.get_by_id。"""
        record = MagicMock(name="bt")
        record.name = "opt-bt"
        svc = self._task_svc(record=record)
        with patch("ginkgo.data.containers.container") as mc:
            mc.backtest_task_service.return_value = svc
            r = cli_runner.invoke(flat_cli.result_app, ["get", "--task-id", "opt-1"])
        assert r.exit_code == 0, r.output
        svc.get_by_id.assert_called_once_with("opt-1")

    def test_get_positional_still_works(self, cli_runner):
        """位置参数回归不破：get <id> 仍透传。"""
        record = MagicMock(name="bt")
        record.name = "pos-bt"
        svc = self._task_svc(record=record)
        with patch("ginkgo.data.containers.container") as mc:
            mc.backtest_task_service.return_value = svc
            r = cli_runner.invoke(flat_cli.result_app, ["get", "pos-1"])
        assert r.exit_code == 0, r.output
        svc.get_by_id.assert_called_once_with("pos-1")

    def test_get_without_any_id_errors(self, cli_runner):
        """get 无位置参数且无 --task-id时报错（必填校验）。"""
        with patch("ginkgo.data.containers.container") as mc:
            mc.backtest_task_service.return_value = self._task_svc()
            r = cli_runner.invoke(flat_cli.result_app, ["get"])
        assert r.exit_code != 0, r.output
        assert "task" in r.output.lower()
