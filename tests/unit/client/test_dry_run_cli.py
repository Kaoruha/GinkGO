"""
性能: ~轻量, 快速
destructive 命令的 --dry-run 预览统一测试（核心 6：execution cleanup / kafka purge /
kafka reset / cache clear / portfolio delete / engine delete）。

每命令断言三件事：
  1. --dry-run 出现在 --help（用无样式描述子串，规避 Rich ANSI 切断 --xxx 字面量）
  2. dry-run 路径下破坏性调用（delete / remove / soft_remove / consume / reset_all_workers
     / kafka_topic_set / redis clear）**未被触发**
  3. dry_run=True 透传到 service 层（portfolio/engine），或横幅/计数打印到位

ANSI 剥离：CLI 各模块用模块级 ``Console(emoji=True)`` 强制着色，Rich 会在词边界插入
``\\x1b[1;36m`` 色码把 ``--dry-run``/``2 mapping`` 这类字面量切断，裸子串匹配假阴。
统一用 ``_strip_ansi`` 预处理 output 后再断言。
"""

import os
import re

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI.sub("", s)


def _get_main_app():
    from main import get_main_app
    return get_main_app()


# ===========================================================================
# 公共 helper
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestAnnounceDryRun:
    def test_prints_banner_with_action(self):
        from ginkgo.client.cli_utils import announce_dry_run
        from rich.console import Console
        import io
        buf = io.StringIO()
        announce_dry_run("删除 portfolio", console=Console(file=buf, color_system=None, emoji=False))
        out = _strip_ansi(buf.getvalue())
        assert "Dry-run" in out
        assert "仅预览" in out
        assert "删除 portfolio" in out
        assert "已跳过确认" in out


# ===========================================================================
# execution cleanup
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestExecutionCleanupDryRun:
    def test_help_lists_dry_run(self, cli_runner):
        res = cli_runner.invoke(_get_main_app(), ["execution", "cleanup", "--help"])
        assert res.exit_code == 0
        assert "without deleting" in _strip_ansi(res.output)

    def test_cleanup_node_dry_run_does_not_delete(self):
        """_cleanup_node(dry_run=True)：exists 探测仍跑，delete 不被调用。"""
        from ginkgo.client.execution_cli import _cleanup_node
        rc = MagicMock()
        rc.exists.return_value = 1  # key 存在
        rc.ttl.return_value = 2  # < _STALE_HEARTBEAT_TTL_THRESHOLD(5) → 视为非活跃，放行清理
        skipped, hb, mt = _cleanup_node(rc, "node_1", force=False, dry_run=True)
        assert skipped is False
        assert hb is True and mt is True
        rc.exists.assert_called()  # 探测仍发生
        rc.delete.assert_not_called()  # 关键：dry-run 不删

    def test_cleanup_node_real_run_deletes(self):
        """对照：dry_run=False 仍调用 delete。"""
        from ginkgo.client.execution_cli import _cleanup_node
        rc = MagicMock()
        rc.exists.return_value = 1
        rc.ttl.return_value = 2
        _cleanup_node(rc, "node_1", force=False, dry_run=False)
        assert rc.delete.call_count == 2  # heartbeat + metrics

    def test_command_passes_dry_run_to_cleanup_node(self, cli_runner):
        """execution cleanup --node-id n1 --dry-run → _cleanup_node 收到 dry_run=True。"""
        mock_redis = MagicMock()
        mock_crud = MagicMock()
        mock_crud.redis = mock_redis
        with patch("ginkgo.data.crud.RedisCRUD", return_value=mock_crud), \
             patch("ginkgo.client.execution_cli._cleanup_node", return_value=(False, True, True)) as m:
            res = cli_runner.invoke(_get_main_app(), ["execution", "cleanup", "--node-id", "n1", "--dry-run"])
        assert res.exit_code == 0
        m.assert_called_once()
        assert m.call_args.kwargs.get("dry_run") is True
        # dry-run 横幅 + dry-run 文案（单节点路径用 verb_hb="Would delete"）
        out = _strip_ansi(res.output)
        assert "Dry-run" in out
        assert "Would delete heartbeat" in out


# ===========================================================================
# kafka purge
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestKafkaPurgeDryRun:
    def test_help_lists_dry_run(self, cli_runner):
        res = cli_runner.invoke(_get_main_app(), ["kafka", "purge", "--help"])
        assert res.exit_code == 0
        assert "不实际消费" in _strip_ansi(res.output)

    def test_dry_run_counts_without_consuming(self, cli_runner):
        """purge --dry-run：get_message_count 被调，consume_messages 不被调，打印 Would purge。"""
        kafka_svc = MagicMock()
        kafka_svc.topic_exists.return_value = True
        kafka_svc.get_message_count.return_value = 7
        cont = MagicMock()
        cont.kafka_service.return_value = kafka_svc
        with patch("ginkgo.data.containers.container", cont):
            res = cli_runner.invoke(_get_main_app(), ["kafka", "purge", "mytopic", "--dry-run"])
        assert res.exit_code == 0
        kafka_svc.get_message_count.assert_called_once_with("mytopic")
        # 关键：没有进入消费/删除循环
        kafka_svc._crud_repo.consume_messages.assert_not_called()
        out = _strip_ansi(res.output)
        assert "Dry-run" in out
        assert "Would purge" in out and "7" in out


