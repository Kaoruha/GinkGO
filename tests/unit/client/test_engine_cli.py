"""
性能: 223MB RSS, 2.09s, 40 tests [PASS]
Unit tests for engine_cli.py commands.

Engine CLI registers its own ``app = typer.Typer()`` with subcommands:
  list, create, cat, status, run, delete, bind-portfolio, unbind-portfolio

Mock strategy:
  - Commands import ``container`` from ``ginkgo.data.containers`` inside
    function bodies -> patch ``"ginkgo.data.containers.container"``.
  - Helper functions from ``engine_cli_helpers`` (resolve_engine_id, etc.)
    are imported at module level -> patch at the engine_cli import site.
"""

import json

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

import pandas as pd
from typer.testing import CliRunner

from ginkgo.client import engine_cli
from ginkgo.data.services.base_service import ServiceResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine_df(rows=None):
    """Build a DataFrame mimicking engine_service.get().data.to_dataframe()."""
    if rows is None:
        rows = [
            {
                "uuid": "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa",
                "name": "TestEngine",
                "is_live": False,
                "status": "ENGINESTATUS_TYPES.IDLE",
                "update_at": "2025-01-01 00:00:00",
            }
        ]
    return pd.DataFrame(rows)


def _make_engine_model(**overrides):
    """Build a mock engine model object."""
    m = MagicMock()
    m.uuid = "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"
    m.name = "TestEngine"
    m.is_live = False
    m.status = "ENGINESTATUS_TYPES.IDLE"
    m.run_count = 0
    m.config_hash = "abc123"
    m.desc = "test description"
    m.description = "test description"
    m.backtest_start_date = None
    m.backtest_end_date = None
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _mock_engine_service(**method_returns):
    """Create a mock engine_service with pre-configured return values."""
    svc = MagicMock()
    for method, ret in method_returns.items():
        getattr(svc, method).return_value = ret
    return svc


def _mock_container(engine_service=None, portfolio_service=None, mapping_service=None, cruds=None):
    """Create a mock container with service factories."""
    c = MagicMock()
    c.engine_service.return_value = engine_service or _mock_engine_service()
    c.portfolio_service.return_value = portfolio_service or MagicMock()
    c.mapping_service.return_value = mapping_service or MagicMock()
    if cruds:
        c.cruds = cruds
    return c


# ===========================================================================
# 1. Help tests
# ===========================================================================


