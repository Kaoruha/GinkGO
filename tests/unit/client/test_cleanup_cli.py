"""
性能: ~轻量, 快速
Unit tests for `ginkgo cleanup` command (core_cli.cleanup) + dry_run 透传。

覆盖：
  1. Help/注册：cleanup 出现在 root help；--help 列出 --yes/-y 与 --dry-run
  2. 命令确认流：--dry-run 跳过确认；--yes 跳过确认；无 flag 走 typer.confirm
     （接受放行 / 拒绝 exit 1）；失败 exit 1
  3. _cleanup_invalid_data 透传：dry_run=True/False 都把 flag 传到 6 个 service 调用
  4. service 层 dry_run 行为：mapping_service.cleanup_orphaned_mappings
     dry_run=True 只 COUNT 不 DELETE；dry_run=False 执行 DELETE
"""

import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_main_app():
    """Return the Typer main app (lazy-loaded)."""
    from main import get_main_app
    return get_main_app()


def _ok_cleanup_result():
    """_cleanup_invalid_data 的成功桩返回值。"""
    return {
        "success": True,
        "cleaned_count": 0,
        "services_cleaned": [],
        "services_failed": [],
        "warnings": [],
        "details": {},
        "dry_run": False,
    }


def _make_container():
    """构造 mock container，各 service 清理方法返回安全 0 计数（避免 MagicMock > 0 报错）。

    返回 (container, services) 以便断言调用参数。
    """
    container = MagicMock()

    mapping_svc = MagicMock()
    mapping_svc.cleanup_orphaned_mappings.return_value = ServiceResult.success(
        {"cleaned_count": 0, "cleaning_details": [], "dry_run": False}
    )
    container.mapping_service.return_value = mapping_svc

    param_svc = MagicMock()
    param_svc.cleanup_orphaned_params.return_value = ServiceResult.success(
        {"deleted_count": 0, "dry_run": False}
    )
    container.param_service.return_value = param_svc

    redis_svc = MagicMock()
    redis_svc.cleanup_dead_tasks.return_value = 0
    redis_svc.cleanup_expired_function_cache.return_value = 0
    container.redis_service.return_value = redis_svc

    signal_svc = MagicMock()
    signal_svc.cleanup.return_value = ServiceResult.success(0)
    container.signal_tracking_service.return_value = signal_svc

    services = {
        "mapping": mapping_svc,
        "param": param_svc,
        "redis": redis_svc,
        "signal": signal_svc,
    }
    return container, services


# ===========================================================================
# 1. Help / 注册
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestCleanupHelp:
    def test_root_help_shows_cleanup(self, cli_runner):
        """cleanup 已注册到 root app。"""
        result = cli_runner.invoke(_get_main_app(), ["--help"])
        assert result.exit_code == 0
        assert "cleanup" in result.output

    def test_cleanup_help_shows_options(self, cli_runner):
        """cleanup --help 列出 --yes/-y 与 --dry-run。

        用中文描述断言（Rich 给选项名加 ANSI 色码会把 --yes 字面量切断，
        但 help 描述文本无样式）。
        """
        result = cli_runner.invoke(_get_main_app(), ["cleanup", "--help"])
        assert result.exit_code == 0
        assert "跳过确认提示" in result.output
        assert "仅预览将清理的数量" in result.output


