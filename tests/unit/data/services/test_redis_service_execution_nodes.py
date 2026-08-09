"""redis_service ExecutionNode 相关方法单元测试。

收口 execution_cli 的 Redis 直连（#6300/#6115）后，原 client 层的不变量
下沉至 service 层：
- #5519: scan_execution_node_ids 内部用 scan_iter（非阻塞），不用 keys（阻塞）
- get_node_heartbeat_ttl / get_execution_node_metrics 契约

不依赖真实 Redis：注入 mock redis_crud（与 test_redis_service_find_keys 同模式）。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

project_root = Path(__file__).parent.parent.parent.parent
_src = str(project_root / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.base_service import ServiceResult

# 心跳键格式：heartbeat:node:{id}（RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT="heartbeat:node"）
_HB_PREFIX = "heartbeat:node:"


class TestScanExecutionNodeIds:
    """scan_execution_node_ids：#5519 scan_iter 非阻塞扫描。"""

    def test_uses_scan_iter_not_keys(self):
        """#5519: 内部调 _crud_repo.scan_iter，绝不调 keys（O(N) 阻塞 Redis 单线程）。"""
        mock_crud = MagicMock()
        mock_crud.scan_iter.return_value = []
        svc = RedisService(redis_crud=mock_crud)

        result = svc.scan_execution_node_ids(limit=100)

        mock_crud.scan_iter.assert_called_once()
        mock_crud.keys.assert_not_called()
        assert isinstance(result, ServiceResult)
        assert result.is_success()
        assert result.data == []

    def test_extracts_node_ids_and_truncates_by_limit(self):
        """scan_iter 返回的 heartbeat 键经 extract_id_from_key 提 id，并按 limit 截断。"""
        mock_crud = MagicMock()
        mock_crud.scan_iter.return_value = [
            f"{_HB_PREFIX}node-a",
            f"{_HB_PREFIX}node-b",
            f"{_HB_PREFIX}node-c",
        ]
        svc = RedisService(redis_crud=mock_crud)

        result = svc.scan_execution_node_ids(limit=2)

        assert result.is_success()
        assert result.data == ["node-a", "node-b"]  # 截断到 2

    def test_no_limit_returns_all(self):
        """limit=None 不截断，返回全部扫描到的 node_id。"""
        mock_crud = MagicMock()
        mock_crud.scan_iter.return_value = [
            f"{_HB_PREFIX}node-a",
            f"{_HB_PREFIX}node-b",
        ]
        svc = RedisService(redis_crud=mock_crud)

        result = svc.scan_execution_node_ids()

        assert result.is_success()
        assert result.data == ["node-a", "node-b"]

    def test_count_hint_passed_to_scan(self):
        """limit 作 SCAN COUNT hint 传入 scan_iter（limit=None 时默认 100）。"""
        mock_crud = MagicMock()
        mock_crud.scan_iter.return_value = []
        svc = RedisService(redis_crud=mock_crud)

        svc.scan_execution_node_ids(limit=50)
        assert mock_crud.scan_iter.call_args.kwargs.get("count") == 50

        svc.scan_execution_node_ids()  # limit=None
        assert mock_crud.scan_iter.call_args.kwargs.get("count") == 100

    def test_crud_error_returns_service_error(self):
        """_crud_repo.scan_iter 抛异常时返 ServiceResult.error，不向上传播。"""
        mock_crud = MagicMock()
        mock_crud.scan_iter.side_effect = RuntimeError("redis down")
        svc = RedisService(redis_crud=mock_crud)

        result = svc.scan_execution_node_ids()

        assert not result.is_success()
        assert "redis down" in (result.error or "")


class TestGetExecutionNodeMetrics:
    """get_execution_node_metrics：读 node:metrics:{id} hash（service 已 decode 为 str）。"""

    def test_returns_decoded_metrics_dict(self):
        mock_crud = MagicMock()
        mock_crud.hgetall.return_value = {"status": "RUNNING", "portfolio_count": "3"}
        svc = RedisService(redis_crud=mock_crud)

        result = svc.get_execution_node_metrics("node-a")

        mock_crud.hgetall.assert_called_once_with("node:metrics:node-a")
        assert result.is_success()
        assert result.data == {"status": "RUNNING", "portfolio_count": "3"}

    def test_empty_metrics_still_success(self):
        """无 metrics（空 hash）仍 success，data={}。"""
        mock_crud = MagicMock()
        mock_crud.hgetall.return_value = {}
        svc = RedisService(redis_crud=mock_crud)

        result = svc.get_execution_node_metrics("ghost")

        assert result.is_success()
        assert result.data == {}