class TestHelp:
    """Verify help output for engine commands."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_root_help(self, cli_runner):
        result = cli_runner.invoke(engine_cli.app, ["--help"])
        assert result.exit_code == 0
        for name in ("list", "create", "cat", "status", "run", "delete"):
            assert name in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_help(self, cli_runner):
        result = cli_runner.invoke(engine_cli.app, ["list", "--help"])
        assert result.exit_code == 0
        for opt in ("--status", "--portfolio", "--filter", "--limit", "--raw"):
            assert opt in result.output


# ===========================================================================
# 2. list command
# ===========================================================================


class TestListEngines:
    """Tests for the 'list' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_all_engines(self, cli_runner):
        df = _make_engine_df()
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=df))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list"])
        assert result.exit_code == 0
        assert "TestEngine" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_limit_pushes_page_size_to_get_engines_df(self, cli_runner):
        """ADR-021 L139：--limit 下推 get_engines_df page_size（all 路径）。"""
        df = _make_engine_df()
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=df))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--limit", "5"])

        assert result.exit_code == 0
        svc.get_engines_df.assert_called_once_with(page_size=5)

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_filter_pushes_page_size_to_fuzzy_search(self, cli_runner):
        """ADR-021 L139：filter 模式 --limit 下推 fuzzy_search page_size。"""
        df = _make_engine_df()
        model_list = MagicMock()
        model_list.to_dataframe.return_value = df
        svc = _mock_engine_service(fuzzy_search=ServiceResult.success(data=model_list))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--filter", "test", "--limit", "5"])

        assert result.exit_code == 0
        _, kwargs = svc.fuzzy_search.call_args
        assert kwargs.get("page_size") == 5

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_with_filter(self, cli_runner):
        df = _make_engine_df()
        model_list = MagicMock()
        model_list.to_dataframe.return_value = df
        svc = _mock_engine_service(
            fuzzy_search=ServiceResult.success(data=model_list),
        )

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--filter", "test"])
        assert result.exit_code == 0
        assert "test" in result.output
        svc.fuzzy_search.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_with_status_filter(self, cli_runner):
        df = _make_engine_df()
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=df))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--status", "idle"])
        assert result.exit_code == 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_with_portfolio_filter(self, cli_runner):
        df = _make_engine_df()
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=df))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--portfolio", "portfolio-123"])
        assert result.exit_code == 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_raw_mode(self, cli_runner):
        df = _make_engine_df()
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=df))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--raw"])
        assert result.exit_code == 0
        assert "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa" in result.output
        assert "TestEngine" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_json_format_outputs_adr021_contract(self, cli_runner):
        df = _make_engine_df()
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=df))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--format", "json", "--limit", "1"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == 1
        assert payload["metadata"] == {"total": 1, "limit": 1, "offset": 0}
        assert payload["data"][0]["name"] == "TestEngine"

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_no_engines_found(self, cli_runner):
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=pd.DataFrame()))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list"])
        assert result.exit_code == 0
        assert "No engines found" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_service_failure(self, cli_runner):
        svc = _mock_engine_service(get_engines_df=ServiceResult.error(error="DB connection lost"))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list"])
        assert result.exit_code == 1  # ADR-021 第 6 维：service 失败 → exit 1（原 exit 0 是 false-success）
        assert "Failed" in result.output or "DB connection lost" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_exception_handling(self, cli_runner):
        """When container.engine_service() raises, the catch-all prints an error."""
        svc = MagicMock()
        svc.get_engines_df.side_effect = RuntimeError("container boom")

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list"])
        assert result.exit_code == 1  # ADR-021 第 6 维：异常 → exit 1（原 exit 0 是 false-success）
        assert "Error" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_service_failure_json_envelope(self, cli_runner):
        """ADR-021 第 1/5/6 维：--format json + service 失败 → stdout 合法 JSON 错误 envelope + exit 1。"""
        svc = _mock_engine_service(get_engines_df=ServiceResult.error(error="DB connection lost"))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--format", "json"])
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert "DB connection lost" in payload["error"]["message"]

    @pytest.mark.unit
    @pytest.mark.cli
    def test_list_exception_json_envelope(self, cli_runner):
        """ADR-021 第 1/5/6 维：--format json + 异常 → stdout 合法 JSON 错误 envelope + exit 1。"""
        svc = MagicMock()
        svc.get_engines_df.side_effect = RuntimeError("container boom")

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["list", "--format", "json"])
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert "container boom" in payload["error"]["message"]


# ===========================================================================
# 3. create command
# ===========================================================================


