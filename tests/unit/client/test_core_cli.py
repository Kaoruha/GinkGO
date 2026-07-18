"""
性能: 226MB RSS, 2.49s, 25 tests [PASS]
Unit tests for core_cli.py commands: status, debug, init, version.

Core commands are registered on the main app via _main_app.command(name=...)(core_cli.func).
Test invocation uses `get_main_app()` from main.py.

Mock strategy:
  - status() / debug() import GCONF, GTM inside the function -> patch at import site
  - init() imports heavy modules inside the function -> patch all external dependencies
  - version() is defined as a fallback in main.py when core_cli.version is missing
"""

import pytest
from pathlib import Path
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
# 2b. status command — ExecutionNode 口径 (#5282)
# ===========================================================================

class TestStatusExecNodes:
    """status 命令应反映 ExecutionNode 心跳数（#5282）。

    原先 Workers 字段只查 GTM data_worker 进程池（Redis SET ginkgo:dataworker_pool），
    完全忽略 ExecutionNode 心跳（Redis key heartbeat:node:*），导致实盘节点运行时
    Workers 误显 0。新增 Exec Nodes 行，复用 redis_service.get_execution_node_status()
    走 Service 层（与 scheduler_cli.nodes() 同源，不直连 Redis）。
    """

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_exec_nodes_count_when_heartbeat_present(self, cli_runner, mock_gconf, mock_gtm):
        """#5282 tracer: ExecutionNode 心跳非空 → status 输出 Exec Nodes 行且计数≠0。"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_services = MagicMock()
        mock_services.data.redis_service.return_value.get_execution_node_status.return_value = ServiceResult.success(
            data=[{"node_id": "node_a"}, {"node_id": "node_b"}, {"node_id": "node_c"}],
        )
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(_get_main_app(), ["status"])

        assert result.exit_code == 0
        assert "Exec Nodes" in result.output
        exec_line = next(l for l in result.output.splitlines() if "Exec Nodes" in l)
        assert "3" in exec_line

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_zero_exec_nodes_when_no_heartbeat(self, cli_runner, mock_gconf, mock_gtm):
        """#5282: 无 ExecutionNode 心跳 → Exec Nodes 显示 0（与 Workers 字段口径并列，不崩）。"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_services = MagicMock()
        mock_services.data.redis_service.return_value.get_execution_node_status.return_value = ServiceResult.success(
            data=[],
        )
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(_get_main_app(), ["status"])

        assert result.exit_code == 0
        exec_line = next(l for l in result.output.splitlines() if "Exec Nodes" in l)
        assert "0" in exec_line

    @pytest.mark.unit
    @pytest.mark.cli
    def test_shows_na_when_redis_service_raises(self, cli_runner, mock_gconf, mock_gtm):
        """#5282: redis_service 异常（Redis 不可用）→ Exec Nodes 显示 N/A，status 其余字段照常输出。"""
        mock_services = MagicMock()
        mock_services.data.redis_service.side_effect = RuntimeError("redis down")
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(_get_main_app(), ["status"])

        assert result.exit_code == 0
        # status 其余字段不受影响
        assert "System Status" in result.output
        exec_line = next(l for l in result.output.splitlines() if "Exec Nodes" in l)
        assert "N/A" in exec_line

    @pytest.mark.unit
    @pytest.mark.cli
    def test_worker_fields_distinct_labels(self, cli_runner, mock_gconf, mock_gtm):
        """#5282 AC: 字段文案明确区分两类——Data Workers（GTM 进程池）与 Exec Nodes（心跳）并列。"""
        from ginkgo.data.services.base_service import ServiceResult
        mock_services = MagicMock()
        mock_services.data.redis_service.return_value.get_execution_node_status.return_value = ServiceResult.success(
            data=[{"node_id": "n1"}],
        )
        mock_gtm.get_worker_count.return_value = 2
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm), \
             patch("ginkgo.services", mock_services):
            result = cli_runner.invoke(_get_main_app(), ["status"])

        assert result.exit_code == 0
        lines = result.output.splitlines()
        # Data Workers 行（GTM data_worker 进程池口径）
        dw_line = next(l for l in lines if "Data Workers" in l)
        assert "2" in dw_line
        # Exec Nodes 行（ExecutionNode 心跳口径，与 scheduler nodes 同源）
        en_line = next(l for l in lines if "Exec Nodes" in l)
        assert "1" in en_line


# ===========================================================================
# 2c. status command — main_control 字段退役 (#6727)
# ===========================================================================

