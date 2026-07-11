"""
性能: 221MB RSS, 1.86s, 7 tests [PASS]
Unit tests for cli_utils.py helper functions.

cli_utils provides utility functions for tree display and parameter retrieval:
  - _get_component_parameters: Fetch params from database via param_crud
  - _add_portfolio_components: Build tree nodes for portfolio's components
  - _show_portfolio_tree: Display portfolio as rich tree
  - _show_engine_tree: Display engine as rich tree (with nested portfolios)

Mock strategy:
  - Patch "ginkgo.data.containers.container" for service access
  - Functions are tested directly (not via CLI runner)
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import uuid
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.client import cli_utils
from ginkgo.enums import FILE_TYPES


def _make_service_result(df: pd.DataFrame, success: bool = True) -> MagicMock:
    """模拟 ServiceResult：.success + .data(pandas.DataFrame)。
    #6136 后调用方走 mapping_service._df 出口，data 即 DataFrame（类型即契约）。"""
    result = MagicMock()
    result.success = success
    result.data = df
    return result


# ============================================================================
# 1. _get_component_parameters
# ============================================================================


# NOTE: Testing private methods directly - consider refactoring to test through public CLI interface

@pytest.mark.unit
@pytest.mark.cli
class TestGetComponentParameters:
    """Tests for _get_component_parameters helper."""

    def test_returns_empty_dict_when_no_params(self):
        crud = MagicMock()
        crud.find.return_value = pd.DataFrame(columns=["value"])
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.cruds.param.return_value = crud
            result = cli_utils._get_component_parameters("mapping-1", "file-1", FILE_TYPES.STRATEGY)
        assert result == {}

    def test_returns_params_dict(self):
        crud = MagicMock()
        crud.find.return_value = pd.DataFrame({"value": [100, 0.5]})
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.cruds.param.return_value = crud
            result = cli_utils._get_component_parameters("mapping-1", "file-1", FILE_TYPES.STRATEGY)
        assert result == {"param_0": 100, "param_1": 0.5}

    def test_returns_empty_on_exception(self):
        crud = MagicMock()
        crud.find.side_effect = Exception("DB error")
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.cruds.param.return_value = crud
            result = cli_utils._get_component_parameters("mapping-1", "file-1", FILE_TYPES.STRATEGY)
        assert result == {}


# ============================================================================
# 2. _add_portfolio_components
# ============================================================================


# NOTE: Testing private methods directly - consider refactoring to test through public CLI interface

@pytest.mark.unit
@pytest.mark.cli
class TestAddPortfolioComponents:
    """Tests for _add_portfolio_components tree builder."""

    def test_no_components_shows_message(self):
        mock_mapping = MagicMock()
        mock_mapping.get_portfolio_file_mappings_df.return_value = _make_service_result(
            pd.DataFrame(columns=["portfolio_id", "type", "name", "file_id", "uuid"])
        )
        parent = MagicMock()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.mapping_service.return_value = mock_mapping
            cli_utils._add_portfolio_components(parent, "portfolio-1", False, None)
        parent.add.assert_called_once()
        assert "No components bound" in parent.add.call_args[0][0]

    def test_components_added_to_tree(self):
        mock_mapping = MagicMock()
        mock_mapping.get_portfolio_file_mappings_df.return_value = _make_service_result(pd.DataFrame([
            {"portfolio_id": "portfolio-1", "type": FILE_TYPES.STRATEGY.value,
             "name": "MyStrategy", "file_id": "file-1", "uuid": "mapping-1"}
        ]))
        parent = MagicMock()
        with patch("ginkgo.data.containers.container") as mock_container:
            mock_container.mapping_service.return_value = mock_mapping
            cli_utils._add_portfolio_components(parent, "portfolio-1", False, None)
        # Should have added a section node via parent.add
        assert parent.add.call_count >= 1


# ============================================================================
# 3. _show_portfolio_tree / _show_engine_tree
# ============================================================================


# NOTE: Testing private methods directly - consider refactoring to test through public CLI interface

