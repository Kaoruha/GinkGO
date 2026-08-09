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
