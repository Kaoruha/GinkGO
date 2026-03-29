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

使用方式：
    from ginkgo.livecore.scheduler import Scheduler

    scheduler = Scheduler()
    scheduler.start()
"""

import time
import threading
import logging
from typing import Dict, List, Optional
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
from ginkgo.interfaces.kafka_topics import KafkaTopics

from .heartbeat import HeartbeatChecker
from .load_balancer import LoadBalancer
from .plan_manager import PlanManager
from .publisher import SchedulePublisher
from .command_handler import CommandHandler

logger = logging.getLogger(__name__)


class Scheduler(threading.Thread):
    """
    Scheduler 调度器（无状态设计）

    编排器模式：组合 HeartbeatChecker、LoadBalancer、PlanManager、
    SchedulePublisher、CommandHandler 五个子模块完成调度工作。
    """

    # Redis 键前缀
    SCHEDULE_PLAN_KEY = "schedule:plan"
    NODE_PORTFOLIOS_PREFIX = "node:"
    NODE_METRICS_PREFIX = "node:metrics:"
    PORTFOLIO_STATUS_PREFIX = "portfolio:"

    # 默认配置
    DEFAULT_SCHEDULE_INTERVAL = 30
    STATUS_REPORT_INTERVAL = 1800
    HEARTBEAT_TTL = 30
    MAX_PORTFOLIOS_PER_NODE = 5
    COMMAND_TOPIC = "scheduler.commands"

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        kafka_producer: Optional[GinkgoProducer] = None,
        schedule_interval: int = DEFAULT_SCHEDULE_INTERVAL,
        status_report_interval: int = STATUS_REPORT_INTERVAL,
        node_id: str = "scheduler_1"
    ):
        super().__init__()

        if redis_client is None:
            from ginkgo.data.crud import RedisCRUD
            redis_crud = RedisCRUD()
            redis_client = redis_crud.redis

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
        self.is_paused = False
        self.last_status_report_time = 0

        # 创建命令消费者
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

        # 初始化子模块
        self._heartbeat_checker = HeartbeatChecker(redis_client)
        self._load_balancer = LoadBalancer(max_portfolios_per_node=self.MAX_PORTFOLIOS_PER_NODE)
        self._plan_manager = PlanManager(redis_client)
        self._publisher = SchedulePublisher(redis_client, kafka_producer)
        self._command_handler = CommandHandler(
            scheduler_ref=self,
            schedule_loop_callback=self._schedule_loop,
            get_healthy_nodes_callback=self._get_healthy_nodes,
            get_current_plan_callback=self._get_current_schedule_plan,
            get_all_portfolios_callback=self._get_all_portfolios,
            assign_portfolios_callback=self._assign_portfolios,
            publish_update_callback=self._publish_schedule_update,
            send_command_callback=self._send_schedule_command,
        )

        logger.info(f"Scheduler {self.node_id} initialized (interval={schedule_interval}s, status_report={status_report_interval}s)")

    def run(self):
        """Scheduler 主循环"""
        self.is_running = True
        logger.info(f"Scheduler {self.node_id} started")

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
                self._command_handler.check_commands(self.command_consumer)

                if not self.is_paused:
                    self._schedule_loop()
                else:
                    logger.debug(f"Scheduler {self.node_id} is paused, skipping schedule loop")

                current_time = time.time()
                if current_time - self.last_status_report_time >= self.status_report_interval:
                    self._send_status_report()
                    self.last_status_report_time = current_time

                for second in range(self.schedule_interval):
                    if self.should_stop:
                        break
                    time.sleep(1)

                    if second > 0 and second % 5 == 0:
                        self._command_handler.check_commands(self.command_consumer)

            except Exception as e:
                logger.error(f"Scheduler {self.node_id} error: {e}")
                time.sleep(5)

        self.is_running = False
        logger.info(f"Scheduler {self.node_id} stopped")

    def stop(self):
        """停止 Scheduler - 优雅关闭"""
        logger.info(f"")
        logger.info(f"═══════════════════════════════════════════════════════")
        logger.info(f"🛑 Stopping Scheduler {self.node_id}")
        logger.info(f"═══════════════════════════════════════════════════════")

        logger.info(f"[Step 1] Setting stop flag...")
        self.should_stop = True
        self.is_running = False
        logger.info(f"  ✅ Stop flag set")

        logger.info(f"[Step 2] Cleaning up Redis data...")
        self._cleanup_redis_data()

        logger.info(f"[Step 3] Closing Kafka Consumer...")
        if self.command_consumer:
            try:
                self.command_consumer.close()
                logger.info(f"  ✅ Command consumer closed")
            except Exception as e:
                logger.error(f"  ✗ Error closing command consumer: {e}")
        else:
            logger.info(f"  ℹ️  No command consumer to close")

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

        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                f"Scheduler {self.node_id} 已停止",
                level="INFO",
                module="Scheduler",
                details={
                    "节点ID": self.node_id,
                    "停止时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to send stop notification: {e}")

    def _cleanup_redis_data(self):
        """清理 Redis 中的 Scheduler 相关数据"""
        try:
            deleted_keys = []

            from ginkgo.data.redis_schema import RedisKeyBuilder
            heartbeat_key = RedisKeyBuilder.scheduler_heartbeat(self.node_id)
            try:
                if self.redis_client.exists(heartbeat_key):
                    self.redis_client.delete(heartbeat_key)
                    deleted_keys.append(heartbeat_key)
                    logger.info(f"  ✅ Deleted scheduler heartbeat: {heartbeat_key}")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not delete heartbeat key: {e}")

            state_key = f"scheduler:state:{self.node_id}"
            try:
                if self.redis_client.exists(state_key):
                    self.redis_client.delete(state_key)
                    deleted_keys.append(state_key)
                    logger.info(f"  ✅ Deleted scheduler state: {state_key}")
            except Exception as e:
                logger.warning(f"  ⚠️  Could not delete state key: {e}")

            if deleted_keys:
                logger.info(f"  ✅ Total keys deleted: {len(deleted_keys)}")
            else:
                logger.info(f"  ℹ️  No scheduler-specific keys to delete")

        except Exception as e:
            logger.error(f"  ✗ Error cleaning up Redis data: {e}")

    # ========================================================================
    # 子模块委托方法（保持向后兼容）
    # ========================================================================

    def _get_healthy_nodes(self) -> List[Dict]:
        return self._heartbeat_checker.get_healthy_nodes()

    def _get_current_schedule_plan(self) -> Dict[str, str]:
        return self._plan_manager.get_current_schedule_plan()

    def _get_all_portfolios(self) -> List[Dict]:
        return self._plan_manager.get_all_portfolios()

    def _assign_portfolios(
        self,
        healthy_nodes: List[Dict],
        current_plan: Dict[str, str],
        orphaned_portfolios: List[str]
    ) -> Dict[str, str]:
        return self._load_balancer.assign_portfolios(healthy_nodes, current_plan, orphaned_portfolios)

    def _get_plan_changes(self, old_plan: Dict[str, str], new_plan: Dict[str, str]) -> Dict[str, tuple]:
        return self._load_balancer.get_plan_changes(old_plan, new_plan)

    def _publish_schedule_update(self, old_plan: Dict[str, str], new_plan: Dict[str, str]):
        self._publisher.publish_schedule_update(old_plan, new_plan)

    def _send_schedule_command(self, change: Dict):
        self._publisher.send_schedule_command(change)

    def _schedule_loop(self):
        """
        执行一次完整的调度循环

        编排子模块完成：心跳检测 → 计划管理 → 负载均衡 → 发布更新
        """
        # 1. 获取健康的 ExecutionNode
        healthy_nodes = self._get_healthy_nodes()

        # 2. 获取当前调度计划
        current_plan = self._get_current_schedule_plan()

        # 3. 发现新的 live portfolio
        new_portfolios = self._plan_manager.discover_new_portfolios(current_plan)

        # 3.5. 清理已删除的 portfolio
        deleted_portfolios = self._plan_manager.detect_deleted_portfolios(current_plan)
        if deleted_portfolios:
            logger.warning(f"Deleted portfolios detected: {[p[:8] for p in deleted_portfolios]}")

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

            for portfolio_id in deleted_portfolios:
                if portfolio_id in current_plan:
                    del current_plan[portfolio_id]

            self.redis_client.delete(self.SCHEDULE_PLAN_KEY)
            if current_plan:
                self.redis_client.hset(self.SCHEDULE_PLAN_KEY, mapping=current_plan)

            logger.info(f"Removed {len(deleted_portfolios)} deleted portfolios from schedule plan and updated Redis")

        # 4. 检测离线 Node 的 Portfolio
        orphaned_portfolios = self._plan_manager.detect_orphaned_portfolios(healthy_nodes, current_plan)

        # ========== 调度信息打印 ==========
        logger.info("")
        logger.info("="*70)
        logger.info(f"Scheduler Cycle - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*70)

        logger.info(f"[DEBUG] Current schedule plan ({len(current_plan)} portfolios):")
        for portfolio_id, node_id in current_plan.items():
            status_icon = "❌" if node_id == "__ORPHANED__" else "✅"
            logger.info(f"  {status_icon} {portfolio_id[:8]}... → {node_id}")

        logger.info("-"*70)

        if healthy_nodes:
            logger.info(f"Available schedulable nodes: {len(healthy_nodes)}")
            for node in healthy_nodes:
                node_id = node['node_id']
                count = node['metrics']['portfolio_count']
                logger.info(f"  - {node_id}: {count}/{self.MAX_PORTFOLIOS_PER_NODE} portfolios")
        else:
            logger.warning("No available schedulable nodes (all nodes offline or no nodes registered)")

        all_portfolios = set(current_plan.keys()) | set(new_portfolios)
        if all_portfolios:
            logger.info(f"Total portfolios: {len(all_portfolios)}")
        else:
            logger.info("No portfolios found")

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

        # 5. 负载均衡
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
                        logger.info(f"  ? {portfolio_id[:8]}...: {old_node} → {new_node} (UNKNOWN)")
                    else:
                        logger.info(f"  + {portfolio_id[:8]}... → {new_node} (REASSIGNED)")
                elif new_node == "__ORPHANED__":
                    logger.info(f"  - {portfolio_id[:8]}... ← {old_node} (ORPHANED)")
                else:
                    logger.info(f"  ~ {portfolio_id[:8]}...: {old_node} → {new_node} (MIGRATED)")
        else:
            logger.info("No schedule plan changes")

        logger.info("="*70)
        logger.info("")

        # 6. 发布调度更新
        if new_plan != current_plan:
            self._publish_schedule_update(current_plan, new_plan)

    def _send_status_report(self):
        """发送调度器状态汇报（每30分钟）"""
        try:
            healthy_nodes = self._get_healthy_nodes()
            current_plan = self._get_current_schedule_plan()

            node_portfolios = {}
            for node_id in [n['node_id'] for n in healthy_nodes]:
                portfolios_on_node = [
                    pid for pid, assigned_node in current_plan.items()
                    if assigned_node == node_id
                ]
                node_portfolios[node_id] = portfolios_on_node

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

            from ginkgo.notifier.core.notification_service import notify

            notify(
                f"调度器状态汇报 - {len(healthy_nodes)}个存活节点, {total_portfolios}个Portfolio运行中",
                level="INFO",
                module="Scheduler",
                details={
                    "存活节点数": len(healthy_nodes),
                    "运行Portfolio总数": total_portfolios,
                    "节点详情": " | ".join(node_details[:5])
                }
            )

            logger.info(
                f"Status report sent: {len(healthy_nodes)} nodes, "
                f"{total_portfolios} portfolios"
            )

        except Exception as e:
            logger.warning(f"Failed to send status report: {e}")
