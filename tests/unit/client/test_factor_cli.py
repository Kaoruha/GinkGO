"""ginkgo factor CLI 接线测试 -- #6792 Phase 1 Slice 3

验证 factor_cli.materialize / libraries 命令的参数解析、service 调用接线、
输出格式与退出码。service/crud 经 monkeypatch 注入 mock, 不触发 container/DB。

核心增量物化逻辑由 test_services.py::TestFactorService 覆盖, 此处只验 CLI 薄层接线。
"""
import re
import pytest
from unittest.mock import MagicMock

from typer.testing import CliRunner

from ginkgo.client import factor_cli
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ENTITY_TYPES


runner = CliRunner()


def _strip_ansi(s: str) -> str:
    """rich Console 给输出加了 ANSI 色码, 会把含变量/引号的字符串拆散
    (如 'nope' 被引号高亮、数字 2 被数值高亮)。去色后再做子串断言。"""
    return re.sub(r'\x1b\[[0-9;]*m', '', s)


def _ok_result(**overrides):
    """构造 success=True 的 ServiceResult, 含默认物化统计数据。"""
    data = {
        "factor_count": 158,
        "processed_entities": 1,
        "skipped_entities": 0,
        "total_factors_stored": 1580,
    }
    data.update(overrides)
    return ServiceResult(success=True, data=data)


@pytest.fixture
def patched_cli(monkeypatch):
    """注入 mock factor_service + factor_crud, 返回 (mock_svc, mock_crud)。"""
    mock_svc = MagicMock()
    mock_crud = MagicMock()
    monkeypatch.setattr(factor_cli, "_get_factor_service", lambda: mock_svc)
    monkeypatch.setattr(factor_cli, "_get_factor_crud", lambda: mock_crud)
    return mock_svc, mock_crud


