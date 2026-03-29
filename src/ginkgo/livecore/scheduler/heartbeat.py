"""
心跳检测模块

负责从 Redis 扫描 ExecutionNode 心跳键，返回健康节点列表及其性能指标。
纯查询逻辑，无副作用。
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class HeartbeatChecker:
    """ExecutionNode 心跳检测器"""

    NODE_METRICS_PREFIX = "node:metrics:"

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def get_healthy_nodes(self) -> List[Dict]:
        """
        获取所有健康的 ExecutionNode（有心跳）

        Returns:
            List[Dict]: 健康的 Node 列表，每个包含 node_id 和 metrics
        """
        try:
            from ginkgo.data.redis_schema import RedisKeyPattern, extract_id_from_key, RedisKeyPrefix
            # 扫描所有心跳键
            heartbeat_keys = self.redis_client.keys(RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL)

            healthy_nodes = []
            for key in heartbeat_keys:
                # 提取 node_id
                node_id = extract_id_from_key(key.decode('utf-8'), f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:")

                # 获取 Node 性能指标
                metrics = self.get_node_metrics(node_id)

                healthy_nodes.append({
                    'node_id': node_id,
                    'metrics': metrics
                })

            logger.debug(f"Found {len(healthy_nodes)} healthy nodes")
            return healthy_nodes

        except Exception as e:
            logger.error(f"Failed to get healthy nodes: {e}")
            return []

    def get_node_metrics(self, node_id: str) -> Dict:
        """
        获取 Node 性能指标

        Args:
            node_id: ExecutionNode ID

        Returns:
            Dict: 性能指标 {portfolio_count, queue_size, cpu_usage}
        """
        try:
            key = f"{self.NODE_METRICS_PREFIX}{node_id}"
            metrics = self.redis_client.hgetall(key)

            return {
                'portfolio_count': int(metrics.get(b'portfolio_count', 0)),
                'queue_size': int(metrics.get(b'queue_size', 0)),
                'cpu_usage': float(metrics.get(b'cpu_usage', 0.0))
            }
        except Exception as e:
            logger.error(f"Failed to get metrics for node {node_id}: {e}")
            return {'portfolio_count': 0, 'queue_size': 0, 'cpu_usage': 0.0}
