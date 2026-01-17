# Upstream: None (独立启动)
# Downstream: ExecutionNode (通过Kafka控制命令)
# Role: 定时任务调度器 - 使用APScheduler发送控制命令到Kafka

import os
import yaml
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.interfaces.dtos import ControlCommandDTO
from ginkgo.messaging import GinkgoProducer
from ginkgo.libs import GLOG, GCONF
from ginkgo.livecore.utils.decorators import safe_job_wrapper
from ginkgo.libs.utils.common import retry


class TaskTimer:
    """
    定时任务调度器

    职责：
    1. 使用APScheduler调度定时任务
    2. 发送控制命令到Kafka（bar_snapshot、update_selector等）
    3. 从task_timer.yml加载配置
    4. 支持多个cron规则

    配置文件：~/.ginkgo/task_timer.yml
    """

    # 默认配置文件路径
    CONFIG_PATH = os.path.expanduser("~/.ginkgo/task_timer.yml")

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化TaskTimer

        Args:
            config_path: 配置文件路径（默认使用~/.ginkgo/task_timer.yml）
        """
        self.config_path = config_path or self.CONFIG_PATH

        # APScheduler
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

        # Kafka Producer
        self._producer: Optional[GinkgoProducer] = None

        # 配置缓存
        self._config: Dict[str, Any] = {}
        self._jobs: List[str] = []

        GLOG.INFO("TaskTimer initialized")

    def start(self) -> bool:
        """
        启动TaskTimer

        Returns:
            bool: 启动是否成功
        """
        try:
            GLOG.INFO("TaskTimer starting...")

            # 初始化Kafka Producer
            self._producer = GinkgoProducer(
                bootstrap_servers=GCONF.get("kafka.bootstrap_servers", "localhost:9092")
            )

            # 加载配置
            self._load_config()

            # 添加定时任务
            self._add_jobs()

            # 启动调度器
            self.scheduler.start()

            GLOG.info(f"TaskTimer started with {len(self._jobs)} jobs")
            return True

        except Exception as e:
            GLOG.ERROR(f"TaskTimer start failed: {e}")
            return False

    def stop(self) -> bool:
        """
        停止TaskTimer

        Returns:
            bool: 停止是否成功
        """
        try:
            GLOG.INFO("TaskTimer stopping...")

            # 停止调度器
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)

            # 关闭Kafka Producer
            if self._producer:
                self._producer.close()

            GLOG.INFO("TaskTimer stopped")
            return True

        except Exception as e:
            GLOG.ERROR(f"TaskTimer stop failed: {e}")
            return False

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                GLOG.WARN(f"Config file not found: {self.config_path}, using defaults")
                self._config = self._get_default_config()
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)

            GLOG.INFO(f"Config loaded from {self.config_path}")

        except Exception as e:
            GLOG.ERROR(f"Failed to load config: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "scheduled_tasks": [
                {
                    "name": "bar_snapshot",
                    "cron": "0 21 * * *",  # 每天21:00
                    "command": "bar_snapshot",
                    "enabled": True,
                },
                {
                    "name": "update_selector",
                    "cron": "0 * * * *",  # 每小时
                    "command": "update_selector",
                    "enabled": True,
                },
            ]
        }

    def _add_jobs(self) -> None:
        """添加定时任务到APScheduler"""
        try:
            scheduled_tasks = self._config.get("scheduled_tasks", [])

            for task_config in scheduled_tasks:
                if not task_config.get("enabled", True):
                    continue

                job_name = task_config.get("name")
                cron_expr = task_config.get("cron")
                command = task_config.get("command")

                if not job_name or not cron_expr or not command:
                    GLOG.WARN(f"Invalid task config: {task_config}")
                    continue

                # 解析cron表达式
                cron_parts = cron_expr.split()
                if len(cron_parts) != 5:
                    GLOG.WARN(f"Invalid cron expression: {cron_expr}")
                    continue

                # 创建CronTrigger
                trigger = CronTrigger(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day=cron_parts[2],
                    month=cron_parts[3],
                    day_of_week=cron_parts[4],
                    timezone='Asia/Shanghai',
                    coalesce=True,
                    max_instances=1,
                    misfire_grace_time=300,
                )

                # 添加任务
                job_func = self._get_job_function(command)
                if job_func:
                    self.scheduler.add_job(
                        job_func,
                        trigger=trigger,
                        name=job_name,
                        id=job_name,
                    )
                    self._jobs.append(job_name)
                    GLOG.INFO(f"Added job: {job_name} ({cron_expr})")

        except Exception as e:
            GLOG.ERROR(f"Failed to add jobs: {e}")

    def _get_job_function(self, command: str) -> Optional[callable]:
        """
        获取任务函数

        Args:
            command: 命令类型

        Returns:
            任务函数
        """
        job_functions = {
            "bar_snapshot": self._bar_snapshot_job,
            "update_selector": self._selector_update_job,
            "update_data": self._data_update_job,
        }

        return job_functions.get(command)

    @safe_job_wrapper
    def _bar_snapshot_job(self) -> None:
        """
        K线快照任务（21:00触发）

        发送bar_snapshot控制命令到Kafka，
        DataManager接收后推送当日K线数据。
        """
        try:
            command_dto = ControlCommandDTO(
                command=ControlCommandDTO.Commands.BAR_SNAPSHOT,
                params={"timestamp": datetime.now().isoformat()},
            )

            # 发布到Kafka（带重试）
            self._publish_to_kafka(command_dto.model_dump_json())
            GLOG.INFO("Sent bar_snapshot command to Kafka")

        except Exception as e:
            GLOG.ERROR(f"Bar snapshot job failed: {e}")

    @safe_job_wrapper
    def _selector_update_job(self) -> None:
        """
        Selector更新任务（每小时触发）

        发送update_selector控制命令到Kafka，
        ExecutionNode接收后触发selector.pick()。
        """
        try:
            command_dto = ControlCommandDTO(
                command=ControlCommandDTO.Commands.UPDATE_SELECTOR,
                params={"timestamp": datetime.now().isoformat()},
            )

            # 发布到Kafka（带重试）
            self._publish_to_kafka(command_dto.model_dump_json())
            GLOG.INFO("Sent update_selector command to Kafka")

        except Exception as e:
            GLOG.ERROR(f"Selector update job failed: {e}")

    @safe_job_wrapper
    def _data_update_job(self) -> None:
        """
        数据更新任务（19:00触发）

        发送update_data控制命令到Kafka。
        """
        try:
            command_dto = ControlCommandDTO(
                command=ControlCommandDTO.Commands.UPDATE_DATA,
                params={"timestamp": datetime.now().isoformat()},
            )

            # 发布到Kafka（带重试）
            self._publish_to_kafka(command_dto.model_dump_json())
            GLOG.INFO("Sent update_data command to Kafka")

        except Exception as e:
            GLOG.ERROR(f"Data update job failed: {e}")

    def validate_config(self) -> bool:
        """
        验证配置文件

        Returns:
            bool: 配置是否有效
        """
        try:
            if not os.path.exists(self.config_path):
                GLOG.ERROR(f"Config file not found: {self.config_path}")
                return False

            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            # 验证scheduled_tasks
            scheduled_tasks = config.get("scheduled_tasks", [])
            if not isinstance(scheduled_tasks, list):
                GLOG.ERROR("scheduled_tasks must be a list")
                return False

            for task in scheduled_tasks:
                # 验证必需字段
                if "name" not in task or "cron" not in task or "command" not in task:
                    GLOG.ERROR(f"Task missing required fields: {task}")
                    return False

                # 验证命令类型
                valid_commands = [
                    "bar_snapshot",
                    "update_selector",
                    "update_data",
                ]
                if task["command"] not in valid_commands:
                    GLOG.ERROR(f"Invalid command: {task['command']}")
                    return False

            GLOG.INFO("Config validation passed")
            return True

        except Exception as e:
            GLOG.ERROR(f"Config validation failed: {e}")
            return False

    @retry(max_try=3, backoff_factor=2)
    def _publish_to_kafka(self, message: str) -> None:
        """
        发布控制命令到Kafka（带重试）

        Args:
            message: JSON格式的控制命令
        """
        if self._producer:
            self._producer.send(
                topic=KafkaTopics.CONTROL_COMMANDS,
                message=message,
            )
