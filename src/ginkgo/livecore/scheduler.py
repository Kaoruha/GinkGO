# Upstream: Scheduler（无状态调度器，从Redis读取状态）
# Downstream: ExecutionNode（接收调度指令，更新Portfolio分配）
# Role: Portfolio动态调度器，负责负载均衡、故障检测和优雅迁移


"""
Scheduler 调度器（无状态设计）

Scheduler 是 LiveCore 的调度组件，负责：
1. 定期执行调度算法（每30秒）
2. ExecutionNode 心跳检测（每10秒上报，TTL=30秒）
3. Portfolio 动态分配到 ExecutionNode（负载均衡）
4. ExecutionNode 故障时自动迁移 Portfolio
5. 发布调度更新到 Kafka schedule.updates topic
6. 接收并处理来自 Kafka 的命令（立即调度、重新计算等）

设计要点：
- 无状态设计：所有调度数据存储在 Redis
- 单线程架构：避免线程嵌套，调度循环和命令处理在同一个线程
- 水平扩展：支持多个 Scheduler 实例（通过 Redis 分布式锁）
- 故障恢复：ExecutionNode 离线时自动迁移 Portfolio（< 60秒）
- 优雅重启：配置更新时触发 Portfolio 优雅重启（< 30秒）
- 命令响应：支持通过 Kafka 接收主动调度命令（非阻塞处理）

Redis 数据结构：
- heartbeat:node:{node_id}           - ExecutionNode 心跳（String, TTL=30秒）
- schedule:plan                       - 当前调度计划（Hash, key=portfolio_id, value=node_id）
- node:{node_id}:portfolios           - Node 上的 Portfolio 列表（Set）
- node:{node_id}:metrics              - Node 性能指标（Hash: portfolio_count, queue_size, cpu_usage）
- portfolio:{portfolio_id}:status     - Portfolio 状态（String: RUNNING/STOPPING/RELOADING）

Kafka Topics:
- schedule.updates                    - 调度更新事件（ControlCommand）
- scheduler.commands                  - 调度器命令（立即调度、重新计算、迁移等）

命令格式（scheduler.commands）:
{
  "command": "recalculate|schedule|migrate|pause|resume|status",
  "timestamp": "2026-01-06T12:00:00",
  "params": {...}
}

线程模型：
- 单线程：调度循环 + 命令处理在同一个线程
- 避免线程嵌套：不启动子线程处理命令
- 命令检查时机：每次调度循环后 + 每5秒检查一次

状态管理：
- RUNNING: 正常运行，执行调度循环和处理命令
- PAUSED: 暂停调度，只处理命令（不执行_schedule_loop）
- STOPPED: 停止运行，退出主循环

使用方式：
    from ginkgo.livecore.scheduler import Scheduler

    # 方式1：使用默认配置（自动创建 Redis 和 Kafka 连接）
    scheduler = Scheduler()
    scheduler.start()

    # 方式2：自定义配置
    scheduler = Scheduler(
        redis_client=custom_redis_client,
        kafka_producer=custom_kafka_producer,
        schedule_interval=30  # 30秒调度一次
    )
    scheduler.start()
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

try:
    from redis import Redis
except ImportError:
    Redis = None

try:
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
except ImportError:
    GinkgoProducer = None

from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs.utils.common import time_logger, retry


# 获取日志记录器
logger = logging.getLogger(__name__)


class Scheduler(threading.Thread):
    """
    Scheduler 调度器（无状态设计）

    职责：
    - 定期执行调度算法（负载均衡）
    - 检查 ExecutionNode 心跳并检测离线
    - 分配 Portfolio 到健康的 ExecutionNode
    - 发布调度更新到 Kafka

    设计模式：
    - 无状态设计：所有状态存储在 Redis
    - 定期调度：每 30 秒执行一次调度算法
    - 心跳检测：检查 Redis 中的心跳键（TTL=30秒）
    """

    # Redis 键前缀
    HEARTBEAT_PREFIX = "heartbeat:node:"
    SCHEDULE_PLAN_KEY = "schedule:plan"
    NODE_PORTFOLIOS_PREFIX = "node:"
    NODE_METRICS_PREFIX = "node:metrics:"
    PORTFOLIO_STATUS_PREFIX = "portfolio:"

    # 默认配置
    DEFAULT_SCHEDULE_INTERVAL = 30  # 30秒调度一次
    STATUS_REPORT_INTERVAL = 1800  # 30分钟汇报一次状态（1800秒）
    HEARTBEAT_TTL = 30  # 心跳 TTL 30秒
    MAX_PORTFOLIOS_PER_NODE = 5  # 每个 Node 最多运行 5 个 Portfolio
    COMMAND_TOPIC = "scheduler.commands"  # 命令主题

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        kafka_producer: Optional[GinkgoProducer] = None,
        schedule_interval: int = DEFAULT_SCHEDULE_INTERVAL,
        status_report_interval: int = STATUS_REPORT_INTERVAL,
        node_id: str = "scheduler_1"
    ):
        """
        初始化 Scheduler

        Args:
            redis_client: Redis 客户端（用于状态存储），如果为None则自动创建
            kafka_producer: Kafka 生产者（用于发布调度更新），如果为None则自动创建
            schedule_interval: 调度间隔（秒），默认 30 秒
            status_report_interval: 状态汇报间隔（秒），默认 1800 秒（30分钟）
            node_id: Scheduler 节点 ID（用于日志标识）
        """
        super().__init__()

        # 如果没有传入 Redis 客户端，自动创建
        if redis_client is None:
            from ginkgo.data.crud import RedisCRUD
            redis_crud = RedisCRUD()
            redis_client = redis_crud.redis

        # 如果没有传入 Kafka 生产者，自动创建
        if kafka_producer is None:
            kafka_producer = GinkgoProducer()

        self.redis_client = redis_client
        self.kafka_producer = kafka_producer
        self.schedule_interval = schedule_interval
        self.status_report_interval = status_report_interval
        self.node_id = node_id

        # 状态标志
        self.is_running = False
        self.should_stop = False
        self.is_paused = False  # 暂停标志
        self.last_status_report_time = 0  # 上次状态汇报时间

        # 创建命令消费者（在主线程中处理命令，避免线程嵌套）
        try:
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer
            self.command_consumer = GinkgoConsumer(
                topic=self.COMMAND_TOPIC,
                group_id=f"scheduler_{self.node_id}"
            )
            logger.debug(f"Command consumer created for {self.COMMAND_TOPIC}")
        except Exception as e:
            logger.warning(f"Failed to create command consumer: {e}")
            self.command_consumer = None

        logger.info(f"Scheduler {self.node_id} initialized (interval={schedule_interval}s, status_report={status_report_interval}s)")

    def run(self):
        """
        Scheduler 主循环

        定期执行调度算法：
        1. 检查 ExecutionNode 心跳
        2. 检测离线 Node
        3. 重新分配离线 Node 的 Portfolio
        4. 发布调度更新到 Kafka
        5. 检查并处理主动调度命令（非阻塞）

        设计要点：
        - 单线程设计：调度循环和命令处理在同一个线程
        - 避免线程嵌套：不启动子线程处理命令
        - 非阻塞命令检查：在每次调度循环后检查命令
        - 支持暂停：PAUSED 状态下不执行调度，但仍处理命令
        """
        self.is_running = True
        logger.info(f"Scheduler {self.node_id} started")

        # 发送启动通知
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                f"调度器 {self.node_id} 已启动",
                level="INFO",
                module="Scheduler",
                details={
                    "节点ID": self.node_id,
                    "调度间隔": f"{self.schedule_interval}秒"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to send startup notification: {e}")

        while not self.should_stop:
            try:
                # 1. 检查并处理命令（非阻塞）
                self._check_commands()

                # 2. 如果未暂停，执行调度算法
                if not self.is_paused:
                    self._schedule_loop()
                else:
                    logger.debug(f"Scheduler {self.node_id} is paused, skipping schedule loop")

                # 3. 检查是否需要发送状态汇报（每30分钟）
                current_time = time.time()
                if current_time - self.last_status_report_time >= self.status_report_interval:
                    self._send_status_report()
                    self.last_status_report_time = current_time

                # 4. 等待下一次调度（可中断）
                for second in range(self.schedule_interval):
                    if self.should_stop:
                        break
                    time.sleep(1)

                    # 每5秒检查一次命令（提高响应速度）
                    if second > 0 and second % 5 == 0:
                        self._check_commands()

            except Exception as e:
                logger.error(f"Scheduler {self.node_id} error: {e}")
                time.sleep(5)  # 出错后等待 5 秒再重试

        self.is_running = False
        logger.info(f"Scheduler {self.node_id} stopped")

    def _schedule_loop(self):
        """
        执行一次完整的调度循环

        步骤：
        1. 获取所有 ExecutionNode 状态
        2. 检查心跳，过滤离线 Node
        3. 发现新的 live portfolio（从数据库）
        4. 检测离线 Node 的 Portfolio（孤儿）
        5. 执行负载均衡算法
        6. 发布调度更新
        """
        # 1. 获取健康的 ExecutionNode
        healthy_nodes = self._get_healthy_nodes()

        # 2. 获取当前调度计划
        current_plan = self._get_current_schedule_plan()

        # 3. 发现新的 live portfolio（从数据库）
        new_portfolios = self._discover_new_portfolios(current_plan)

        # 3.5. 清理已删除的 portfolio（调度计划有，但数据库不存在的）
        deleted_portfolios = self._detect_deleted_portfolios(current_plan)
        if deleted_portfolios:
            logger.warning(f"Deleted portfolios detected: {[p[:8] for p in deleted_portfolios]}")

            # 发送删除通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"清理已删除Portfolio - {len(deleted_portfolios)}个Portfolio已从调度计划移除",
                    level="INFO",
                    module="Scheduler",
                    details={
                        "已删除Portfolio数": len(deleted_portfolios),
                        "Portfolio IDs": ", ".join([p[:8] for p in deleted_portfolios])
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to send deleted portfolios notification: {e}")

            # 从当前计划中移除已删除的portfolio
            for portfolio_id in deleted_portfolios:
                if portfolio_id in current_plan:
                    del current_plan[portfolio_id]

            # 立即更新Redis（移除已删除的portfolio）
            self.redis_client.delete(self.SCHEDULE_PLAN_KEY)
            if current_plan:
                self.redis_client.hset(self.SCHEDULE_PLAN_KEY, mapping=current_plan)

            logger.info(f"Removed {len(deleted_portfolios)} deleted portfolios from schedule plan and updated Redis")

        # 4. 检测离线 Node 的 Portfolio
        orphaned_portfolios = self._detect_orphaned_portfolios(healthy_nodes)

        # ========== 调度信息打印 ==========
        logger.info("")
        logger.info("="*70)
        logger.info(f"Scheduler Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)

        # [DEBUG] 打印当前调度计划详情
        logger.info(f"[DEBUG] Current schedule plan ({len(current_plan)} portfolios):")
        for portfolio_id, node_id in current_plan.items():
            status_icon = "❌" if node_id == "__ORPHANED__" else "✅"
            logger.info(f"  {status_icon} {portfolio_id[:8]}... → {node_id}")

        logger.info("-"*70)

        # 打印可调度节点
        if healthy_nodes:
            logger.info(f"Available schedulable nodes: {len(healthy_nodes)}")
            for node in healthy_nodes:
                node_id = node['node_id']
                count = node['metrics']['portfolio_count']
                logger.info(f"  - {node_id}: {count}/{self.MAX_PORTFOLIOS_PER_NODE} portfolios")
        else:
            logger.warning("No available schedulable nodes (all nodes offline or no nodes registered)")

        # 打印当前所有portfolio
        all_portfolios = set(current_plan.keys()) | set(new_portfolios)
        if all_portfolios:
            logger.info(f"Total portfolios: {len(all_portfolios)}")
        else:
            logger.info("No portfolios found")

        # 打印需要调整的portfolio
        portfolios_to_assign = list(new_portfolios) + orphaned_portfolios
        if portfolios_to_assign:
            logger.info(f"Portfolios to assign: {len(portfolios_to_assign)}")
            logger.info(f"  - New: {len(new_portfolios)}")
            if new_portfolios:
                for p in new_portfolios:
                    logger.info(f"      - {p[:8]}... (from database)")
            logger.info(f"  - Orphaned (node offline): {len(orphaned_portfolios)}")
            if orphaned_portfolios:
                for p in orphaned_portfolios:
                    old_node = current_plan.get(p, "unknown")
                    logger.info(f"      - {p[:8]}... (was on {old_node})")
        else:
            logger.info("No portfolio assignments needed")
            logger.info(f"[DEBUG] new_portfolios={len(new_portfolios)}, orphaned_portfolios={len(orphaned_portfolios)}")

        logger.info("-"*70)

        # 5. 重新分配 Portfolio（负载均衡）
        new_plan = self._assign_portfolios(
            healthy_nodes=healthy_nodes,
            current_plan=current_plan,
            orphaned_portfolios=portfolios_to_assign
        )

        # 打印调度计划变化
        if new_plan != current_plan:
            changes = self._get_plan_changes(current_plan, new_plan)
            logger.info(f"Schedule plan changes: {len(changes)}")
            for portfolio_id, (old_node, new_node) in changes.items():
                if old_node == "__ORPHANED__":
                    if new_node == "__ORPHANED__":
                        # ORPHANED → ORPHANED (理论上不应该出现)
                        logger.info(f"  ? {portfolio_id[:8]}...: {old_node} → {new_node} (UNKNOWN)")
                    else:
                        # ORPHANED → node (孤儿重新分配 OR 新portfolio)
                        logger.info(f"  + {portfolio_id[:8]}... → {new_node} (REASSIGNED)")
                elif new_node == "__ORPHANED__":
                    # node → ORPHANED (节点离线，变为孤儿)
                    logger.info(f"  - {portfolio_id[:8]}... ← {old_node} (ORPHANED)")
                else:
                    # node → node (迁移)
                    logger.info(f"  ~ {portfolio_id[:8]}...: {old_node} → {new_node} (MIGRATED)")
        else:
            logger.info("No schedule plan changes")

        logger.info("="*70)
        logger.info("")

        # 6. 发布调度更新
        if new_plan != current_plan:
            self._publish_schedule_update(current_plan, new_plan)

    def stop(self):
        """
        停止 Scheduler - 优雅关闭流程

        核心策略：
        1. 设置停止标志（通知主循环退出）
        2. 清理 Redis 心跳和状态数据
        3. 关闭 Kafka Consumer 和 Producer
        4. 等待主线程结束
        """
        logger.info(f"")
        logger.info(f"═══════════════════════════════════════════════════════")
        logger.info(f"🛑 Stopping Scheduler {self.node_id}")
        logger.info(f"═══════════════════════════════════════════════════════")

        # 0. 设置停止标志（通知主循环退出）
        logger.info(f"[Step 1] Setting stop flag...")
        self.should_stop = True
        self.is_running = False
        logger.info(f"  ✅ Stop flag set")

        # 1. 清理 Redis 数据（重要：让 ExecutionNode 知道 Scheduler 离线）
        logger.info(f"[Step 2] Cleaning up Redis data...")
        self._cleanup_redis_data()

        # 2. 关闭 Kafka Consumer（停止接收命令）
        logger.info(f"[Step 3] Closing Kafka Consumer...")
        if self.command_consumer:
            try:
                self.command_consumer.close()
                logger.info(f"  ✅ Command consumer closed")
            except Exception as e:
                logger.error(f"  ✗ Error closing command consumer: {e}")
        else:
            logger.info(f"  ℹ️  No command consumer to close")

        # 3. 关闭 Kafka Producer（停止发送调度更新）
        logger.info(f"[Step 4] Closing Kafka Producer...")
        if self.kafka_producer:
            try:
                self.kafka_producer.close()
                logger.info(f"  ✅ Kafka producer closed")
            except Exception as e:
                logger.error(f"  ✗ Error closing Kafka producer: {e}")
        else:
            logger.info(f"  ℹ️  No Kafka producer to close")

        logger.info(f"")
        logger.info(f"═══════════════════════════════════════════════════════")
        logger.info(f"✅ Scheduler {self.node_id} stopped gracefully")
        logger.info(f"═══════════════════════════════════════════════════════")
        logger.info(f"")

    def _cleanup_redis_data(self):
        """
        清理 Redis 中的 Scheduler 相关数据

        清理内容：
        1. Scheduler 心跳数据（虽然 Scheduler 没有心跳，但清理以防将来添加）
        2. Scheduler 状态数据
        """
        try:
            deleted_keys = []

            # 清理 Scheduler 心跳（预留，当前没有心跳机制）
            heartbeat_key = f"heartbeat:scheduler:{self.node_id}"
            try:
                if self.redis_client.exists(heartbeat_key):
                    self.redis_client.delete(heartbeat_key)
                    deleted_keys.append(heartbeat_key)
                    logger.info(f"  ✅ Deleted scheduler heartbeat: {heartbeat_key}")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not delete heartbeat key: {e}")

            # 清理 Scheduler 状态（预留，当前没有状态键）
            state_key = f"scheduler:state:{self.node_id}"
            try:
                if self.redis_client.exists(state_key):
                    self.redis_client.delete(state_key)
                    deleted_keys.append(state_key)
                    logger.info(f"  ✅ Deleted scheduler state: {state_key}")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not delete state key: {e}")

            # 重要说明：
            # - schedule:plan 不清理（这是全局调度计划，其他 Scheduler 可能需要）
            # - heartbeat:node:* 不清理（这是 ExecutionNode 的心跳，不是 Scheduler 的）
            # - node:*:portfolios 不清理（这是 ExecutionNode 的状态，不是 Scheduler 的）

            if deleted_keys:
                logger.info(f"  ✅ Total keys deleted: {len(deleted_keys)}")
            else:
                logger.info(f"  ℹ️  No scheduler-specific keys to delete")

        except Exception as e:
            logger.error(f"  ✗ Error cleaning up Redis data: {e}")

    # ========================================================================
    # 心跳检测
    # ========================================================================

    def _get_healthy_nodes(self) -> List[Dict]:
        """
        获取所有健康的 ExecutionNode（有心跳）

        Returns:
            List[Dict]: 健康的 Node 列表，每个包含 node_id 和 metrics
        """
        try:
            # 扫描所有心跳键
            heartbeat_keys = self.redis_client.keys(f"{self.HEARTBEAT_PREFIX}*")

            healthy_nodes = []
            for key in heartbeat_keys:
                # 提取 node_id
                node_id = key.decode('utf-8').replace(self.HEARTBEAT_PREFIX, "")

                # 获取 Node 性能指标
                metrics = self._get_node_metrics(node_id)

                healthy_nodes.append({
                    'node_id': node_id,
                    'metrics': metrics
                })

            logger.debug(f"Found {len(healthy_nodes)} healthy nodes")
            return healthy_nodes

        except Exception as e:
            logger.error(f"Failed to get healthy nodes: {e}")
            return []

    def _get_node_metrics(self, node_id: str) -> Dict:
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

    # ========================================================================
    # 调度计划管理
    # ========================================================================

    def _get_current_schedule_plan(self) -> Dict[str, str]:
        """
        获取当前调度计划

        Returns:
            Dict: {portfolio_id: node_id}
        """
        try:
            plan = self.redis_client.hgetall(self.SCHEDULE_PLAN_KEY)

            # 转换 bytes 到 str
            return {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in plan.items()
            }
        except Exception as e:
            logger.error(f"Failed to get current schedule plan: {e}")
            return {}

    def _detect_orphaned_portfolios(self, healthy_nodes: List[Dict]) -> List[str]:
        """
        检测离线 Node 的 Portfolio（孤儿 Portfolio）

        Args:
            healthy_nodes: 健康的 Node 列表

        Returns:
            List[str]: 需要重新分配的 portfolio_id 列表
        """
        try:
            # 获取当前调度计划
            current_plan = self._get_current_schedule_plan()

            # 健康的 Node ID 集合
            healthy_node_ids = {n['node_id'] for n in healthy_nodes}

            # 找出分配给离线 Node 的 Portfolio
            orphaned = []
            for portfolio_id, node_id in current_plan.items():
                if node_id not in healthy_node_ids:
                    orphaned.append(portfolio_id)

            # 只在发现孤儿portfolio时打印
            if orphaned:
                logger.warning(f"Orphan portfolios (node offline): {[p[:8] for p in orphaned]}")

                # 发送节点下线警告通知
                try:
                    from ginkgo.notifier.core.notification_service import notify

                    # 找出离线的节点
                    offline_nodes = set()
                    for portfolio_id in orphaned:
                        old_node = current_plan.get(portfolio_id)
                        if old_node and old_node != "__ORPHANED__":
                            offline_nodes.add(old_node)

                    notify(
                        f"检测到节点下线 - {len(offline_nodes)}个节点离线, {len(orphaned)}个Portfolio需要重新分配",
                        level="WARN",
                        module="Scheduler",
                        details={
                            "离线节点数": len(offline_nodes),
                            "离线节点": ", ".join(list(offline_nodes)[:5]),
                            "受影响Portfolio数": len(orphaned),
                            "需要重新分配": "是"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send node offline warning: {e}")

            return orphaned

        except Exception as e:
            logger.error(f"Failed to detect orphaned portfolios: {e}")
            return []

    def _detect_deleted_portfolios(self, current_plan: Dict[str, str]) -> List[str]:
        """
        检测已删除的 Portfolio（调度计划中有，但数据库不存在的）

        Args:
            current_plan: 当前调度计划 {portfolio_id: node_id}

        Returns:
            List[str]: 需要从调度计划中移除的 portfolio_id 列表
        """
        try:
            # 获取数据库中所有 live portfolio
            all_portfolios = self._get_all_portfolios()
            existing_portfolio_ids = {p.uuid for p in all_portfolios}

            # 找出调度计划中有，但数据库中不存在的 portfolio
            deleted = []
            for portfolio_id in current_plan.keys():
                if portfolio_id not in existing_portfolio_ids:
                    deleted.append(portfolio_id)

            # 只在发现已删除portfolio时打印
            if deleted:
                logger.warning(f"Deleted portfolios (removed from database): {[p[:8] for p in deleted]}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to detect deleted portfolios: {e}")
            return []

    # ========================================================================
    # 负载均衡算法
    # ========================================================================

    def _assign_portfolios(
        self,
        healthy_nodes: List[Dict],
        current_plan: Dict[str, str],
        orphaned_portfolios: List[str]
    ) -> Dict[str, str]:
        """
        负载均衡算法：分配 Portfolio 到 ExecutionNode

        策略：
        1. 保留当前已有的分配（除非 Node 离线）
        2. 优先分配到负载最低的 Node
        3. 每个 Node 最多运行 MAX_PORTFOLIOS_PER_NODE 个 Portfolio
        4. 如果没有可用 Node，返回空分配（等待下次调度）

        Args:
            healthy_nodes: 健康的 Node 列表
            current_plan: 当前调度计划 {portfolio_id: node_id}
            orphaned_portfolios: 需要重新分配的 portfolio_id 列表

        Returns:
            Dict: 新的调度计划 {portfolio_id: node_id}
        """
        new_plan = {}

        # 1. 保留当前健康的分配
        healthy_node_ids = {n['node_id'] for n in healthy_nodes}
        for portfolio_id, node_id in current_plan.items():
            # 跳过孤儿portfolio（等待分配）
            if node_id == "__ORPHANED__":
                continue
            if node_id in healthy_node_ids:
                new_plan[portfolio_id] = node_id

        # 2. 重新分配孤儿 Portfolio
        if orphaned_portfolios:
            # 如果没有健康节点，保留孤儿portfolio在计划中（标记为特殊值）
            if not healthy_nodes:
                for portfolio_id in orphaned_portfolios:
                    # Redis不能存储None，使用特殊字符串标记
                    new_plan[portfolio_id] = "__ORPHANED__"
                    logger.warning(
                        f"Portfolio {portfolio_id[:8]}... marked as orphaned "
                        f"(waiting for available node)"
                    )
                return new_plan

            # 按负载排序（负载低的优先）
            sorted_nodes = sorted(
                healthy_nodes,
                key=lambda n: n['metrics']['portfolio_count']
            )

            for portfolio_id in orphaned_portfolios:
                # 找到负载最低的 Node
                assigned = False
                for node in sorted_nodes:
                    node_id = node['node_id']
                    portfolio_count = node['metrics']['portfolio_count']

                    # 检查是否超过上限
                    if portfolio_count < self.MAX_PORTFOLIOS_PER_NODE:
                        new_plan[portfolio_id] = node_id
                        assigned = True

                        # 更新计数（用于后续分配）
                        node['metrics']['portfolio_count'] += 1
                        break

                if not assigned:
                    logger.warning(
                        f"No available node for portfolio {portfolio_id[:8]}... "
                        f"(all {len(healthy_nodes)} nodes at max capacity {self.MAX_PORTFOLIOS_PER_NODE})"
                    )

            # 发送负载均衡完成通知
            try:
                from ginkgo.notifier.core.notification_service import notify

                # 计算负载分布
                portfolio_distribution = {}
                for node_id in [n['node_id'] for n in healthy_nodes]:
                    count = sum(1 for pid in new_plan.values() if pid == node_id)
                    portfolio_distribution[node_id] = count

                notify(
                    f"负载均衡完成 - {len(orphaned_portfolios)}个Portfolio已重新分配",
                    level="INFO",
                    module="Scheduler",
                    details={
                        "重新分配数": len(orphaned_portfolios),
                        "可用节点数": len(healthy_nodes),
                        "负载分布": str(portfolio_distribution)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to send load balancing notification: {e}")

        return new_plan

    def _get_plan_changes(
        self,
        old_plan: Dict[str, str],
        new_plan: Dict[str, str]
    ) -> Dict[str, tuple]:
        """
        比较新旧调度计划的变化

        Args:
            old_plan: 旧计划 {portfolio_id: node_id}
            new_plan: 新计划 {portfolio_id: node_id}

        Returns:
            Dict: 变化字典 {portfolio_id: (old_node_id, new_node_id)}
                  old_node_id 或 new_node_id 为 None 表示新增或删除
        """
        changes = {}

        # 检查新增和变更
        all_portfolio_ids = set(old_plan.keys()) | set(new_plan.keys())

        for portfolio_id in all_portfolio_ids:
            old_node = old_plan.get(portfolio_id)
            new_node = new_plan.get(portfolio_id)

            if old_node != new_node:
                changes[portfolio_id] = (old_node, new_node)

        return changes

    # ========================================================================
    # 调度更新发布
    # ========================================================================

    @time_logger(threshold=1.0)
    @retry(max_try=3)
    def _publish_schedule_update(
        self,
        old_plan: Dict[str, str],
        new_plan: Dict[str, str]
    ):
        """
        发布调度更新到 Kafka

        比较新旧计划，只发布变更的分配。

        Args:
            old_plan: 旧的调度计划 {portfolio_id: node_id}
            new_plan: 新的调度计划 {portfolio_id: node_id}
        """
        try:
            # 找出变更
            changes = []
            for portfolio_id, new_node_id in new_plan.items():
                old_node_id = old_plan.get(portfolio_id)

                if old_node_id != new_node_id:
                    changes.append({
                        'portfolio_id': portfolio_id,
                        'from_node': old_node_id,  # None 表示新分配
                        'to_node': new_node_id,
                        'timestamp': datetime.now().isoformat()
                    })

            # 发布变更到 Kafka
            if changes:
                for change in changes:
                    self._send_schedule_command(change)

                # 更新 Redis 中的调度计划
                self.redis_client.delete(self.SCHEDULE_PLAN_KEY)
                if new_plan:
                    self.redis_client.hset(self.SCHEDULE_PLAN_KEY, mapping=new_plan)

                # 只打印总结日志
                logger.info(f"Schedule updated: {len(changes)} portfolios assigned")

                # 发送调度计划变化通知
                try:
                    from ginkgo.notifier.core.notification_service import notify

                    # 统计变化类型
                    new_count = sum(1 for c in changes if c[1][0] in (None, "__ORPHANED__"))
                    migrate_count = sum(1 for c in changes if c[1][0] not in (None, "__ORPHANED__") and c[1][1] != "__ORPHANED__")
                    orphaned_count = sum(1 for c in changes if c[1][1] == "__ORPHANED__")

                    notify(
                        f"调度计划已更新 - {len(changes)}个Portfolio分配变化",
                        level="INFO",
                        module="Scheduler",
                        details={
                            "总变化数": len(changes),
                            "新分配": new_count,
                            "迁移": migrate_count,
                            "孤儿": orphaned_count
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send schedule update notification: {e}")

        except Exception as e:
            logger.error(f"Failed to publish schedule update: {e}")

    def _send_schedule_command(self, change: Dict):
        """
        发送调度命令到 Kafka

        Args:
            change: 变更信息 {portfolio_id, from_node, to_node, timestamp}
        """
        try:
            # 构造ExecutionNode期望的消息格式
            command = "portfolio.migrate"
            command_data = {
                "command": command,
                "portfolio_id": change['portfolio_id'],
                "source_node": change['from_node'],
                "target_node": change['to_node'],
                "timestamp": change['timestamp']
            }

            # [DEBUG] 打印Kafka消息
            logger.info(f"[KAFKA] Sending schedule command:")
            logger.info(f"  Topic: schedule.updates")
            logger.info(f"  Command: {command}")
            logger.info(f"  Portfolio: {change['portfolio_id'][:8]}...")
            logger.info(f"  Source: {change['from_node']}")
            logger.info(f"  Target: {change['to_node']}")

            # 发送到Kafka
            success = self.kafka_producer.send(
                topic="schedule.updates",
                msg=command_data
            )

            if not success:
                logger.error(f"[KAFKA] Failed to send portfolio {change['portfolio_id'][:8]} to Kafka")
            else:
                logger.info(f"[KAFKA] ✓ Message sent successfully")

        except Exception as e:
            logger.error(f"Failed to send schedule command: {e}")

    # ========================================================================
    # 命令处理（通过 Kafka 接收主动调度命令）
    # ========================================================================

    def _check_commands(self):
        """
        非阻塞检查并处理命令

        设计要点：
        - 在主线程中调用，避免线程嵌套
        - 非阻塞poll，一次处理所有可用命令
        - 调用时机：每次调度循环后 + 每5秒检查一次
        """
        if not self.command_consumer:
            return

        try:
            import json

            # 非阻塞地检查命令（timeout_ms=0）
            # TODO: 适配 GinkgoConsumer 的接口
            # message = self.command_consumer.poll(timeout_ms=0)
            # while message:
            #     command_data = json.loads(message.value.decode('utf-8'))
            #     self._process_command(command_data)
            #     message = self.command_consumer.poll(timeout_ms=0)

            pass  # TODO: 实现实际Kafka消费

        except Exception as e:
            logger.error(f"Error checking commands: {e}")

    def _process_command(self, command_data: Dict):
        """
        处理单个命令

        Args:
            command_data: 命令数据 {command, timestamp, params}
        """
        try:
            command = command_data.get('command')
            timestamp = command_data.get('timestamp')
            params = command_data.get('params', {})

            logger.info(f"Received command: {command} at {timestamp}")

            if command == 'recalculate':
                self._handle_recalculate(params)

            elif command == 'schedule':
                self._handle_schedule(params)

            elif command == 'migrate':
                self._handle_migrate(params)

            elif command == 'pause':
                self._handle_pause(params)

            elif command == 'resume':
                self._handle_resume(params)

            elif command == 'status':
                self._handle_status(params)

            else:
                logger.warning(f"Unknown command: {command}")

        except Exception as e:
            logger.error(f"Failed to process command: {e}")

    def _handle_recalculate(self, params: Dict):
        """
        处理重新计算命令（负载均衡）

        Args:
            params: 命令参数 {force: bool, dry_run: bool}
        """
        force = params.get('force', False)

        # 检查暂停状态
        if self.is_paused and not force:
            logger.warning("Scheduler is PAUSED, recalculate command rejected")
            logger.info("Use --force to override and execute recalculate while paused")
            return

        if self.is_paused and force:
            logger.warning("Scheduler is PAUSED, executing recalculate with --force")

        logger.info("Executing recalculate command")

        # 立即执行一次调度循环
        self._schedule_loop()

        logger.info("Recalculate completed")

    def _handle_schedule(self, params: Dict):
        """
        处理立即调度命令

        Args:
            params: 命令参数 {force: bool}
        """
        force = params.get('force', False)

        # 检查暂停状态
        if self.is_paused and not force:
            logger.warning("Scheduler is PAUSED, schedule command rejected")
            logger.info("Use --force to override and execute schedule while paused")
            return

        if self.is_paused and force:
            logger.warning("Scheduler is PAUSED, executing schedule with --force")

        logger.info("Executing immediate schedule command")

        # 获取当前调度计划
        current_plan = self._get_current_schedule_plan()

        # 获取所有 Portfolio
        all_portfolios = self._get_all_portfolios()

        # 找出未分配的 Portfolio
        assigned_ids = set(current_plan.keys())
        unassigned = [p for p in all_portfolios if p['uuid'] not in assigned_ids]

        if unassigned:
            logger.info(f"Found {len(unassigned)} unassigned portfolios")

            # 获取健康节点
            healthy_nodes = self._get_healthy_nodes()

            # 分配未分配的 Portfolio
            new_plan = self._assign_portfolios(
                healthy_nodes=healthy_nodes,
                current_plan=current_plan,
                orphaned_portfolios=[p['uuid'] for p in unassigned]
            )

            # 发布调度更新
            if new_plan != current_plan:
                self._publish_schedule_update(current_plan, new_plan)
                logger.info(f"Assigned {len(unassigned)} portfolios")
        else:
            logger.info("No unassigned portfolios to schedule")

    def _handle_migrate(self, params: Dict):
        """
        处理迁移命令

        Args:
            params: {portfolio_id, from_node, to_node}
        """
        portfolio_id = params.get('portfolio_id')
        from_node = params.get('from_node')
        to_node = params.get('to_node')

        logger.info(f"Migrating {portfolio_id} from {from_node} to {to_node}")

        # 发布迁移命令到 Kafka
        migration_command = {
            'command': 'portfolio.migrate',
            'portfolio_id': portfolio_id,
            'source_node': from_node,
            'target_node': to_node,
            'timestamp': datetime.now().isoformat()
        }

        # TODO: 发送到 Kafka schedule.updates
        self._send_schedule_command({
            'portfolio_id': portfolio_id,
            'from_node': from_node,
            'to_node': to_node,
            'timestamp': migration_command['timestamp']
        })

        logger.info(f"Migration command sent for {portfolio_id}")

    def _handle_pause(self, params: Dict):
        """
        处理暂停命令

        Args:
            params: {} (无参数)
        """
        if self.is_paused:
            logger.info("Scheduler is already paused")
        else:
            self.is_paused = True
            logger.info(f"Scheduler {self.node_id} PAUSED - scheduling loop suspended")

    def _handle_resume(self, params: Dict):
        """
        处理恢复命令

        Args:
            params: {} (无参数)
        """
        if not self.is_paused:
            logger.info("Scheduler is not paused")
        else:
            self.is_paused = False
            logger.info(f"Scheduler {self.node_id} RESUMED - scheduling loop restored")

    def _handle_status(self, params: Dict):
        """
        处理状态查询命令

        Args:
            params: {} (无参数)
        """
        # 确定主状态
        if self.should_stop:
            main_status = 'STOPPED'
        elif self.is_paused:
            main_status = 'PAUSED'
        elif self.is_running:
            main_status = 'RUNNING'
        else:
            main_status = 'INITIALIZED'

        # 确定命令可用性
        if self.is_paused:
            commands_status = {
                'pause': 'already_paused',
                'resume': 'available',
                'recalculate': 'use --force',
                'schedule': 'use --force',
                'migrate': 'available',  # 紧急干预始终可用
                'reload': 'available',   # 配置重载始终可用
                'status': 'available'
            }
        else:
            commands_status = {
                'pause': 'available',
                'resume': 'not_paused',
                'recalculate': 'available',
                'schedule': 'available',
                'migrate': 'available',
                'reload': 'available',
                'status': 'available'
            }

        status = {
            'node_id': self.node_id,
            'main_status': main_status,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'should_stop': self.should_stop,
            'schedule_interval': self.schedule_interval,
            'auto_scheduling': not self.is_paused and self.is_running,
            'commands_available': commands_status
        }

        logger.info(f"Scheduler status: {status}")

        # TODO: 可以通过 Kafka 或其他方式返回状态给调用者
        # 例如：发送到 status.report topic 或 Redis

    def _send_status_report(self):
        """
        发送调度器状态汇报（每30分钟）

        汇报内容包括：
        - 存活节点列表
        - 每个节点下的Portfolio分配情况
        - 总体运行状态
        """
        try:
            # 获取存活节点
            healthy_nodes = self._get_healthy_nodes()

            # 获取当前调度计划
            current_plan = self._get_current_schedule_plan()

            # 构建节点到Portfolio的映射
            node_portfolios = {}
            for node_id in [n['node_id'] for n in healthy_nodes]:
                portfolios_on_node = [
                    pid for pid, assigned_node in current_plan.items()
                    if assigned_node == node_id
                ]
                node_portfolios[node_id] = portfolios_on_node

            # 构建汇报详情
            node_details = []
            total_portfolios = 0

            for node in healthy_nodes:
                node_id = node['node_id']
                portfolio_count = len(node_portfolios.get(node_id, []))
                total_portfolios += portfolio_count
                metrics = node['metrics']

                node_details.append(
                    f"{node_id}: {portfolio_count}个Portfolio "
                    f"(队列:{metrics['queue_size']}, CPU:{metrics['cpu_usage']:.1f}%)"
                )

            # 发送状态汇报通知
            from ginkgo.notifier.core.notification_service import notify

            notify(
                f"调度器状态汇报 - {len(healthy_nodes)}个存活节点, {total_portfolios}个Portfolio运行中",
                level="INFO",
                module="Scheduler",
                details={
                    "存活节点数": len(healthy_nodes),
                    "运行Portfolio总数": total_portfolios,
                    "节点详情": " | ".join(node_details[:5])  # 限制长度
                }
            )

            logger.info(
                f"Status report sent: {len(healthy_nodes)} nodes, "
                f"{total_portfolios} portfolios"
            )

        except Exception as e:
            logger.warning(f"Failed to send status report: {e}")

    def _get_all_portfolios(self) -> List[Dict]:
        """
        获取所有 Portfolio

        Returns:
            List[Dict]: Portfolio 列表
        """
        try:
            from ginkgo import services

            portfolio_service = services.data.portfolio_service()
            result = portfolio_service.get(is_live=True)

            if result.success:
                return result.data
            else:
                logger.error(f"Failed to get portfolios: {result.message}")
                return []

        except Exception as e:
            logger.error(f"Failed to get portfolios: {e}")
            return []

    def _discover_new_portfolios(self, current_plan: Dict[str, str]) -> List[str]:
        """
        发现新的 live portfolio（从数据库中查找 is_live=True 但不在调度计划中的）

        Args:
            current_plan: 当前调度计划 {portfolio_id: node_id}

        Returns:
            List[str]: 需要分配的 portfolio_id 列表
        """
        try:
            # 获取所有 live portfolio（返回MPortfolio对象列表）
            all_portfolios = self._get_all_portfolios()

            if not all_portfolios:
                return []

            # 找出不在当前计划中的 portfolio
            assigned_ids = set(current_plan.keys())
            new_portfolios = [p.uuid for p in all_portfolios if p.uuid not in assigned_ids]

            # 只在发现新portfolio时打印
            if new_portfolios:
                logger.info(f"New portfolios: {[p[:8] for p in new_portfolios]}")

            return new_portfolios

        except Exception as e:
            logger.error(f"Failed to discover new portfolios: {e}")
            return []
