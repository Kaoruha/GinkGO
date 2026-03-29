# 从 node.py 提取的心跳管理模块
# 负责：心跳上报、节点指标更新、Portfolio状态上报、node_id冲突检测、旧数据清理


"""
HeartbeatManager - 心跳管理器

从 ExecutionNode 中提取的心跳相关逻辑，负责：
- 心跳上报循环（每10秒发送一次）
- node_id 冲突检测（防止重复启动）
- 旧心跳数据清理
- 节点性能指标更新到 Redis
- Portfolio 状态更新到 Redis
- ExecutionNode 状态更新到 Redis
"""

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.workers.execution_node.node import ExecutionNode

# 获取日志记录器
logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    心跳管理器

    持有 ExecutionNode 实例引用，通过引用访问节点的状态和队列信息。
    所有方法均通过 node 引用读写节点属性，保持与原始逻辑完全一致。
    """

    def __init__(self, node: "ExecutionNode"):
        """
        初始化心跳管理器

        Args:
            node: ExecutionNode 实例引用
        """
        self.node = node

    def heartbeat_loop(self):
        """
        心跳上报循环（每10秒发送一次）

        心跳数据包含：
        - 心跳时间戳
        - Portfolio 数量
        - 队列使用情况
        - 性能指标
        """
        node = self.node
        while node.is_running:
            try:
                # 发送心跳到 Redis
                self.send_heartbeat()

                # 更新性能指标到 Redis
                self.update_node_metrics()

                # 更新节点状态到 Redis (T068)
                self.update_node_state()

                # 更新所有Portfolio状态到 Redis (T067)
                self.update_all_portfolios_state()

                # 等待下一次心跳
                for _ in range(node.heartbeat_interval):
                    if not node.is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in heartbeat loop for node {node.node_id}: {e}")
                time.sleep(5)  # 出错后等待5秒再重试

        logger.info(f"Heartbeat loop stopped for node {node.node_id}")

    def is_node_id_in_use(self) -> bool:
        """
        检查node_id是否已被其他实例使用

        通过检查Redis中的心跳键和TTL来判断：
        - 心跳键不存在 -> 可用
        - 心跳键存在但TTL < 10秒 -> 残留数据，可用
        - 心跳键存在且TTL >= 10秒 -> 被其他实例使用，不可用

        Returns:
            bool: True表示node_id已被使用，False表示可用
        """
        node = self.node
        try:
            redis_client = node._get_redis_client()
            if not redis_client:
                logger.warning("Failed to get Redis client for node_id check")
                return False  # 无法检查，保守策略：允许启动

            from ginkgo.data.redis_schema import RedisKeyBuilder
            heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node.node_id)
            heartbeat_exists = redis_client.exists(heartbeat_key)

            if not heartbeat_exists:
                # 心跳不存在，node_id可用
                return False

            # 心跳存在，检查TTL
            ttl = redis_client.ttl(heartbeat_key)

            if ttl < 0:
                # 永不过期的键（异常情况），认为被占用
                logger.warning(f"Heartbeat for {node.node_id} has no expiration")
                return True
            elif ttl < 10:
                # TTL < 10秒，很可能是残留数据，允许启动
                logger.info(f"Heartbeat TTL ({ttl}s) is short, treating as stale data")
                return False
            else:
                # TTL >= 10秒，有其他实例在运行
                logger.warning(f"Heartbeat for {node.node_id} exists with TTL {ttl}s (in use)")
                return True

        except Exception as e:
            logger.error(f"Failed to check if node_id is in use: {e}")
            return False  # 检查失败，保守策略：允许启动

    def cleanup_old_heartbeat_data(self):
        """
        清理旧的心跳和指标数据

        在节点启动时调用，确保没有残留的过期数据：
        - 删除旧的 heartbeat:node:{node_id}
        - 删除旧的 node:metrics:{node_id}

        云原生设计：节点重启后完全清空旧状态
        """
        node = self.node
        try:
            # 获取 Redis 客户端
            redis_client = node._get_redis_client()
            if not redis_client:
                logger.error("Failed to get Redis client for cleanup")
                return

            # 构造键名
            from ginkgo.data.redis_schema import RedisKeyBuilder
            heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node.node_id)
            metrics_key = f"node:metrics:{node.node_id}"

            # 删除旧的心跳数据
            deleted_heartbeat = redis_client.delete(heartbeat_key)
            if deleted_heartbeat:
                logger.info(f"Cleaned up old heartbeat data for node {node.node_id}")

            # 删除旧的指标数据
            deleted_metrics = redis_client.delete(metrics_key)
            if deleted_metrics:
                logger.info(f"Cleaned up old metrics data for node {node.node_id}")

            logger.debug(f"Cleanup completed for node {node.node_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup old data for node {node.node_id}: {e}")

    def send_heartbeat(self):
        """
        发送心跳到 Redis

        Redis Key: heartbeat:node:{node_id}
        Value: 当前时间戳
        TTL: 30秒（超过30秒无心跳认为节点离线）
        """
        node = self.node
        try:
            # 获取 Redis 客户端
            redis_client = node._get_redis_client()
            if not redis_client:
                logger.error("Failed to get Redis client for heartbeat")
                return

            # 构造心跳键
            from ginkgo.data.redis_schema import RedisKeyBuilder
            heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node.node_id)

            # 设置心跳值（当前时间戳）
            heartbeat_value = datetime.now().isoformat()

            # 设置键并附带TTL
            redis_client.setex(
                heartbeat_key,
                node.heartbeat_ttl,
                heartbeat_value
            )

            logger.debug(f"Heartbeat sent for node {node.node_id}")

        except Exception as e:
            logger.error(f"Failed to send heartbeat for node {node.node_id}: {e}")

    def update_node_metrics(self):
        """
        更新节点性能指标到 Redis

        Redis Key: node:metrics:{node_id} (Hash)
        Fields:
        - portfolio_count: Portfolio 数量
        - queue_size: 平均队列大小
        - status: 节点状态 (RUNNING/PAUSED/STOPPED)
        - cpu_usage: CPU 使用率（预留）
        - memory_usage: 内存使用（预留）
        """
        node = self.node
        try:
            # 获取 Redis 客户端
            redis_client = node._get_redis_client()
            if not redis_client:
                return

            # 确定节点状态
            if not node.is_running:
                status = "STOPPED"
            elif node.is_paused:
                status = "PAUSED"
            else:
                status = "RUNNING"

            # 收集性能指标
            metrics = {
                "portfolio_count": str(len(node.portfolios)),
                "queue_size": str(self.get_average_queue_size()),
                "status": status,  # 节点状态
                "cpu_usage": "0.0",  # 预留，未来实现
                "memory_usage": "0",  # 预留，未来实现
                "total_events": str(node.total_event_count),
                "backpressure_count": str(node.backpressure_count),
                "dropped_events": str(node.dropped_event_count)
            }

            # 更新到 Redis
            metrics_key = f"node:metrics:{node.node_id}"
            redis_client.hset(metrics_key, mapping=metrics)

            logger.debug(f"Metrics updated for node {node.node_id}: {metrics}")

        except Exception as e:
            logger.error(f"Failed to update metrics for node {node.node_id}: {e}")

    def get_average_queue_size(self) -> int:
        """
        获取所有 Portfolio 的平均队列大小

        Returns:
            int: 平均队列大小
        """
        node = self.node
        try:
            if not node.portfolios:
                return 0

            total_size = 0
            # 使用ExecutionNode持有的队列字典
            for portfolio_id, queue in node.input_queues.items():
                total_size += queue.qsize()

            return total_size // len(node.input_queues)

        except Exception as e:
            logger.error(f"Failed to get average queue size: {e}")
            return 0

    def update_portfolio_state(self, portfolio_id: str):
        """
        更新Portfolio状态到Redis (T067)

        Redis Key: portfolio:{portfolio_id}:state (Hash)
        Fields:
        - status: Portfolio运行状态 (RUNNING/PAUSED/STOPPED/RELOADING/MIGRATING)
        - queue_size: 输入队列大小
        - buffer_size: 缓存消息大小
        - position_count: 持仓数量
        - node_id: 所在节点ID

        Args:
            portfolio_id: Portfolio ID
        """
        node = self.node
        try:
            redis_client = node._get_redis_client()
            if not redis_client:
                return

            # 获取Portfolio实例
            portfolio = node._portfolio_instances.get(portfolio_id)
            if not portfolio:
                logger.warning(f"Portfolio {portfolio_id} not found for state update")
                return

            # 获取队列大小
            queue_size = 0
            if portfolio_id in node.input_queues:
                queue_size = node.input_queues[portfolio_id].qsize()

            # 获取缓存大小（如果有buffer机制）
            buffer_size = 0
            # TODO: 从PortfolioProcessor获取buffer大小

            # 获取持仓数量
            position_count = 0
            if hasattr(portfolio, 'positions'):
                position_count = len(portfolio.positions)

            # 获取Portfolio状态
            status = "UNKNOWN"
            if hasattr(portfolio, 'get_status'):
                status_obj = portfolio.get_status()
                status = str(status_obj).split('.')[-1] if status_obj else "UNKNOWN"

            # 构造状态字典
            state = {
                "status": status,
                "queue_size": str(queue_size),
                "buffer_size": str(buffer_size),
                "position_count": str(position_count),
                "node_id": node.node_id
            }

            # 写入Redis
            state_key = f"portfolio:{portfolio_id}:state"
            redis_client.hset(state_key, mapping=state)

            logger.debug(f"Portfolio state updated: {portfolio_id} -> {state}")

        except Exception as e:
            logger.error(f"Failed to update portfolio state {portfolio_id}: {e}")

    def update_all_portfolios_state(self):
        """
        更新所有Portfolio的状态到Redis (T067)

        在心跳周期中调用，批量更新所有Portfolio状态
        """
        node = self.node
        try:
            for portfolio_id in list(node._portfolio_instances.keys()):
                self.update_portfolio_state(portfolio_id)

        except Exception as e:
            logger.error(f"Failed to update all portfolios state: {e}")

    def update_node_state(self):
        """
        更新ExecutionNode状态到Redis (T068)

        Redis Key: execution_node:{node_id}:info (Hash)
        Fields:
        - status: 节点状态 (RUNNING/PAUSED/STOPPED)
        - portfolio_count: Portfolio数量
        - max_portfolios: 最大Portfolio数量
        - queue_usage_70pct: 队列使用率是否超过70%
        - queue_usage_95pct: 队列使用率是否超过95%
        - uptime_seconds: 运行时长（秒）
        - started_at: 启动时间
        """
        node = self.node
        try:
            redis_client = node._get_redis_client()
            if not redis_client:
                return

            # 确定节点状态
            if not node.is_running:
                status = "STOPPED"
            elif node.is_paused:
                status = "PAUSED"
            else:
                status = "RUNNING"

            # 计算队列使用率
            avg_queue_size = self.get_average_queue_size()
            queue_usage_70pct = avg_queue_size > 700  # 假设队列上限1000
            queue_usage_95pct = avg_queue_size > 950

            # 计算运行时长
            uptime_seconds = 0
            if node.started_at:
                try:
                    from datetime import datetime
                    started = datetime.fromisoformat(node.started_at)
                    uptime_seconds = int((datetime.now() - started).total_seconds())
                except Exception:
                    pass

            # 构造状态字典
            state = {
                "status": status,
                "portfolio_count": str(len(node.portfolios)),
                "max_portfolios": str(node.max_portfolios),
                "queue_usage_70pct": str(queue_usage_70pct),
                "queue_usage_95pct": str(queue_usage_95pct),
                "uptime_seconds": str(uptime_seconds),
                "started_at": node.started_at or ""
            }

            # 写入Redis
            info_key = f"execution_node:{node.node_id}:info"
            redis_client.hset(info_key, mapping=state)

            logger.debug(f"Node state updated: {node.node_id} -> {state}")

        except Exception as e:
            logger.error(f"Failed to update node state {node.node_id}: {e}")