class TestGetNodeHeartbeatTtl:
    """get_node_heartbeat_ttl：读心跳 TTL（-2=absent, -1=no-expire, >=0 秒）。"""

    def test_returns_ttl_int(self):
        mock_crud = MagicMock()
        mock_crud.ttl.return_value = 25
        svc = RedisService(redis_crud=mock_crud)

        result = svc.get_node_heartbeat_ttl("node-a")

        assert result.is_success()
        assert result.data == 25

    def test_absent_key_returns_minus_two(self):
        """心跳键不存在 → TTL=-2（节点未运行）。"""
        mock_crud = MagicMock()
        mock_crud.ttl.return_value = -2
        svc = RedisService(redis_crud=mock_crud)

        result = svc.get_node_heartbeat_ttl("ghost")

        assert result.is_success()
        assert result.data == -2

    def test_uses_rediskeybuilder_heartbeat_key(self):
        """ttl 查的是 RedisKeyBuilder.execution_node_heartbeat(id) 构造的键。"""
        mock_crud = MagicMock()
        mock_crud.ttl.return_value = 10
        svc = RedisService(redis_crud=mock_crud)

        svc.get_node_heartbeat_ttl("node-1")

        mock_crud.ttl.assert_called_once_with("heartbeat:node:node-1")


def _make_exists(hb: int, mt: int):
    """key-aware exists side_effect：按 key 名区分 heartbeat/metrics，不依赖调用顺序。

    service 构造的键：heartbeat:node:{id}（含 "heartbeat"）与 node:metrics:{id}（不含），
    以 "heartbeat" 子串区分。与原 client 层 _make_exists 同逻辑（逻辑下沉后接口不变）。
    """
    def fake(key):
        k = key.decode() if isinstance(key, bytes) else key
        return hb if "heartbeat" in k else mt
    return fake


class TestIsExecutionNodeActive:
    """is_execution_node_active：#4945 判活（原 execution_cli._is_node_active 下沉）。

    阈值 5s：TTL≥5 活跃，0≤TTL<5 stale（可清理），TTL<0 永不过期保守判活，
    heartbeat 不存在→不活跃。
    """

    def test_fresh_heartbeat_is_active(self):
        """TTL ≥ 阈值 → 活跃（运行中，不应清理）。"""
        mock_crud = MagicMock()
        mock_crud.exists.return_value = 1
        mock_crud.ttl.return_value = 20
        svc = RedisService(redis_crud=mock_crud)

        result = svc.is_execution_node_active("node-a")

        assert result.is_success()
        assert result.data is True

    def test_stale_heartbeat_is_not_active(self):
        """TTL < 阈值（即将过期）→ 不活跃（可清理）。"""
        mock_crud = MagicMock()
        mock_crud.exists.return_value = 1
        mock_crud.ttl.return_value = 3  # < 5s 阈值
        svc = RedisService(redis_crud=mock_crud)

        result = svc.is_execution_node_active("node-a")

        assert result.is_success()
        assert result.data is False

    def test_no_heartbeat_is_not_active(self):
        """heartbeat 不存在 → 不活跃（短路，不查 TTL）。"""
        mock_crud = MagicMock()
        mock_crud.exists.return_value = 0
        svc = RedisService(redis_crud=mock_crud)

        result = svc.is_execution_node_active("node-a")

        assert result.is_success()
        assert result.data is False
        mock_crud.ttl.assert_not_called()  # 短路

    def test_never_expire_heartbeat_is_active(self):
        """TTL=-1（key 存在但永不过期，异常）→ 保守判活（#4945 review）。"""
        mock_crud = MagicMock()
        mock_crud.exists.return_value = 1
        mock_crud.ttl.return_value = -1
        svc = RedisService(redis_crud=mock_crud)

        result = svc.is_execution_node_active("node-a")

        assert result.is_success()
        assert result.data is True


