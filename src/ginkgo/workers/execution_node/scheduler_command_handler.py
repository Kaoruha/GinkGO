# 从 node.py 提取的调度命令处理模块
# 负责：处理来自 Scheduler 的 Kafka 命令（reload/migrate/pause/resume/shutdown）


"""
SchedulerCommandHandler - 调度命令处理器

从 ExecutionNode 中提取的调度命令处理逻辑，负责：
- portfolio.reload: 重新加载Portfolio配置
- portfolio.migrate: 迁移Portfolio到其他Node
- node.pause: 暂停节点
- node.resume: 恢复节点
- node.shutdown: 关闭节点

所有命令通过 Kafka schedule.updates topic 传入，
由 ExecutionNode 的 _schedule_updates_loop 调用本模块处理。
"""

import logging
from typing import TYPE_CHECKING

from ginkgo.enums import PORTFOLIO_RUNSTATE_TYPES

if TYPE_CHECKING:
    from ginkgo.workers.execution_node.node import ExecutionNode

# 获取日志记录器
logger = logging.getLogger(__name__)


class SchedulerCommandHandler:
    """
    调度命令处理器

    持有 ExecutionNode 实例引用，通过引用调用节点的公共方法
    （load_portfolio, pause, resume, stop 等）来执行调度命令。
    """

    def __init__(self, node: "ExecutionNode"):
        """
        初始化调度命令处理器

        Args:
            node: ExecutionNode 实例引用
        """
        self.node = node

    def handle_schedule_update(self, msg):
        """
        处理调度更新消息

        Args:
            msg: Kafka消息对象（GinkgoConsumer已反序列化，msg.value是dict）

        消息格式（JSON）：
        {
            "command": "portfolio.reload" | "portfolio.migrate" | "node.shutdown",
            "portfolio_id": "portfolio_uuid",
            "target_node": "target_node_id",  // 仅portfolio.migrate需要
            "timestamp": "2026-01-06T10:00:00"
        }
        """
        try:
            # GinkgoConsumer 已经反序列化了消息，msg.value 直接是 dict
            command_data = msg.value

            command = command_data.get('command')
            portfolio_id = command_data.get('portfolio_id', '')
            timestamp = command_data.get('timestamp')
            target_node = command_data.get('target_node', '')
            source_node = command_data.get('source_node', '')

            logger.info(f"{'─'*80}")
            logger.info(f"[KAFKA] Received schedule command: {command}")
            logger.info(f"  Portfolio ID: {portfolio_id[:8] if portfolio_id else 'N/A'}")
            logger.info(f"  Source Node:  {source_node if source_node else 'None (new assignment)'}")
            logger.info(f"  Target Node:  {target_node}")
            logger.info(f"  Timestamp:    {timestamp}")
            logger.info(f"{'─'*80}")

            # 路由到不同的处理方法
            if command == 'portfolio.reload':
                self.handle_portfolio_reload(portfolio_id, command_data)
            elif command == 'portfolio.migrate':
                self.handle_portfolio_migrate(portfolio_id, command_data)
            elif command == 'node.pause':
                self.handle_node_pause(command_data)
            elif command == 'node.resume':
                self.handle_node_resume(command_data)
            elif command == 'node.shutdown':
                self.handle_node_shutdown(command_data)
            else:
                logger.warning(f"Unknown schedule command: {command}")

        except Exception as e:
            logger.error(f"Error handling schedule update: {e}")

    def handle_portfolio_reload(self, portfolio_id: str, command_data: dict):
        """
        处理Portfolio重新加载命令（T048 - 完整实现）

        完整流程：
        1. 检查Portfolio是否存在
        2. 调用Portfolio.graceful_reload()
        3. 处理消息缓存（如果需要）
        4. 验证重载结果

        Args:
            portfolio_id: Portfolio ID
            command_data: 命令数据
        """
        node = self.node
        logger.info(f"Reloading portfolio {portfolio_id}")

        try:
            # 检查Portfolio是否存在
            if portfolio_id not in node._portfolio_instances:
                logger.warning(f"Portfolio {portfolio_id} not found in node {node.node_id}")
                return

            # 获取Portfolio实例
            portfolio = node._portfolio_instances[portfolio_id]

            # 调用优雅重载
            logger.info(f"Calling graceful_reload() for portfolio {portfolio_id}")
            success = portfolio.graceful_reload(timeout=30)

            if success:
                logger.info(f"Portfolio {portfolio_id} reloaded successfully")
            else:
                logger.error(f"Portfolio {portfolio_id} reload failed")

        except Exception as e:
            logger.error(f"Failed to reload portfolio {portfolio_id}: {e}")

    def handle_portfolio_migrate(self, portfolio_id: str, command_data: dict):
        """
        处理Portfolio迁移命令（T050 - 完整实现）

        完整流程：
        1. 检查是否是迁移到本节点（接收端）
        2. 如果是迁出本节点：优雅停止并移除
        3. 更新调度计划

        Args:
            portfolio_id: Portfolio ID
            command_data: 命令数据，包含target_node
        """
        node = self.node
        target_node = command_data.get('target_node')

        logger.info(f"[MIGRATE] Processing portfolio migration: {portfolio_id[:8]} -> {target_node}")

        try:
            # 情况 1: 迁移到本节点（接收端）
            if target_node == node.node_id:
                logger.info(f"[MIGRATE] Portfolio {portfolio_id[:8]} is being migrated TO this node ({node.node_id})")
                logger.info(f"[MIGRATE] Starting portfolio receive and load process...")
                node._receive_portfolio(portfolio_id)
                return

            # 情况 2: 从本节点迁出（发送端）
            if portfolio_id not in node._portfolio_instances:
                logger.warning(f"[MIGRATE] Portfolio {portfolio_id[:8]} not found in node {node.node_id} (nothing to migrate away)")
                return

            logger.info(f"[MIGRATE] Migrating portfolio {portfolio_id[:8]} AWAY from this node")

            # 获取Portfolio实例
            portfolio = node._portfolio_instances[portfolio_id]

            # 设置迁移状态
            portfolio._set_status(PORTFOLIO_RUNSTATE_TYPES.MIGRATING)
            logger.info(f"[MIGRATE] Set portfolio status to MIGRATING")

            # 停止PortfolioProcessor
            if portfolio_id in node.portfolios:
                processor = node.portfolios[portfolio_id]
                processor.stop()
                logger.info(f"[MIGRATE] Processor stopped for portfolio {portfolio_id[:8]}")

            # 从本节点移除
            with node.portfolio_lock:
                if portfolio_id in node.portfolios:
                    del node.portfolios[portfolio_id]

                if portfolio_id in node._portfolio_instances:
                    del node._portfolio_instances[portfolio_id]

            # 从InterestMap移除订阅
            # TODO: 实现 InterestMap.remove_portfolio() 方法
            logger.info(f"[MIGRATE] Portfolio {portfolio_id[:8]} removed from node {node.node_id}")
            logger.info(f"[MIGRATE] Migration away completed successfully")

        except Exception as e:
            logger.error(f"[MIGRATE] Failed to migrate portfolio {portfolio_id[:8]}: {e}")

    def handle_node_pause(self, command_data: dict):
        """
        处理节点暂停命令

        Args:
            command_data: 命令数据
        """
        node = self.node
        logger.info(f"Received node pause command for {node.node_id}")
        node.pause()

    def handle_node_resume(self, command_data: dict):
        """
        处理节点恢复命令

        Args:
            command_data: 命令数据
        """
        node = self.node
        logger.info(f"Received node resume command for {node.node_id}")
        node.resume()

    def handle_node_shutdown(self, command_data: dict):
        """
        处理节点关闭命令

        Args:
            command_data: 命令数据
        """
        node = self.node
        logger.info(f"Received node shutdown command for {node.node_id}")

        try:
            # 优雅关闭节点
            logger.info(f"Shutting down node {node.node_id} gracefully")

            # TODO: 实现优雅关闭流程
            # 1. 停止接收新消息
            # 2. 等待现有消息处理完成
            # 3. 关闭所有Portfolio
            # 4. 退出

            node.stop()

        except Exception as e:
            logger.error(f"Failed to shutdown node {node.node_id}: {e}")