# ===========================================================================
# 2. 命令确认流
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestCleanupConfirmFlow:
    def test_dry_run_skips_confirm_and_passes_true(self, cli_runner):
        """--dry-run 不触发确认，打印 Dry-run 横幅，并以 dry_run=True 调下层。"""
        with patch(
            "ginkgo.client.core_cli._cleanup_invalid_data",
            return_value=_ok_cleanup_result(),
        ) as m, patch("ginkgo.client.core_cli.typer.confirm") as conf:
            result = cli_runner.invoke(_get_main_app(), ["cleanup", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry-run" in result.output
        conf.assert_not_called()
        m.assert_called_once_with(dry_run=True)

    def test_yes_flag_skips_confirm_and_passes_false(self, cli_runner):
        """--yes 跳过确认，以 dry_run=False 调下层。"""
        with patch(
            "ginkgo.client.core_cli._cleanup_invalid_data",
            return_value=_ok_cleanup_result(),
        ) as m, patch("ginkgo.client.core_cli.typer.confirm") as conf:
            result = cli_runner.invoke(_get_main_app(), ["cleanup", "--yes"])
        assert result.exit_code == 0
        conf.assert_not_called()
        m.assert_called_once_with(dry_run=False)

    def test_confirm_accepted_proceeds(self, cli_runner):
        """无 flag + 用户确认 → 放行，dry_run=False。"""
        with patch("ginkgo.client.core_cli.typer.confirm", return_value=True) as conf, \
             patch(
                 "ginkgo.client.core_cli._cleanup_invalid_data",
                 return_value=_ok_cleanup_result(),
             ) as m:
            result = cli_runner.invoke(_get_main_app(), ["cleanup"])
        assert result.exit_code == 0
        conf.assert_called_once()
        m.assert_called_once_with(dry_run=False)

    def test_confirm_rejected_exits_1_and_skips_cleanup(self, cli_runner):
        """无 flag + 用户拒绝 → exit 1，打印已取消，不调下层清理。"""
        with patch("ginkgo.client.core_cli.typer.confirm", return_value=False), \
             patch("ginkgo.client.core_cli._cleanup_invalid_data") as m:
            result = cli_runner.invoke(_get_main_app(), ["cleanup"])
        assert result.exit_code == 1
        assert "已取消" in result.output
        m.assert_not_called()

    def test_failure_exits_1(self, cli_runner):
        """下层返回 success=False → exit 1（--yes 避开确认噪音）。"""
        fail = _ok_cleanup_result()
        fail["success"] = False
        with patch("ginkgo.client.core_cli._cleanup_invalid_data", return_value=fail):
            result = cli_runner.invoke(_get_main_app(), ["cleanup", "--yes"])
        assert result.exit_code == 1


# ===========================================================================
# 3. _cleanup_invalid_data 透传 dry_run 到 6 个 service 调用
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestCleanupInvalidDataPropagation:
    def test_dry_run_true_propagates_to_all_services(self):
        """dry_run=True 透传到 mapping/param/redis(dead+cache)/signal 全部调用点。"""
        container, svcs = _make_container()
        with patch("ginkgo.data.containers.container", container):
            from ginkgo.client.core_cli import _cleanup_invalid_data
            result = _cleanup_invalid_data(dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        svcs["mapping"].cleanup_orphaned_mappings.assert_called_once_with(dry_run=True)
        svcs["param"].cleanup_orphaned_params.assert_called_once_with(dry_run=True)
        svcs["redis"].cleanup_dead_tasks.assert_called_once_with(max_idle_time=3600, dry_run=True)
        svcs["redis"].cleanup_expired_function_cache.assert_called_once_with(dry_run=True)
        svcs["signal"].cleanup.assert_called_once_with(days_to_keep=30, dry_run=True)

    def test_dry_run_false_propagates_to_all_services(self):
        """dry_run=False 透传到全部调用点（默认删除路径）。"""
        container, svcs = _make_container()
        with patch("ginkgo.data.containers.container", container):
            from ginkgo.client.core_cli import _cleanup_invalid_data
            result = _cleanup_invalid_data(dry_run=False)
        assert result["success"] is True
        assert result["dry_run"] is False
        svcs["mapping"].cleanup_orphaned_mappings.assert_called_once_with(dry_run=False)
        svcs["param"].cleanup_orphaned_params.assert_called_once_with(dry_run=False)
        svcs["redis"].cleanup_dead_tasks.assert_called_once_with(max_idle_time=3600, dry_run=False)
        svcs["redis"].cleanup_expired_function_cache.assert_called_once_with(dry_run=False)
        svcs["signal"].cleanup.assert_called_once_with(days_to_keep=30, dry_run=False)


# ===========================================================================
# 4. service 层 dry_run 行为：mapping_service（重构后的 rules 循环）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestMappingServiceDryRun:
    """mapping_service.cleanup_orphaned_mappings：dry_run 只 COUNT 不 DELETE。"""

    def _make_svc_and_session(self, counts):
        """counts: list of 6 ints 对应 6 条 rule 的 COUNT 标量返回。"""
        mock_ep = MagicMock()
        mock_pf = MagicMock()
        mock_eh = MagicMock()
        mock_param = MagicMock()
        from ginkgo.data.services.mapping_service import MappingService
        svc = MappingService(
            engine_portfolio_mapping_crud=mock_ep,
            portfolio_file_mapping_crud=mock_pf,
            engine_handler_mapping_crud=mock_eh,
            param_crud=mock_param,
        )
        mock_session = MagicMock()
        mock_ep.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_ep.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # 实现里 COUNT 与 DELETE 在规则循环内交替执行（COUNT 必先于该规则的 DELETE，
        # 且 COUNT 按规则顺序触发）。故按 SQL 文本路由：COUNT → 弹出下一个计数，
        # DELETE → 返回 rowcount。与交替顺序无关，最稳。
        count_queue = list(counts)

        def _execute_side_effect(stmt, *_a, **_k):
            result = MagicMock()
            if "COUNT" in str(stmt).upper():
                result.scalar.return_value = count_queue.pop(0)
            else:  # DELETE
                result.rowcount = 1
            return result

        mock_session.execute.side_effect = _execute_side_effect
        return svc, mock_session

    def test_dry_run_true_does_not_delete(self):
        """dry_run=True：仅 6 次 COUNT，无 DELETE 被执行。"""
        svc, mock_session = self._make_svc_and_session([1, 0, 1, 0, 0, 0])
        result = svc.cleanup_orphaned_mappings(dry_run=True)
        assert result.success is True
        # 只应有 6 次 COUNT 查询，0 次 DELETE
        assert mock_session.execute.call_count == 6
        # 统计到 2 个孤立映射（第 1、3 条 rule 各 1）
        assert result.data["cleaned_count"] == 2
        assert result.data["dry_run"] is True

    def test_dry_run_false_executes_delete(self):
        """dry_run=False：6 次 COUNT + 命中 rule 各 1 次 DELETE。"""
        svc, mock_session = self._make_svc_and_session([1, 0, 1, 0, 0, 0])
        result = svc.cleanup_orphaned_mappings(dry_run=False)
        assert result.success is True
        # 6 COUNT + 2 DELETE = 8 次 execute
        assert mock_session.execute.call_count == 8
        assert result.data["cleaned_count"] == 2
        assert result.data["dry_run"] is False

    def test_dry_run_true_zero_orphans_issues_no_delete(self):
        """dry_run=True 且零孤立：仅 COUNT，DELETE 0 次。"""
        svc, mock_session = self._make_svc_and_session([0, 0, 0, 0, 0, 0])
        result = svc.cleanup_orphaned_mappings(dry_run=True)
        assert result.success is True
        assert mock_session.execute.call_count == 6
        assert result.data["cleaned_count"] == 0