class TestCleanupExecutionNode:
    """cleanup_execution_node：#5980 删除 + #4945 活跃守卫（原 _cleanup_node 下沉）。

    返回 data = {skipped_active, heartbeat_deleted, metrics_deleted}：
    - 活跃节点（fresh heartbeat）默认拒绝（skipped_active=True），force=True 跳过守卫。
    - stale/无数据节点按 key 存在性删除；dry_run=True 探测仍跑、delete 不触发。
    """

    def test_stale_node_deletes_heartbeat_and_metrics(self):
        """stale 节点（heartbeat 存在但 TTL 很小）→ 删 heartbeat + metrics。"""
        mock_crud = MagicMock()
        mock_crud.exists.side_effect = _make_exists(hb=1, mt=1)
        mock_crud.ttl.return_value = 0  # stale
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node-a")

        assert result.is_success()
        d = result.data
        assert d["skipped_active"] is False
        assert d["heartbeat_deleted"] is True and d["metrics_deleted"] is True
        assert mock_crud.delete.call_count == 2

    def test_no_data_returns_false_and_skips_delete(self):
        """无任何数据 → 不删。"""
        mock_crud = MagicMock()
        mock_crud.exists.side_effect = _make_exists(hb=0, mt=0)
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node-x")

        assert result.is_success()
        d = result.data
        assert d["skipped_active"] is False
        assert d["heartbeat_deleted"] is False and d["metrics_deleted"] is False
        mock_crud.delete.assert_not_called()

    def test_stale_node_heartbeat_only_deletes_heartbeat(self):
        """stale 节点且只有 heartbeat → 只删 heartbeat。"""
        mock_crud = MagicMock()
        mock_crud.exists.side_effect = _make_exists(hb=1, mt=0)
        mock_crud.ttl.return_value = 0  # stale
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node-hb")

        assert result.is_success()
        d = result.data
        assert d["heartbeat_deleted"] is True and d["metrics_deleted"] is False
        assert mock_crud.delete.call_count == 1

    def test_active_node_rejected_without_force(self):
        """#4945: 活跃节点（fresh heartbeat）默认拒绝清理，不删任何 key。"""
        mock_crud = MagicMock()
        mock_crud.exists.side_effect = _make_exists(hb=1, mt=1)
        mock_crud.ttl.return_value = 20  # 活跃（≥ 阈值 5）
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node-a")

        assert result.is_success()
        d = result.data
        assert d["skipped_active"] is True
        assert d["heartbeat_deleted"] is False and d["metrics_deleted"] is False
        mock_crud.delete.assert_not_called()

    def test_active_node_force_overrides_guard(self):
        """#4945: force=True 强制清理活跃节点（跳过守卫）。"""
        mock_crud = MagicMock()
        mock_crud.exists.side_effect = _make_exists(hb=1, mt=1)
        mock_crud.ttl.return_value = 20  # 活跃
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node-a", force=True)

        assert result.is_success()
        d = result.data
        assert d["skipped_active"] is False
        assert d["heartbeat_deleted"] is True and d["metrics_deleted"] is True
        assert mock_crud.delete.call_count == 2

    def test_never_expire_node_rejected_without_force(self):
        """#4945 review: TTL=-1（永不过期异常 heartbeat）默认拒绝，保守口径一致。"""
        mock_crud = MagicMock()
        mock_crud.exists.side_effect = _make_exists(hb=1, mt=1)
        mock_crud.ttl.return_value = -1  # 永不过期（异常）
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node-a")

        assert result.is_success()
        d = result.data
        assert d["skipped_active"] is True
        mock_crud.delete.assert_not_called()

    def test_dry_run_does_not_delete(self):
        """dry_run=True：exists 探测仍跑，delete 不被调用（#5980 预览）。"""
        mock_crud = MagicMock()
        mock_crud.exists.return_value = 1  # key 存在
        mock_crud.ttl.return_value = 2  # < 阈值 5 → stale，放行清理
        svc = RedisService(redis_crud=mock_crud)

        result = svc.cleanup_execution_node("node_1", force=False, dry_run=True)

        assert result.is_success()
        d = result.data
        assert d["skipped_active"] is False
        assert d["heartbeat_deleted"] is True and d["metrics_deleted"] is True
        mock_crud.exists.assert_called()  # 探测仍发生
        mock_crud.delete.assert_not_called()  # 关键：dry-run 不删

    def test_real_run_deletes(self):
        """对照：dry_run=False 仍调用 delete（heartbeat + metrics）。"""
        mock_crud = MagicMock()
        mock_crud.exists.return_value = 1
        mock_crud.ttl.return_value = 2
        svc = RedisService(redis_crud=mock_crud)

        svc.cleanup_execution_node("node_1", force=False, dry_run=False)

        assert mock_crud.delete.call_count == 2