class TestCreate:
    """Tests for the 'create' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_create_engine_success(self, cli_runner):
        engine_model = _make_engine_model()
        svc = _mock_engine_service(add=ServiceResult.success(data=engine_model))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["create", "--name", "MyEngine"])
        assert result.exit_code == 0
        assert "MyEngine" in result.output
        assert "created successfully" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_create_with_type_option(self, cli_runner):
        engine_model = _make_engine_model()
        svc = _mock_engine_service(add=ServiceResult.success(data=engine_model))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["create", "--name", "LiveEngine", "--type", "live"])
        assert result.exit_code == 0
        assert "live" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_create_missing_name(self, cli_runner):
        result = cli_runner.invoke(engine_cli.app, ["create"])
        assert result.exit_code != 0

    @pytest.mark.unit
    @pytest.mark.cli
    def test_create_service_failure(self, cli_runner):
        svc = _mock_engine_service(add=ServiceResult.error(error="Duplicate name"))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["create", "--name", "Dup"])
        assert result.exit_code == 1
        assert "Failed" in result.output or "Duplicate" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_create_exception_handling(self, cli_runner):
        """When engine_service.add() raises, the catch-all prints an error."""
        svc = MagicMock()
        svc.add.side_effect = RuntimeError("create boom")

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["create", "--name", "X"])
        assert result.exit_code == 1
        assert "Error" in result.output


# ===========================================================================
# 4. cat command
# ===========================================================================


class TestCat:
    """Tests for the 'cat' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_cat_engine_by_uuid(self, cli_runner):
        engine = _make_engine_model(config_snapshot=None)
        model_list = MagicMock()
        model_list.__len__ = MagicMock(return_value=1)
        model_list.__getitem__ = MagicMock(return_value=engine)
        svc = _mock_engine_service(get=ServiceResult.success(data=model_list))

        with (
            patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
            patch("ginkgo.client.engine_cli.collect_component_info", return_value={"has_portfolio": False}),
            patch("ginkgo.client.engine_cli.display_component_tree"),
        ):
            result = cli_runner.invoke(engine_cli.app, ["cat", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 0
        assert "TestEngine" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_cat_engine_not_found(self, cli_runner):
        with patch("ginkgo.client.engine_cli.resolve_engine_id", return_value=None):
            result = cli_runner.invoke(engine_cli.app, ["cat", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_cat_no_id_shows_list(self, cli_runner):
        svc = _mock_engine_service(get_engines_df=ServiceResult.success(data=_make_engine_df()))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["cat"])
        assert result.exit_code == 0
        assert "No engine ID" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_cat_service_failure(self, cli_runner):
        svc = _mock_engine_service(get=ServiceResult.error(error="fetch failed"))

        with (
            patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(engine_cli.app, ["cat", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 1
        assert "Failed" in result.output or "fetch failed" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_cat_component_tree_display(self, cli_runner):
        engine = _make_engine_model(config_snapshot=None)
        model_list = MagicMock()
        model_list.__len__ = MagicMock(return_value=1)
        model_list.__getitem__ = MagicMock(return_value=engine)
        svc = _mock_engine_service(get=ServiceResult.success(data=model_list))

        component_data = {
            "has_portfolio": True,
            "portfolio_id": "port-uuid",
            "portfolio_info": None,
            "strategies": [],
            "risk_managers": [],
            "analyzers": [],
            "selectors": [],
            "sizers": [],
        }

        with (
            patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
            patch("ginkgo.client.engine_cli.collect_component_info", return_value=component_data),
            patch("ginkgo.client.engine_cli.display_component_tree") as mock_tree,
        ):
            result = cli_runner.invoke(engine_cli.app, ["cat", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 0
        mock_tree.assert_called_once()


# ===========================================================================
# 5. status command
# ===========================================================================


class TestStatus:
    """Tests for the 'status' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_show_engine_status(self, cli_runner):
        engine = _make_engine_model()
        model_list = MagicMock()
        model_list.__len__ = MagicMock(return_value=1)
        model_list.__getitem__ = MagicMock(return_value=engine)
        svc = _mock_engine_service(get=ServiceResult.success(data=model_list))

        with (
            patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(engine_cli.app, ["status", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 0
        assert "Engine Status" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_status_engine_not_found(self, cli_runner):
        with patch("ginkgo.client.engine_cli.resolve_engine_id", return_value=None):
            result = cli_runner.invoke(engine_cli.app, ["status", "ghost-engine"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_status_resolve_by_name(self, cli_runner):
        engine = _make_engine_model()
        model_list = MagicMock()
        model_list.__len__ = MagicMock(return_value=1)
        model_list.__getitem__ = MagicMock(return_value=engine)
        svc = _mock_engine_service(get=ServiceResult.success(data=model_list))

        with (
            patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)),
            patch(
                "ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"
            ) as mock_resolve,
        ):
            result = cli_runner.invoke(engine_cli.app, ["status", "TestEngine"])
        assert result.exit_code == 0
        mock_resolve.assert_called_with("TestEngine")

    @pytest.mark.unit
    @pytest.mark.cli
    def test_status_service_failure(self, cli_runner):
        svc = _mock_engine_service(get=ServiceResult.error(error="db error"))

        with (
            patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(engine_cli.app, ["status", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 1
        assert "Failed" in result.output or "db error" in result.output


# ===========================================================================
# 6. run command
# ===========================================================================


class TestRun:
    """Tests for the 'run' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_run_no_id_shows_list(self, cli_runner):
        model_list = MagicMock()
        model_list.to_dataframe.return_value = _make_engine_df()
        svc = _mock_engine_service(get=ServiceResult.success(data=model_list))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["run"])
        assert result.exit_code == 0
        assert "No engine ID" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_run_engine_not_found(self, cli_runner):
        with patch("ginkgo.client.engine_cli.resolve_engine_id", return_value=None):
            result = cli_runner.invoke(engine_cli.app, ["run", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_run_dry_run_success(self, cli_runner):
        mock_engine = MagicMock()
        mock_engine.engine_id = "test-id"
        assembly_svc = MagicMock()
        assembly_svc.assemble_backtest_engine.return_value = ServiceResult.success(data=mock_engine)
        trading_container = MagicMock()
        trading_container.services.engine_assembly_service.return_value = assembly_svc

        with (
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
            patch("ginkgo.trading.core.containers.container", trading_container),
        ):
            result = cli_runner.invoke(engine_cli.app, ["run", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output or "Validation" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_run_dry_run_failure(self, cli_runner):
        assembly_svc = MagicMock()
        assembly_svc.assemble_backtest_engine.return_value = ServiceResult.error(
            error="assembly failed", message="assembly failed"
        )
        trading_container = MagicMock()
        trading_container.services.engine_assembly_service.return_value = assembly_svc

        with (
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
            patch("ginkgo.trading.core.containers.container", trading_container),
        ):
            result = cli_runner.invoke(engine_cli.app, ["run", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "--dry-run"])
        assert result.exit_code == 0
        assert "Validation error" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_run_assembly_failure(self, cli_runner):
        assembly_svc = MagicMock()
        assembly_svc.assemble_backtest_engine.return_value = ServiceResult.error(
            error="missing component", message="missing component"
        )
        trading_container = MagicMock()
        trading_container.services.engine_assembly_service.return_value = assembly_svc

        mock_gconf = MagicMock()
        mock_gconf.DEBUGMODE = False

        with (
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
            patch("ginkgo.trading.core.containers.container", trading_container),
            patch("ginkgo.libs.GCONF", mock_gconf),
        ):
            result = cli_runner.invoke(engine_cli.app, ["run", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 0
        assert "assembly failed" in result.output or "Error" in result.output


# ===========================================================================
# 7. delete command
# ===========================================================================


class TestDelete:
    """Tests for the 'delete' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_delete_with_confirm(self, cli_runner):
        svc = _mock_engine_service(delete=ServiceResult.success(data=None))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["delete", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "--confirm"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_delete_with_yes_short_flag(self, cli_runner):
        """-y 短标志成功删除（#6006: 统一确认标志跨命令一致）"""
        svc = _mock_engine_service(delete=ServiceResult.success(data=None))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["delete", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "-y"])
        assert result.exit_code == 0
        assert "deleted successfully" in result.output
        svc.delete.assert_called_once_with("aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa")

    @pytest.mark.unit
    @pytest.mark.cli
    def test_delete_missing_confirm(self, cli_runner):
        result = cli_runner.invoke(engine_cli.app, ["delete", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 1
        assert "--confirm" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_delete_service_failure(self, cli_runner):
        svc = _mock_engine_service(delete=ServiceResult.error(error="not found"))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["delete", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "--confirm"])
        assert result.exit_code == 1
        assert "Failed" in result.output or "not found" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_delete_exception_handling(self, cli_runner):
        """When engine_service.delete() raises, the catch-all prints an error."""
        svc = MagicMock()
        svc.delete.side_effect = RuntimeError("delete boom")

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["delete", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "--confirm"])
        assert result.exit_code == 1
        assert "Error" in result.output


# ===========================================================================
# 8. bind-portfolio / unbind-portfolio commands
# ===========================================================================


class TestBindPortfolio:
    """Tests for the 'bind-portfolio' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_bind_success(self, cli_runner):
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "port-uuid"
        mock_portfolio.name = "TestPortfolio"

        port_model_list = MagicMock()
        port_model_list.__len__ = MagicMock(return_value=1)
        port_model_list.__getitem__ = MagicMock(return_value=mock_portfolio)

        eng_model_list = MagicMock()
        eng_model_list.__len__ = MagicMock(return_value=1)
        eng_model_list.__getitem__ = MagicMock(return_value=_make_engine_model())

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=port_model_list)

        engine_svc = MagicMock()
        engine_svc.get.return_value = ServiceResult.success(data=eng_model_list)

        mapping_svc = MagicMock()
        mapping_svc.get_engine_portfolio_mapping.return_value = ServiceResult.success(data=[])
        mapping_svc.create_engine_portfolio_mapping.return_value = ServiceResult.success(data=None, message="OK")

        container = _mock_container(
            engine_service=engine_svc,
            portfolio_service=portfolio_svc,
            mapping_service=mapping_svc,
        )

        with (
            patch("ginkgo.data.containers.container", container),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(
                engine_cli.app, ["bind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "port-uuid"]
            )
        assert result.exit_code == 0
        assert "binding created" in result.output.lower() or "TestEngine" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_bind_missing_engine_id(self, cli_runner):
        model_list = MagicMock()
        model_list.to_dataframe.return_value = _make_engine_df()
        svc = _mock_engine_service(get=ServiceResult.success(data=model_list))

        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["bind-portfolio"])
        assert result.exit_code == 0
        assert "No engine ID" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_bind_missing_portfolio_id(self, cli_runner):
        portfolio_svc = MagicMock()
        portfolio_svc.get_portfolios_df.return_value = ServiceResult.success(
            data=pd.DataFrame(
                [{"uuid": "p1", "name": "Port", "initial_capital": 100000, "is_live": False, "is_del": False}]
            )
        )

        container = _mock_container(portfolio_service=portfolio_svc)

        with patch("ginkgo.data.containers.container", container):
            result = cli_runner.invoke(engine_cli.app, ["bind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"])
        assert result.exit_code == 0
        assert "No portfolio ID" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_bind_engine_not_found(self, cli_runner):
        with (
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value=None),
            patch("ginkgo.data.containers.container", _mock_container()),
        ):
            result = cli_runner.invoke(engine_cli.app, ["bind-portfolio", "nonexistent", "port-uuid"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_bind_mode_mismatch_shows_error(self, cli_runner):
        """#5112: service 返回模式不兼容错误时，CLI 显示错误（非 ✅）且退出码非 0"""
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "port-uuid"
        mock_portfolio.name = "TestPortfolio"

        port_model_list = MagicMock()
        port_model_list.__len__ = MagicMock(return_value=1)
        port_model_list.__getitem__ = MagicMock(return_value=mock_portfolio)

        eng_model_list = MagicMock()
        eng_model_list.__len__ = MagicMock(return_value=1)
        eng_model_list.__getitem__ = MagicMock(return_value=_make_engine_model())

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=port_model_list)
        engine_svc = MagicMock()
        engine_svc.get.return_value = ServiceResult.success(data=eng_model_list)

        mapping_svc = MagicMock()
        mapping_svc.get_engine_portfolio_mapping.return_value = ServiceResult.success(data=[])
        mapping_svc.create_engine_portfolio_mapping.return_value = ServiceResult.error(
            "模式不兼容: BACKTEST engine 不能绑定 PAPER/LIVE portfolio"
        )

        container = _mock_container(
            engine_service=engine_svc,
            portfolio_service=portfolio_svc,
            mapping_service=mapping_svc,
        )

        with (
            patch("ginkgo.data.containers.container", container),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(
                engine_cli.app,
                ["bind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "port-uuid"],
            )
        assert result.exit_code == 1, f"模式不兼容应非 0 退出: {result.output}"
        assert "模式不兼容" in result.output, f"输出应含错误信息: {result.output}"
        assert "binding created successfully" not in result.output.lower()


class TestUnbindPortfolio:
    """Tests for the 'unbind-portfolio' command."""

    @pytest.mark.unit
    @pytest.mark.cli
    def test_unbind_with_confirm(self, cli_runner):
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "port-uuid"
        mock_portfolio.name = "TestPortfolio"

        port_model_list = MagicMock()
        port_model_list.__len__ = MagicMock(return_value=1)
        port_model_list.__getitem__ = MagicMock(return_value=mock_portfolio)

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=port_model_list)

        mapping_svc = MagicMock()
        mapping_svc.delete_engine_portfolio_mapping.return_value = ServiceResult.success(data=None)

        container = _mock_container(
            portfolio_service=portfolio_svc,
            mapping_service=mapping_svc,
        )

        with (
            patch("ginkgo.data.containers.container", container),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(
                engine_cli.app,
                ["unbind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "port-uuid", "--confirm"],
            )
        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()

    @pytest.mark.unit
    @pytest.mark.cli
    def test_unbind_with_yes_short_flag(self, cli_runner):
        """-y 短标志成功解绑（#6006: 统一确认标志跨命令一致）"""
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "port-uuid"
        mock_portfolio.name = "TestPortfolio"

        port_model_list = MagicMock()
        port_model_list.__len__ = MagicMock(return_value=1)
        port_model_list.__getitem__ = MagicMock(return_value=mock_portfolio)

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=port_model_list)

        mapping_svc = MagicMock()
        mapping_svc.delete_engine_portfolio_mapping.return_value = ServiceResult.success(data=None)

        container = _mock_container(
            portfolio_service=portfolio_svc,
            mapping_service=mapping_svc,
        )

        with (
            patch("ginkgo.data.containers.container", container),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(
                engine_cli.app,
                ["unbind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "port-uuid", "-y"],
            )
        assert result.exit_code == 0
        assert "deleted successfully" in result.output.lower()
        mapping_svc.delete_engine_portfolio_mapping.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.cli
    def test_unbind_missing_confirm(self, cli_runner):
        result = cli_runner.invoke(
            engine_cli.app,
            ["unbind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "port-uuid"],
        )
        assert result.exit_code == 1
        assert "--confirm" in result.output

    @pytest.mark.unit
    @pytest.mark.cli
    def test_unbind_service_failure(self, cli_runner):
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "port-uuid"
        mock_portfolio.name = "TestPortfolio"

        port_model_list = MagicMock()
        port_model_list.__len__ = MagicMock(return_value=1)
        port_model_list.__getitem__ = MagicMock(return_value=mock_portfolio)

        portfolio_svc = MagicMock()
        portfolio_svc.get.return_value = ServiceResult.success(data=port_model_list)

        mapping_svc = MagicMock()
        mapping_svc.delete_engine_portfolio_mapping.return_value = ServiceResult.error(error="binding not found")

        container = _mock_container(
            portfolio_service=portfolio_svc,
            mapping_service=mapping_svc,
        )

        with (
            patch("ginkgo.data.containers.container", container),
            patch("ginkgo.client.engine_cli.resolve_engine_id", return_value="aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa"),
        ):
            result = cli_runner.invoke(
                engine_cli.app,
                ["unbind-portfolio", "aaaaaaaa-1111-aaaa-1111-aaaaaaaaaaaa", "port-uuid", "--confirm"],
            )
        assert result.exit_code == 1
        assert "Failed" in result.output or "not found" in result.output


# ===========================================================================
# #5375: resolve_engine_id 的 fuzzy 搜索分支
# ===========================================================================


class TestResolveEngineIdFuzzy:
    """#5375: 模糊搜索命中时 resolve_engine_id 必须返回 UUID，不能崩溃。

    根因: engine_cli_helpers.py 仅导入 ``Table as RichTable``，而 fuzzy 分支
    用了裸名 ``Table`` 触发 NameError，被外层 except 吞掉伪装成"解析失败"。
    现有 cat 测试均 patch 掉 resolve_engine_id，该路径从未被覆盖。
    """

    @pytest.mark.unit
    @pytest.mark.cli
    def test_fuzzy_match_returns_uuid_without_crash(self):
        from ginkgo.client.engine_cli_helpers import resolve_engine_id

        engine = _make_engine_model(name="low_usage_engine")
        svc = _mock_engine_service()
        # UUID 精确查找与 name 精确查找均空 -> 落入 fuzzy 分支
        svc.get.return_value = ServiceResult.success(data=[])
        svc.fuzzy_search.return_value = ServiceResult.success(data=[engine])
        container = _mock_container(engine_service=svc)

        with patch("ginkgo.data.containers.container", container):
            resolved = resolve_engine_id("low_usage_en")

        # fuzzy 命中第一条的 UUID 应被返回，而非因 NameError 返回 None
        assert resolved == engine.uuid


# ---------------------------------------------------------------------------
# #5988: engine create 输出 Engine ID 应为纯 UUID，非 dict repr
# ---------------------------------------------------------------------------


class TestEngineCreate:
    """#5988: ``engine create`` 成功后 ``Engine ID`` 行应只含纯 UUID 字符串。

    Service 层 ``engine_service.add`` 返回 ``data={"engine_info": {...}}``（dict），
    而非带 ``.uuid`` 属性的 Model 对象。旧代码用 ``hasattr(result.data, 'uuid')``
    探测 dict 必然 False，回退分支把整个 dict ``repr`` 当成 Engine ID 打印。
    """

    @pytest.mark.unit
    @pytest.mark.cli
    def test_create_shows_pure_uuid_not_dict_repr(self, cli_runner):
        engine_info = {
            "uuid": "abc123def4567890abcdef1234567890",
            "name": "test_engine",
            "is_live": False,
            "status": "IDLE",
            "desc": "回测引擎: test_engine",
        }
        svc = _mock_engine_service(add=ServiceResult.success(data={"engine_info": engine_info}))
        with patch("ginkgo.data.containers.container", _mock_container(engine_service=svc)):
            result = cli_runner.invoke(engine_cli.app, ["create", "-n", "test_engine", "-t", "backtest"])

        assert result.exit_code == 0, result.output
        engine_id_lines = [l for l in result.output.splitlines() if "Engine ID" in l]
        assert engine_id_lines, f"未找到 Engine ID 行:\n{result.output}"
        engine_id_line = engine_id_lines[0]
        # dict repr 含 '{' / '}' —— 纯 UUID 行不应含这些
        assert "{" not in engine_id_line, f"Engine ID 行含 dict repr:\n{engine_id_line}"
        assert "abc123def4567890abcdef1234567890" in engine_id_line
