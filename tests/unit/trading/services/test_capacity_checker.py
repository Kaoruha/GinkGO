"""#4800: 集群容量预检 _make_capacity_checker 数据流测试。

review #6568 指出: 原 checker 复用 get_execution_node_status() 读心跳键 active_portfolios，
但执行节点心跳键只存裸 ISO 时间戳（无 active_portfolios 字段），致 used_slots 恒 0、
满载集群也放行，#4800「deploy 假成功」原场景原样复现。

本测试用真实 _make_capacity_checker + fake redis 验证数据流真正接通——读 node:metrics
Hash 的 portfolio_count（与 LoadBalancer.assign_portfolios 同源，load_balancer.py:73,80,82），
而非 mock 掉 checker callable。
"""
from unittest import mock

from ginkgo.trading.containers import _make_capacity_checker


class _FakeRedis:
    """模拟 redis-py 客户端，仅实现 HeartbeatChecker 用到的 keys()/hgetall()。

    Args:
        nodes: {node_id: portfolio_count} 模拟集群拓扑
    """

    def __init__(self, nodes):
        self._nodes = nodes

    def keys(self, pattern):
        # pattern = RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL = "heartbeat:node:*"
        return [f"heartbeat:node:{nid}".encode() for nid in self._nodes]

    def hgetall(self, key):
        # key = "node:metrics:{node_id}" (HeartbeatChecker.NODE_METRICS_PREFIX)
        if not isinstance(key, str) or not key.startswith("node:metrics:"):
            return {}
        nid = key.split("node:metrics:", 1)[1]
        count = self._nodes.get(nid, 0)
        return {
            b"portfolio_count": str(count).encode(),
            b"queue_size": b"0",
            b"cpu_usage": b"0.0",
            b"status": b"RUNNING",
        }


def _run_checker_with_fake_redis(nodes):
    """构造真实 _make_capacity_checker，注入 fake redis_service，返回 capacity dict。"""
    fake_svc = mock.MagicMock()
    fake_svc.redis = _FakeRedis(nodes)
    with mock.patch("ginkgo.data.containers.container") as fake_container:
        fake_container.redis_service.return_value = fake_svc
        checker = _make_capacity_checker()
        return checker()


class TestCapacityCheckerDataSource:
    """数据流契约: 读 node:metrics Hash 的 portfolio_count（与 LoadBalancer 同源）。"""

    def test_zero_available_when_single_node_at_max_capacity(self):
        """满载: 1 节点 portfolio_count=5（=MAX_PORTFOLIOS_PER_NODE）→ available_slots=0。

        原 bug: 读心跳键 active_portfolios 恒 0 → available=5-0=5 误放行（#4800 假成功场景）。
        修复后: 读 node:metrics portfolio_count=5 → available=5-5=0 正确触发早失败。
        """
        result = _run_checker_with_fake_redis({"node_1": 5})

        assert result["healthy_nodes"] == 1
        assert result["used_slots"] == 5
        assert result["available_slots"] == 0

    def test_positive_available_when_nodes_have_room(self):
        """回归: 多节点混合负载，有空位时 available 正确聚合。

        2 节点 (MAX=5): n1=4, n2=2 → total=10, used=6, available=4。
        与 LoadBalancer 逐节点判断 (portfolio_count < max) 同语义: 每节点都有空位。
        """
        result = _run_checker_with_fake_redis({"n1": 4, "n2": 2})

        assert result["healthy_nodes"] == 2
        assert result["total_slots"] == 10
        assert result["used_slots"] == 6
        assert result["available_slots"] == 4

    def test_fail_open_when_redis_unavailable(self):
        """容错: Redis 不可用时 fail-open (available_slots=1)，不因基础设施故障阻塞 deploy。

        真实场景: Redis 网络抖动/重启期间，容量未知 → 放行 deploy（宁可乐观分配，
        让 worker 端 LoadBalancer 再判满载）而非阻塞业务。注意: 此时 healthy_nodes=0
        反映"无法探活"，调用方不应据此判定集群健康。
        """
        with mock.patch("ginkgo.data.containers.container") as fake_container:
            fake_container.redis_service.side_effect = Exception("redis connection refused")
            checker = _make_capacity_checker()
            result = checker()

        assert result["healthy_nodes"] == 0
        assert result["available_slots"] == 1  # fail-open