# ===========================================================================
# kafka reset
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestKafkaResetDryRun:
    def test_help_lists_dry_run(self, cli_runner):
        res = cli_runner.invoke(_get_main_app(), ["kafka", "reset", "--help"])
        assert res.exit_code == 0
        assert "不重建主题" in _strip_ansi(res.output)

    def test_dry_run_reports_workers_without_resetting(self, cli_runner):
        """reset --dry-run：get_worker_count 被调，reset_all_workers/kafka_topic_set 不被调。"""
        gtm = MagicMock()
        gtm.get_worker_count.return_value = 3
        with patch("ginkgo.libs.core.threading.GinkgoThreadManager", return_value=gtm), \
             patch("ginkgo.data.drivers.ginkgo_kafka.kafka_topic_set") as topic_set:
            res = cli_runner.invoke(_get_main_app(), ["kafka", "reset", "--dry-run"])
        assert res.exit_code == 0
        gtm.get_worker_count.assert_called_once()
        gtm.reset_all_workers.assert_not_called()  # 关键：未停 worker
        topic_set.assert_not_called()  # 关键：未重建主题
        out = _strip_ansi(res.output)
        assert "Dry-run" in out
        assert "3 worker" in out


# ===========================================================================
# cache clear
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestCacheClearDryRun:
    def test_help_lists_dry_run(self, cli_runner):
        res = cli_runner.invoke(_get_main_app(), ["cache", "clear", "--help"])
        assert res.exit_code == 0
        assert "Preview the scope" in _strip_ansi(res.output)

    def test_dry_run_does_not_clear(self, cli_runner):
        """clear --dry-run：不触达 redis_service.clear_*，打印 Would clear。"""
        redis_svc = MagicMock()
        cont = MagicMock()
        cont.redis_service.return_value = redis_svc
        with patch("ginkgo.data.containers.container", cont):
            res = cli_runner.invoke(_get_main_app(), ["cache", "clear", "--dry-run"])
        assert res.exit_code == 0
        redis_svc.clear_function_cache.assert_not_called()
        redis_svc.clear_all_sync_progress.assert_not_called()
        out = _strip_ansi(res.output)
        assert "Dry-run" in out
        assert "Would clear" in out


# ===========================================================================
# portfolio delete（service 层 dry_run）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestPortfolioDeleteDryRun:
    def _svc(self):
        svc = MagicMock()
        svc.exists.return_value = ServiceResult.success({"exists": True})
        svc.delete.return_value = ServiceResult.success(
            {"portfolio_id": "P1", "mappings_deleted": 2, "parameters_deleted": 5,
             "deployments_would_stop": 1, "dry_run": True, "warnings": []}
        )
        return svc

    def test_help_lists_dry_run(self, cli_runner):
        res = cli_runner.invoke(_get_main_app(), ["portfolio", "delete", "--help"])
        assert res.exit_code == 0
        assert "Preview cascade scope" in _strip_ansi(res.output)

    def test_dry_run_bypasses_confirm_and_passes_true(self, cli_runner):
        """--dry-run 无需 --confirm 即放行，且 delete(dry_run=True)。"""
        svc = self._svc()
        cont = MagicMock()
        cont.portfolio_service.return_value = svc
        with patch("ginkgo.data.containers.container", cont):
            res = cli_runner.invoke(_get_main_app(), ["portfolio", "delete", "P1", "--dry-run"])
        assert res.exit_code == 0
        out = _strip_ansi(res.output)
        assert "Please use --confirm" not in out  # 守卫被旁路
        assert svc.delete.call_args.kwargs.get("dry_run") is True
        assert "2 mapping" in out and "5 parameter" in out and "1 deployment" in out


# ===========================================================================
# engine delete（service 层 dry_run）
# ===========================================================================

@pytest.mark.unit
@pytest.mark.cli
class TestEngineDeleteDryRun:
    def test_help_lists_dry_run(self, cli_runner):
        res = cli_runner.invoke(_get_main_app(), ["engine", "delete", "--help"])
        assert res.exit_code == 0
        assert "Preview cascade scope" in _strip_ansi(res.output)

    def test_dry_run_bypasses_confirm_and_passes_true(self, cli_runner):
        svc = MagicMock()
        svc.delete.return_value = ServiceResult.success(
            {"engine_id": "E1", "mappings_would_delete": 3, "dry_run": True, "warnings": []}
        )
        cont = MagicMock()
        cont.engine_service.return_value = svc
        with patch("ginkgo.data.containers.container", cont):
            res = cli_runner.invoke(_get_main_app(), ["engine", "delete", "E1", "--dry-run"])
        assert res.exit_code == 0
        out = _strip_ansi(res.output)
        assert "Please use --confirm" not in out
        assert svc.delete.call_args.kwargs.get("dry_run") is True
        assert "3 portfolio mapping" in out