class TestStatusMainControlRetired:
    """#6727: main_control 远控总线退役后,status 不再显示 Main Ctrl / Watch Dog。

    #6726 删除远控消费链后,无进程再 register_main_process,GTM.main_status /
    watch_dog_status 属性恒返回 "NOT EXIST",core_cli 这两行输出成误导性半死 UI。
    本测试守护 status 不得回退出这两行。
    """

    @pytest.mark.unit
    @pytest.mark.cli
    def test_status_omits_main_control_fields(self, cli_runner, mock_gconf, mock_gtm):
        """#6727 AC: status 输出不含 Main Ctrl / Watch Dog 两行。"""
        with patch("ginkgo.libs.GCONF", mock_gconf), \
             patch("ginkgo.libs.GTM", mock_gtm):
            result = cli_runner.invoke(_get_main_app(), ["status"])
        assert result.exit_code == 0
        assert "Main Ctrl" not in result.output
        assert "Watch Dog" not in result.output


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

    @pytest.mark.unit
    @pytest.mark.cli
    def test_no_hardcoded_stale_version_in_main(self):
        """main.py 不得含硬编码版本号字面量（#5406 AC#3，防 0.8.1 漂移回归）。

        兜底分支若回填具体版本号，CLI 与 API 版本会再次分裂。
        用文件路径定位 main.py，避免 editable install 下 import 解析错位。
        """
        main_py = Path(__file__).resolve().parents[3] / "main.py"
        src = main_py.read_text(encoding="utf-8")
        assert "0.8.1" not in src, "main.py 残留硬编码版本号，破坏 CLI/API 版本一致性"

    @pytest.mark.unit
    @pytest.mark.cli
    def test_version_output_not_stale(self, cli_runner):
        """正常路径输出来自动态 VERSION，不含硬编码 0.8.1（#5406 AC#3）。"""
        result = cli_runner.invoke(_get_main_app(), ["version"])
        assert result.exit_code == 0
        assert "0.8.1" not in result.output


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


# ===========================================================================
# 6. list_components engines (ADR-010: get_engines 死调用 → get_engines_df)
# ===========================================================================

class TestListComponentsEngines:
    """list_components(ENGINES) 从死调用 get_engines() 迁到 get_engines_df()。"""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_success_unpacks_dataframe(self):
        """get_engines_df 成功：解包 ServiceResult.data 拿到 DataFrame。"""
        import pandas as pd
        from ginkgo.client.core_cli import list_components, ComponentType
        from ginkgo.data.services.base_service import ServiceResult

        expected_df = pd.DataFrame([{"uuid": "e1", "name": "EngineA"}])
        mock_engine_service = MagicMock()
        mock_engine_service.get_engines_df.return_value = ServiceResult.success(data=expected_df)

        with patch("ginkgo.data.containers.container") as mock_container, \
             patch("ginkgo.libs.utils.display.display_dataframe") as mock_display:
            mock_container.engine_service.return_value = mock_engine_service
            list_components(ComponentType.ENGINES)

        mock_engine_service.get_engines_df.assert_called_once()
        # display_dataframe 收到的 df 应是解包后的 DataFrame（前 page 行）
        called_df = mock_display.call_args.kwargs.get("data")
        assert called_df is not None
        assert called_df.iloc[0]["uuid"] == "e1"
        assert called_df.iloc[0]["name"] == "EngineA"

    @pytest.mark.unit
    @pytest.mark.cli
    def test_failure_falls_back_to_empty_dataframe(self):
        """get_engines_df 失败/None：兜底空 DataFrame，打印 No engines found 且不抛。"""
        from ginkgo.client.core_cli import list_components, ComponentType
        from ginkgo.data.services.base_service import ServiceResult

        mock_engine_service = MagicMock()
        mock_engine_service.get_engines_df.return_value = ServiceResult.error("boom")

        with patch("ginkgo.data.containers.container") as mock_container, \
             patch("ginkgo.libs.utils.display.display_dataframe") as mock_display:
            mock_container.engine_service.return_value = mock_engine_service
            # 不应抛异常
            list_components(ComponentType.ENGINES)

        mock_engine_service.get_engines_df.assert_called_once()
        # 空 DataFrame 走 "No engines found" 早返回，display_dataframe 不应被调用
        mock_display.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.cli
    def test_none_data_falls_back_to_empty_dataframe(self):
        """success=True 但 data=None：同样兜底空 DataFrame。"""
        from ginkgo.client.core_cli import list_components, ComponentType
        from ginkgo.data.services.base_service import ServiceResult

        mock_engine_service = MagicMock()
        mock_engine_service.get_engines_df.return_value = ServiceResult.success(data=None)

        with patch("ginkgo.data.containers.container") as mock_container, \
             patch("ginkgo.libs.utils.display.display_dataframe") as mock_display:
            mock_container.engine_service.return_value = mock_engine_service
            list_components(ComponentType.ENGINES)

        mock_display.assert_not_called()



class TestInitAdminUserTransactions:
    @pytest.mark.unit
    def test_init_admin_user_does_not_commit_inside_managed_session(self):
        from ginkgo.client.core_cli import _init_admin_user

        session = MagicMock()
        select_result = MagicMock()
        select_result.fetchone.return_value = None
        session.execute.side_effect = [select_result, MagicMock(), MagicMock()]

        from contextlib import contextmanager

        @contextmanager
        def fake_session_manager():
            yield session

        user_crud = MagicMock()
        user_crud.get_session.side_effect = fake_session_manager
        mock_container = MagicMock()
        mock_container.user_crud.return_value = user_crud
        mock_container.user_credential_crud.return_value = MagicMock()

        with patch("ginkgo.data.containers.container", mock_container), \
             patch("bcrypt.gensalt", return_value=b"salt"), \
             patch("bcrypt.hashpw", return_value=b"hashed"):
            result = _init_admin_user()

        assert result["status"] == "created"
        assert session.execute.call_count == 3
        session.commit.assert_not_called()