@pytest.mark.unit
@pytest.mark.cli
class TestShowTree:
    """Tests for tree display functions."""

    def test_show_portfolio_tree(self):
        portfolio_row = {"name": "TestPortfolio", "uuid": "p-1"}
        mock_mapping = MagicMock()
        mock_mapping.get_portfolio_file_mappings_df.return_value = _make_service_result(
            pd.DataFrame(columns=["portfolio_id", "type", "name", "file_id", "uuid"])
        )
        with patch("ginkgo.data.containers.container") as mock_container, \
             patch.object(cli_utils.console, "print") as mock_print:
            mock_container.mapping_service.return_value = mock_mapping
            cli_utils._show_portfolio_tree(portfolio_row, False, None)
        mock_print.assert_called_once()

    def test_show_engine_tree_no_portfolios(self):
        engine_row = {"name": "TestEngine", "uuid": "e-1"}
        mock_mapping = MagicMock()
        mock_mapping.get_engine_portfolio_mappings_df.return_value = _make_service_result(
            pd.DataFrame(columns=["engine_id", "portfolio_id"])
        )
        with patch("ginkgo.data.containers.container") as mock_container, \
             patch.object(cli_utils.console, "print") as mock_print:
            mock_container.mapping_service.return_value = mock_mapping
            cli_utils._show_engine_tree(engine_row, False, None)
        mock_print.assert_called_once()


# ============================================================================
# ADR-021 E2 (#6577): CLI 输出层 helper 测试
# 6 个 helper: is_interactive / make_console / GinkgoJSONEncoder /
#             safe_confirm / make_progress / format_result
# ============================================================================

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import typer