@pytest.mark.unit
class TestFactorCliMaterialize:
    def test_materialize_success_calls_service_with_incremental(self, patched_cli):
        """3a: 成功路径 → exit 0, 调 service, incremental=True + factor_crud 注入。"""
        mock_svc, mock_crud = patched_cli
        mock_svc.calculate_factors_by_library.return_value = _ok_result()

        result = runner.invoke(factor_cli.app, [
            "materialize", "alpha158",
            "--start", "2024-01-01", "--end", "2024-12-31",
            "-c", "000001.SZ",
        ])

        assert result.exit_code == 0, result.output
        mock_svc.calculate_factors_by_library.assert_called_once()
        kwargs = mock_svc.calculate_factors_by_library.call_args.kwargs
        assert kwargs["library_name"] == "alpha158"
        assert kwargs["entity_ids"] == ["000001.SZ"]
        assert kwargs["start_date"] == "2024-01-01"
        assert kwargs["end_date"] == "2024-12-31"
        assert kwargs["incremental"] is True
        assert kwargs["factor_crud"] is mock_crud
        assert kwargs["entity_type"] == ENTITY_TYPES.STOCK
        assert "物化完成" in result.output

    def test_materialize_multi_entities(self, patched_cli):
        """3a-b: 多个 -c 全部透传给 service 的 entity_ids。"""
        mock_svc, _ = patched_cli
        mock_svc.calculate_factors_by_library.return_value = _ok_result()

        result = runner.invoke(factor_cli.app, [
            "materialize", "alpha158",
            "--start", "2024-01-01", "--end", "2024-12-31",
            "-c", "000001.SZ", "-c", "000002.SZ",
        ])

        assert result.exit_code == 0, result.output
        kwargs = mock_svc.calculate_factors_by_library.call_args.kwargs
        assert kwargs["entity_ids"] == ["000001.SZ", "000002.SZ"]

    def test_materialize_full_flag_disables_incremental(self, patched_cli):
        """3d: --full → incremental=False (全量重算, 不查已物化)。"""
        mock_svc, _ = patched_cli
        mock_svc.calculate_factors_by_library.return_value = _ok_result()

        result = runner.invoke(factor_cli.app, [
            "materialize", "alpha158",
            "--start", "2024-01-01", "--end", "2024-12-31",
            "-c", "000001.SZ", "--full",
        ])

        assert result.exit_code == 0, result.output
        kwargs = mock_svc.calculate_factors_by_library.call_args.kwargs
        assert kwargs["incremental"] is False
        assert "--full" in result.output

    def test_materialize_service_failure_exits_nonzero(self, patched_cli):
        """3b: service 返回 success=False → exit 1 + 打印 error。"""
        mock_svc, _ = patched_cli
        mock_svc.calculate_factors_by_library.return_value = ServiceResult(
            success=False, error="Library 'nope' not found"
        )

        result = runner.invoke(factor_cli.app, [
            "materialize", "nope",
            "--start", "2024-01-01", "--end", "2024-12-31",
            "-c", "000001.SZ",
        ])

        assert result.exit_code == 1, result.output
        out = _strip_ansi(result.output)
        assert "物化失败" in out
        assert "Library 'nope' not found" in out

    def test_materialize_no_entity_exits_nonzero(self, patched_cli):
        """3c: 未指定 --entity → exit 1, 不调 service。"""
        mock_svc, _ = patched_cli

        result = runner.invoke(factor_cli.app, [
            "materialize", "alpha158",
            "--start", "2024-01-01", "--end", "2024-12-31",
        ])

        assert result.exit_code == 1, result.output
        assert "--entity" in result.output
        mock_svc.calculate_factors_by_library.assert_not_called()

    def test_materialize_invalid_entity_type_exits_nonzero(self, patched_cli):
        """3e: 无效 entity_type → exit 1, 不调 service。"""
        mock_svc, _ = patched_cli

        result = runner.invoke(factor_cli.app, [
            "materialize", "alpha158",
            "--start", "2024-01-01", "--end", "2024-12-31",
            "-c", "000001.SZ", "--entity-type", "nonexistent_type",
        ])

        assert result.exit_code == 1, result.output
        assert "nonexistent_type" in result.output
        mock_svc.calculate_factors_by_library.assert_not_called()

    def test_materialize_incremental_hint_when_skipped(self, patched_cli):
        """增量跳过提示: skipped>0 + 非 full → 输出 '增量跳过' 提示。"""
        mock_svc, _ = patched_cli
        mock_svc.calculate_factors_by_library.return_value = _ok_result(skipped_entities=2)

        result = runner.invoke(factor_cli.app, [
            "materialize", "alpha158",
            "--start", "2024-01-01", "--end", "2024-12-31",
            "-c", "000001.SZ",
        ])

        assert result.exit_code == 0, result.output
        assert "增量跳过 2" in _strip_ansi(result.output)


@pytest.mark.unit
class TestFactorCliLibraries:
    def test_libraries_lists_registered(self, patched_cli):
        """3f: libraries 命令列出 registry 的库 + 因子数。"""
        mock_svc, _ = patched_cli
        registry = MagicMock()
        registry.get_registered_libraries.return_value = {
            "alpha158": object(),
            "world_quant_alpha101": object(),
        }
        registry.get_factors_by_library.side_effect = lambda name: {
            "alpha158": {"KMID": "...", "MA5": "..."},
            "world_quant_alpha101": {"Alpha001": "..."},
        }[name]
        mock_svc.factor_registry = registry

        result = runner.invoke(factor_cli.app, ["libraries"])

        assert result.exit_code == 0, result.output
        assert "alpha158" in result.output
        assert "world_quant_alpha101" in result.output
        assert "2" in result.output  # alpha158 因子数

    def test_libraries_empty(self, patched_cli):
        """无库时输出提示而非崩溃。"""
        mock_svc, _ = patched_cli
        registry = MagicMock()
        registry.get_registered_libraries.return_value = {}
        mock_svc.factor_registry = registry

        result = runner.invoke(factor_cli.app, ["libraries"])

        assert result.exit_code == 0, result.output
        assert "未发现" in result.output
