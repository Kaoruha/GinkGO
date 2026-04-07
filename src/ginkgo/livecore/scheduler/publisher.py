# Upstream: Scheduler._publish_schedule_update()
# Downstream: Kafka (schedule.updates topic), Redis (调度计划更新)
# Role: 比较新旧计划差异并发布调度变更到Kafka

"""
调度更新发布模块

负责比较新旧计划差异，通过 Kafka 发布调度更新到 schedule.updates topic。
"""

import logging
from datetime import datetime
from typing import Dict

from ginkgo.libs.utils.common import time_logger, retry
from ginkgo.interfaces.kafka_topics import KafkaTopics

logger = logging.getLogger(__name__)


class SchedulePublisher:
    """调度更新 Kafka 发布器"""

    SCHEDULE_PLAN_KEY = "schedule:plan"

    def __init__(self, redis_client, kafka_producer):
        self.redis_client = redis_client
        self.kafka_producer = kafka_producer

    @time_logger(threshold=1.0)
    @retry(max_try=3)
    def publish_schedule_update(
        self,
        old_plan: Dict[str, str],
        new_plan: Dict[str, str],
    ):
        """
        发布调度更新到 Kafka

        比较新旧计划，只发布变更的分配。

        Args:
            old_plan: 旧的调度计划 {portfolio_id: node_id}
            new_plan: 新的调度计划 {portfolio_id: node_id}
        """
        try:
            changes = []
            for portfolio_id, new_node_id in new_plan.items():
                old_node_id = old_plan.get(portfolio_id)

                if old_node_id != new_node_id:
                    changes.append({
                        'portfolio_id': portfolio_id,
                        'from_node': old_node_id,
                        'to_node': new_node_id,
                        'timestamp': datetime.now().isoformat()
                    })

            if changes:
                for change in changes:
                    self.send_schedule_command(change)

                # 更新 Redis 中的调度计划
                self.redis_client.delete(self.SCHEDULE_PLAN_KEY)
                if new_plan:
                    self.redis_client.hset(self.SCHEDULE_PLAN_KEY, mapping=new_plan)

                logger.info(f"Schedule updated: {len(changes)} portfolios assigned")

                try:
                    from ginkgo.notifier.core.notification_service import notify

                    new_count = sum(1 for c in changes if c['from_node'] in (None, "__ORPHANED__"))
                    migrate_count = sum(
                        1 for c in changes
                        if c['from_node'] not in (None, "__ORPHANED__")
                        and c['to_node'] != "__ORPHANED__"
                    )
                    orphaned_count = sum(1 for c in changes if c['to_node'] == "__ORPHANED__")

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

    def send_schedule_command(self, change: Dict):
        """
        发送调度命令到 Kafka

        Args:
            change: 变更信息 {portfolio_id, from_node, to_node, timestamp}
        """
        try:
            from ginkgo.interfaces.dtos import ScheduleUpdateDTO

            command_dto = ScheduleUpdateDTO(
                command=ScheduleUpdateDTO.Commands.PORTFOLIO_MIGRATE,
                portfolio_id=change['portfolio_id'],
                source_node=change['from_node'],
                target_node=change['to_node'],
                source="scheduler"
            )

            logger.info(f"[KAFKA] Sending schedule command:")
            logger.info(f"  Topic: {KafkaTopics.SCHEDULE_UPDATES}")
            logger.info(f"  Command: {command_dto.command}")
            logger.info(f"  Portfolio: {change['portfolio_id'][:8]}...")
            logger.info(f"  Source: {change['from_node']}")
            logger.info(f"  Target: {change['to_node']}")

            success = self.kafka_producer.send(
                topic=KafkaTopics.SCHEDULE_UPDATES,
                msg=command_dto.model_dump_json()
            )

            if not success:
                logger.error(f"[KAFKA] Failed to send portfolio {change['portfolio_id'][:8]} to Kafka")
            else:
                logger.info(f"[KAFKA] ✓ Message sent successfully")

        except Exception as e:
            logger.error(f"Failed to send schedule command: {e}")