# ----------------------------------------------------------------------------
# is_interactive (ADR-021 第 2 维: TTY 推断 + 显式覆盖)
# ----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestIsInteractive:
    def test_default_returns_stdin_isatty_true(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert cli_utils.is_interactive() is True

    def test_default_returns_stdin_isatty_false(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert cli_utils.is_interactive() is False

    def test_explicit_true_overrides_non_tty(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert cli_utils.is_interactive(explicit=True) is True

    def test_explicit_false_overrides_tty(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            assert cli_utils.is_interactive(explicit=False) is False


# ----------------------------------------------------------------------------
# make_console (ADR-021 第 7 维: Layer1 自动 + Layer2 NO_COLOR env + Layer3 --no-color)
# ----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestMakeConsole:
    def test_default_color_system_auto_when_no_color_disabled(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console(no_color=False)
            _, kwargs = MockConsole.call_args
            assert kwargs["color_system"] == "auto"

    def test_no_color_flag_disables_color(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console(no_color=True)
            _, kwargs = MockConsole.call_args
            assert kwargs["color_system"] is None

    def test_no_color_env_disables_color(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console(no_color=False)
            _, kwargs = MockConsole.call_args
            assert kwargs["color_system"] is None

    def test_no_color_flag_overrides_even_when_env_absent(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console(no_color=True)
            _, kwargs = MockConsole.call_args
            assert kwargs["color_system"] is None

    def test_stderr_always_true(self):
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console()
            _, kwargs = MockConsole.call_args
            assert kwargs["stderr"] is True

    def test_legacy_windows_false(self):
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console()
            _, kwargs = MockConsole.call_args
            assert kwargs["legacy_windows"] is False

    def test_emoji_true_when_isatty(self):
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console(isatty=True)
            _, kwargs = MockConsole.call_args
            assert kwargs["emoji"] is True

    def test_emoji_false_when_not_isatty(self):
        with patch("ginkgo.client.cli_utils.Console") as MockConsole:
            cli_utils.make_console(isatty=False)
            _, kwargs = MockConsole.call_args
            assert kwargs["emoji"] is False

    def test_emoji_follows_stdin_isatty_by_default(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True
            with patch("ginkgo.client.cli_utils.Console") as MockConsole:
                cli_utils.make_console()
                _, kwargs = MockConsole.call_args
                assert kwargs["emoji"] is True


# ----------------------------------------------------------------------------
# GinkgoJSONEncoder (ADR-021 第 10 维)
# ----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestGinkgoJSONEncoder:
    def test_datetime_iso8601_with_T_separator(self):
        dt = datetime(2025, 6, 1, 12, 30, 45, tzinfo=timezone.utc)
        out = json.dumps(dt, cls=cli_utils.GinkgoJSONEncoder)
        assert "2025-06-01T12:30:45" in out
        # 反例: str(datetime) 用空格分隔
        assert "2025-06-01 12:30:45" not in out

    def test_date_iso8601(self):
        d = date(2025, 6, 1)
        out = json.dumps(d, cls=cli_utils.GinkgoJSONEncoder)
        assert out == '"2025-06-01"'

    def test_decimal_as_str_preserves_precision(self):
        out = json.dumps(Decimal("1.005"), cls=cli_utils.GinkgoJSONEncoder)
        assert out == '"1.005"'

    def test_uuid_with_dashes(self):
        u = uuid.UUID("12345678-1234-5678-1234-567812345678")
        out = json.dumps(u, cls=cli_utils.GinkgoJSONEncoder)
        assert out == '"12345678-1234-5678-1234-567812345678"'

    def test_dataframe_to_records(self):
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        out = json.loads(json.dumps(df, cls=cli_utils.GinkgoJSONEncoder))
        assert out == [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]

    def test_pydantic_basemodel_model_dump_json(self):
        from pydantic import BaseModel

        class M(BaseModel):
            x: int = 1
            y: str = "abc"

        out = json.loads(json.dumps(M(), cls=cli_utils.GinkgoJSONEncoder))
        assert out == {"x": 1, "y": "abc"}

    def test_sqlalchemy_model_columns_dict(self):
        # 真实 DeclarativeBase（isinstance 判定，非 SimpleNamespace duck-typing）
        from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

        class Base(DeclarativeBase):
            pass

        class Record(Base):
            __tablename__ = "record_cli_utils_test"
            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column()

        record = Record(id=42, name="foo")
        out = json.loads(json.dumps(record, cls=cli_utils.GinkgoJSONEncoder))
        assert out == {"id": 42, "name": "foo"}

    def test_magicmock_raises_typeerror_not_infinite_recursion(self):
        """防回归（OOM 根因）：MagicMock 对任意属性 hasattr 恒 True，
        旧 ``hasattr(obj, "model_dump")`` duck-typing 触发 C 层无限递归 ~1GB/s → OOM。
        isinstance 白名单后须抛 TypeError（响亮失败），绝不递归。"""
        m = MagicMock()
        with pytest.raises(TypeError):
            json.dumps(m, cls=cli_utils.GinkgoJSONEncoder)

    def test_unknown_type_falls_back_to_default(self):
        # 未覆盖类型应让父类 default 抛 TypeError
        with pytest.raises(TypeError):
            json.dumps(object(), cls=cli_utils.GinkgoJSONEncoder)


# ----------------------------------------------------------------------------
# safe_confirm (ADR-021 第 3 维: TTY 守卫 + 专用异常)
# ----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestSafeConfirm:
    def test_tty_calls_typer_confirm(self):
        with patch("sys.stdin") as mock_stdin, \
             patch.object(cli_utils.typer, "confirm", return_value=True) as mock_c:
            mock_stdin.isatty.return_value = True
            assert cli_utils.safe_confirm("sure?") is True
            mock_c.assert_called_once()

    def test_non_tty_require_tty_raises_cli_confirm_error(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            with pytest.raises(cli_utils.CliConfirmError):
                cli_utils.safe_confirm("sure?", require_tty=True)

    def test_cli_confirm_error_is_exception_subclass(self):
        # 呼应 arch_typer_exit_caught_by_except: 专用异常仍继承 Exception
        # 调用方按具体类型捕获，避免被通用 except 吞
        assert issubclass(cli_utils.CliConfirmError, Exception)

    def test_non_tty_yes_flag_returns_true(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert cli_utils.safe_confirm("sure?", yes_flag=True) is True

    def test_non_tty_yes_flag_short_circuits_before_require_check(self):
        # yes_flag=True 即使 require_tty=True 也返 True（--yes 优先级最高）
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert cli_utils.safe_confirm("sure?", require_tty=True, yes_flag=True) is True

    def test_non_tty_require_false_returns_default(self):
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert cli_utils.safe_confirm("sure?", require_tty=False, default=True) is True
            assert cli_utils.safe_confirm("sure?", require_tty=False, default=False) is False


# ----------------------------------------------------------------------------
# make_progress (ADR-021 第 8 维)
# ----------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.cli
class TestMakeProgress:
    def test_json_format_returns_none(self):
        assert cli_utils.make_progress(format="json", isatty=True) is None

    def test_non_tty_returns_none(self):
        assert cli_utils.make_progress(format="text", isatty=False) is None

    def test_tty_text_returns_progress_with_transient(self):
        from rich.progress import Progress
        p = cli_utils.make_progress(format="text", isatty=True)
        assert isinstance(p, Progress)
        # transient 存到内部 Live 对象（rich Progress 不暴露为顶层属性）
        assert p.live.transient is True

    def test_progress_console_targets_stderr(self):
        p = cli_utils.make_progress(format="text", isatty=True)
        assert p.console.file is sys.stderr


# ----------------------------------------------------------------------------
# format_result (ADR-021 第 5/6/9 维, #6591 实现)
# ----------------------------------------------------------------------------

from ginkgo.data.services.base_service import ServiceResult


@pytest.mark.unit
@pytest.mark.cli
class TestFormatResult:
    """format_result 行为测试（ADR-021 第 5/6/9 维，#6591）。

    三种输出结构（list/get/fail）+ exit code 映射（0/1/2/124）。
    占位测试 test_raises_not_implemented_anchored_to_6576 已随 #6591 实现删除。
    """

    def test_success_list_json_structure(self, capsys):
        """成功 list：data 是 list → {success:true, data:[...], count:N, metadata:{}}"""
        result = ServiceResult.success(data=[{"id": 1}, {"id": 2}])
        cli_utils.format_result(result, format="json", command="list")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True
        assert out["data"] == [{"id": 1}, {"id": 2}]
        assert out["count"] == 2
        assert out["metadata"] == {}

    def test_success_get_json_structure(self, capsys):
        """成功 get：data 非 list → {success:true, data:{...}}（无 count/metadata）"""
        result = ServiceResult.success(data={"uuid": "abc", "name": "foo"})
        cli_utils.format_result(result, format="json", command="get")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True
        assert out["data"] == {"uuid": "abc", "name": "foo"}
        # get 结构不含 count / metadata
        assert "count" not in out
        assert "metadata" not in out

    def test_success_empty_list_has_count_zero(self, capsys):
        """空 list（ADR-021 第 9 维）：count=0，仍是成功 exit 0"""
        result = ServiceResult.success(data=[])
        cli_utils.format_result(result, format="json", command="list")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True
        assert out["data"] == []
        assert out["count"] == 0

    def test_success_does_not_raise_exit(self, capsys):
        """成功路径不 raise typer.Exit（ADR-021 第 6 维：0 = 正常 return）"""
        result = ServiceResult.success(data={"x": 1})
        # 不抛异常即成功路径 return
        cli_utils.format_result(result, format="json", command="get")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True

    def test_fail_json_structure_with_code(self, capsys):
        """失败：{success:false, error:{code, message}, data:null}"""
        result = ServiceResult.failure(message="参数错误", code="BAD_PARAMS")
        with pytest.raises(typer.Exit) as exc_info:
            cli_utils.format_result(result, format="json", command="create")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is False
        assert out["error"] == {"code": "BAD_PARAMS", "message": "参数错误"}
        assert out["data"] is None
        assert exc_info.value.exit_code == 2

    def test_exit_code_bad_params_is_2(self, capsys):
        """exit code 映射：BAD_PARAMS → 2"""
        result = ServiceResult.failure(message="bad", code="BAD_PARAMS")
        with pytest.raises(typer.Exit) as exc_info:
            cli_utils.format_result(result, format="json", command="x")
        assert exc_info.value.exit_code == 2

    def test_exit_code_timeout_is_124(self, capsys):
        """exit code 映射：TIMEOUT → 124（GNU timeout 惯例）"""
        result = ServiceResult.failure(message="超时", code="TIMEOUT")
        with pytest.raises(typer.Exit) as exc_info:
            cli_utils.format_result(result, format="json", command="x")
        assert exc_info.value.exit_code == 124

    def test_exit_code_other_non_none_code_is_1(self, capsys):
        """exit code 映射：其他非 None code（如 NOT_FOUND）→ 1"""
        result = ServiceResult.failure(message="未找到", code="NOT_FOUND")
        with pytest.raises(typer.Exit) as exc_info:
            cli_utils.format_result(result, format="json", command="get")
        assert exc_info.value.exit_code == 1

    def test_exit_code_none_code_failure_is_1(self, capsys):
        """exit code 映射：code=None 的失败 → 1（默认业务失败）"""
        result = ServiceResult.failure(message="未知错误")
        with pytest.raises(typer.Exit) as exc_info:
            cli_utils.format_result(result, format="json", command="x")
        assert exc_info.value.exit_code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"]["code"] is None

    def test_backward_compat_legacy_result_without_code_attr(self, capsys):
        """向后兼容：无 code 属性的旧 ServiceResult（duck-typed）调用不崩"""
        # 旧实例：仅 success/error/data，无 code 属性（模拟 436 处历史调用）
        legacy = SimpleNamespace(success=True, data={"k": "v"}, error="")
        cli_utils.format_result(legacy, format="json", command="get")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True
        assert out["data"] == {"k": "v"}

    def test_backward_compat_legacy_failure_without_code_attr(self, capsys):
        """向后兼容：无 code 属性的旧失败实例 → exit 1，error.code=null"""
        legacy = SimpleNamespace(success=False, data=None, error="旧错误")
        with pytest.raises(typer.Exit) as exc_info:
            cli_utils.format_result(legacy, format="json", command="x")
        assert exc_info.value.exit_code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["error"] == {"code": None, "message": "旧错误"}

    def test_text_format_does_not_raise_not_implemented(self, capsys):
        """format='text' 当前复用 JSON 输出（rich 渲染留 E4/E5），不抛 NotImplementedError"""
        result = ServiceResult.success(data=[{"id": 1}])
        cli_utils.format_result(result, format="text", command="list")
        out = json.loads(capsys.readouterr().out)
        assert out["success"] is True
        assert out["count"] == 1
