# Upstream: Scheduler (编排器，持有CommandHandler实例)
# Downstream: Scheduler状态 (is_paused), LoadBalancer, SchedulePublisher
# Role: 处理Kafka调度命令(recalculate/schedule/migrate/pause/resume)

"""
命令处理模块

处理来自 Kafka 的调度命令（recalculate/schedule/migrate/pause/resume/status）。
通过回调接口与 Scheduler 交互，避免循环依赖。
"""

import logging
from datetime import datetime
from typing import Dict, Callable, Optional

logger = logging.getLogger(__name__)


class CommandHandler:
    """调度命令处理器"""

    def __init__(
        self,
        scheduler_ref,
        schedule_loop_callback: Callable,
        get_healthy_nodes_callback: Callable,
        get_current_plan_callback: Callable,
        get_all_portfolios_callback: Callable,
        assign_portfolios_callback: Callable,
        publish_update_callback: Callable,
        send_command_callback: Callable,
    ):
        """
        Args:
            scheduler_ref: Scheduler 实例引用（用于访问 is_paused 等状态）
            schedule_loop_callback: 调用 _schedule_loop 的回调
            get_healthy_nodes_callback: 获取健康节点的回调
            get_current_plan_callback: 获取当前计划的回调
            get_all_portfolios_callback: 获取所有 Portfolio 的回调
            assign_portfolios_callback: 分配 Portfolio 的回调
            publish_update_callback: 发布调度更新的回调
            send_command_callback: 发送调度命令的回调
        """
        self._scheduler = scheduler_ref
        self._schedule_loop = schedule_loop_callback
        self._get_healthy_nodes = get_healthy_nodes_callback
        self._get_current_plan = get_current_plan_callback
        self._get_all_portfolios = get_all_portfolios_callback
        self._assign_portfolios = assign_portfolios_callback
        self._publish_update = publish_update_callback
        self._send_command = send_command_callback

    def check_commands(self, command_consumer):
        """
        非阻塞检查并处理命令

        Args:
            command_consumer: Kafka 命令消费者
        """
        if not command_consumer:
            return

        try:
            import json
            # TODO: 适配 GinkgoConsumer 的接口
            pass
        except Exception as e:
            logger.error(f"Error checking commands: {e}")

    def process_command(self, command_data: Dict):
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

            handler_map = {
                'recalculate': self.handle_recalculate,
                'schedule': self.handle_schedule,
                'migrate': self.handle_migrate,
                'pause': self.handle_pause,
                'resume': self.handle_resume,
                'status': self.handle_status,
            }

            handler = handler_map.get(command)
            if handler:
                handler(params)
            else:
                logger.warning(f"Unknown command: {command}")

        except Exception as e:
            logger.error(f"Failed to process command: {e}")

    def handle_recalculate(self, params: Dict):
        """处理重新计算命令"""
        force = params.get('force', False)

        if self._scheduler.is_paused and not force:
            logger.warning("Scheduler is PAUSED, recalculate command rejected")
            logger.info("Use --force to override and execute recalculate while paused")
            return

        if self._scheduler.is_paused and force:
            logger.warning("Scheduler is PAUSED, executing recalculate with --force")

        logger.info("Executing recalculate command")
        self._schedule_loop()
        logger.info("Recalculate completed")

    def handle_schedule(self, params: Dict):
        """处理立即调度命令"""
        force = params.get('force', False)

        if self._scheduler.is_paused and not force:
            logger.warning("Scheduler is PAUSED, schedule command rejected")
            logger.info("Use --force to override and execute schedule while paused")
            return

        if self._scheduler.is_paused and force:
            logger.warning("Scheduler is PAUSED, executing schedule with --force")

        logger.info("Executing immediate schedule command")

        current_plan = self._get_current_plan()
        all_portfolios = self._get_all_portfolios()

        assigned_ids = set(current_plan.keys())
        unassigned = [p for p in all_portfolios if p['uuid'] not in assigned_ids]

        if unassigned:
            logger.info(f"Found {len(unassigned)} unassigned portfolios")

            healthy_nodes = self._get_healthy_nodes()

            new_plan = self._assign_portfolios(
                healthy_nodes=healthy_nodes,
                current_plan=current_plan,
                orphaned_portfolios=[p['uuid'] for p in unassigned]
            )

            if new_plan != current_plan:
                self._publish_update(current_plan, new_plan)
                logger.info(f"Assigned {len(unassigned)} portfolios")
        else:
            logger.info("No unassigned portfolios to schedule")

    def handle_migrate(self, params: Dict):
        """处理迁移命令"""
        portfolio_id = params.get('portfolio_id')
        from_node = params.get('from_node')
        to_node = params.get('to_node')

        logger.info(f"Migrating {portfolio_id} from {from_node} to {to_node}")

        self._send_command({
            'portfolio_id': portfolio_id,
            'from_node': from_node,
            'to_node': to_node,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Migration command sent for {portfolio_id}")

    def handle_pause(self, params: Dict):
        """处理暂停命令"""
        if self._scheduler.is_paused:
            logger.info("Scheduler is already paused")
        else:
            self._scheduler.is_paused = True
            logger.info(f"Scheduler {self._scheduler.node_id} PAUSED - scheduling loop suspended")

    def handle_resume(self, params: Dict):
        """处理恢复命令"""
        if not self._scheduler.is_paused:
            logger.info("Scheduler is not paused")
        else:
            self._scheduler.is_paused = False
            logger.info(f"Scheduler {self._scheduler.node_id} RESUMED - scheduling loop restored")

    def handle_status(self, params: Dict):
        """处理状态查询命令"""
        s = self._scheduler

        if s.should_stop:
            main_status = 'STOPPED'
        elif s.is_paused:
            main_status = 'PAUSED'
        elif s.is_running:
            main_status = 'RUNNING'
        else:
            main_status = 'INITIALIZED'

        if s.is_paused:
            commands_status = {
                'pause': 'already_paused',
                'resume': 'available',
                'recalculate': 'use --force',
                'schedule': 'use --force',
                'migrate': 'available',
                'reload': 'available',
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
            'node_id': s.node_id,
            'main_status': main_status,
            'is_running': s.is_running,
            'is_paused': s.is_paused,
            'should_stop': s.should_stop,
            'schedule_interval': s.schedule_interval,
            'auto_scheduling': not s.is_paused and s.is_running,
            'commands_available': commands_status
        }

        logger.info(f"Scheduler status: {status}")
