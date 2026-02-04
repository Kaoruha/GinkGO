# Upstream: None (独立启动)
# Downstream: ExecutionNode (通过Kafka控制命令)
# Role: 定时任务调度器 - 使用APScheduler发送控制命令到Kafka

import os
import time
import yaml
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.interfaces.dtos import ControlCommandDTO
from ginkgo.messaging import GinkgoProducer
from ginkgo.libs import GCONF
from ginkgo.livecore.utils.decorators import safe_job_wrapper
from ginkgo.libs.utils.common import retry

try:
    from redis import Redis
except ImportError:
    Redis = None


class TaskTimer:
    """
    定时任务调度器

    职责：
    1. 使用APScheduler调度定时任务
    2. 发送控制命令到Kafka（bar_snapshot、update_selector等）
    3. 从task_timer.yml加载配置
    4. 支持多个cron规则
    5. 发送心跳到Redis（用于监控组件存活状态）

    配置文件：~/.ginkgo/task_timer.yml
    """

    # 默认配置文件路径
    CONFIG_PATH = os.path.expanduser("~/.ginkgo/task_timer.yml")

    # 心跳配置
    HEARTBEAT_INTERVAL = 10  # 10秒心跳间隔
    HEARTBEAT_TTL = 30       # 30秒TTL

    def __init__(self, config_path: Optional[str] = None, node_id: str = "task_timer_1"):
        """
        初始化TaskTimer

        Args:
            config_path: 配置文件路径（默认使用~/.ginkgo/task_timer.yml）
            node_id: 节点ID，用于心跳标识
        """
        self.config_path = config_path or self.CONFIG_PATH
        self.node_id = node_id

        # APScheduler
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

        # Kafka Producer
        self._producer: Optional[GinkgoProducer] = None

        # 配置缓存
        self._config: Dict[str, Any] = {}
        self._jobs: List[str] = []

        # Redis客户端（用于心跳）
        self._redis_client: Optional[Redis] = None

        # 心跳线程
        self.heartbeat_thread: Optional[threading.Thread] = None

        # 运行状态
        self.is_running = False

        print("[INFO] TaskTimer initialized")

    def _get_redis_client(self) -> Optional[Redis]:
        """获取Redis客户端"""
        if Redis is None:
            return None

        if self._redis_client is None:
            try:
                self._redis_client = Redis(
                    host=GCONF.REDISHOST,
                    port=GCONF.REDISPORT,
                    db=0,
                    decode_responses=True
                )
            except Exception as e:
                print(f"[WARN] Failed to create Redis client: {e}")
        return self._redis_client

    def _get_heartbeat_key(self) -> str:
        """获取心跳Redis Key"""
        return f"heartbeat:task_timer:{self.node_id}"

    def _start_heartbeat_thread(self):
        """启动心跳上报线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            print("[WARN] Heartbeat thread already running")
            return

        # 清理旧的心跳数据
        self._cleanup_old_heartbeat_data()

        # 立即发送一次心跳
        self._send_heartbeat()

        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name=f"heartbeat_{self.node_id}"
        )
        self.heartbeat_thread.start()
        print(f"[INFO] Heartbeat thread started for {self.node_id}")

    def _heartbeat_loop(self):
        """心跳上报循环"""
        while self.is_running:
            try:
                self._send_heartbeat()

                # 等待下一次心跳
                for _ in range(self.HEARTBEAT_INTERVAL):
                    if not self.is_running:
                        break
                    time.sleep(1)

            except Exception as e:
                print(f"[ERROR] Error in heartbeat loop: {e}")
                time.sleep(5)

        print("[INFO] Heartbeat loop stopped")

    def _send_heartbeat(self):
        """发送心跳到Redis"""
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            heartbeat_key = self._get_heartbeat_key()

            # 构建心跳数据（支持微服务模式）
            import socket
            heartbeat_data = {
                "timestamp": datetime.now().isoformat(),
                "component_type": "task_timer",
                "component_id": self.node_id,
                "host": socket.gethostname(),
                "pid": os.getpid(),
                "jobs_count": len(self._jobs),
            }

            heartbeat_value = __import__('json').dumps(heartbeat_data)

            # 设置心跳并附带TTL
            redis_client.setex(
                heartbeat_key,
                self.HEARTBEAT_TTL,
                heartbeat_value
            )

        except Exception as e:
            print(f"[ERROR] Failed to send heartbeat: {e}")

    def _cleanup_old_heartbeat_data(self):
        """清理旧的心跳数据"""
        try:
            redis_client = self._get_redis_client()
            if not redis_client:
                return

            heartbeat_key = self._get_heartbeat_key()
            deleted = redis_client.delete(heartbeat_key)
            if deleted:
                print(f"[INFO] Cleaned up old heartbeat data")

        except Exception as e:
            print(f"[WARN] Failed to cleanup old heartbeat data: {e}")

    def get_jobs_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有任务状态

        Returns:
            Dict: 任务状态字典，包含下次执行时间等信息
        """
        jobs = self.scheduler.get_jobs()
        status = {}

        for job in jobs:
            status[job.name] = {
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }

        return status

    def start(self) -> bool:
        """
        启动TaskTimer

        Returns:
            bool: 启动是否成功
        """
        try:
            print("[INFO] TaskTimer starting...")

            self.is_running = True

            # 初始化Kafka Producer
            self._producer = GinkgoProducer()

            # 加载配置
            self._load_config()

            # 添加定时任务
            self._add_jobs()

            # 启动调度器
            self.scheduler.start()

            # 启动心跳线程
            self._start_heartbeat_thread()

            print(f"[INFO] TaskTimer started with {len(self._jobs)} jobs")

            # 发送启动通知
            try:
                from ginkgo.notifier.core.notification_service import notify_with_fields

                # 构建任务字段列表
                scheduled_tasks = self._config.get("scheduled_tasks", [])
                task_fields = [
                    {"name": "节点ID", "value": self.node_id, "inline": True},
                    {"name": "任务数量", "value": str(len(self._jobs)), "inline": True},
                    {"name": "启动时间", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
                ]

                # 添加每个任务的字段
                for task in scheduled_tasks:
                    status = "✓ 启用" if task.get("enabled", True) else "✗ 禁用"
                    task_fields.append({
                        "name": task['name'],
                        "value": f"{task['cron']} - {status}",
                        "inline": False
                    })

                notify_with_fields(
                    content="TaskTimer启动成功",
                    title="TaskTimer",
                    level="INFO",
                    module="TaskTimer",
                    fields=task_fields
                )
            except Exception as notify_error:
                print(f"[WARN] Failed to send start notification: {notify_error}")

            return True

        except Exception as e:
            print(f"[ERROR] TaskTimer start failed: {e}")
            self.is_running = False

            # 发送失败通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"TaskTimer启动失败: {e}",
                    level="ERROR",
                    module="TaskTimer",
                    details={
                        "节点ID": self.node_id,
                        "错误信息": str(e),
                    },
                )
            except Exception:
                pass

            return False

    def stop(self) -> bool:
        """
        停止TaskTimer

        Returns:
            bool: 停止是否成功
        """
        try:
            print("[INFO] TaskTimer stopping...")

            # 设置停止标志
            self.is_running = False

            # 停止调度器
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)

            # 等待心跳线程退出
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=5)
                if not self.heartbeat_thread.is_alive():
                    print("[INFO] Heartbeat thread stopped")
                else:
                    print("[WARN] Heartbeat thread did not stop in time")

            # 关闭Kafka Producer
            if self._producer:
                self._producer.close()

            # 关闭Redis连接
            if self._redis_client:
                self._redis_client.close()

            print("[INFO] TaskTimer stopped")

            # 发送停止通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    "TaskTimer已停止",
                    level="INFO",
                    module="TaskTimer",
                    details={
                        "节点ID": self.node_id,
                        "停止时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "运行任务数": len(self._jobs),
                    },
                )
            except Exception as notify_error:
                print(f"[WARN] Failed to send stop notification: {notify_error}")

            return True

        except Exception as e:
            print(f"[ERROR] TaskTimer stop failed: {e}")

            # 发送失败通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"TaskTimer停止失败: {e}",
                    level="ERROR",
                    module="TaskTimer",
                    details={
                        "节点ID": self.node_id,
                        "错误信息": str(e),
                    },
                )
            except Exception:
                pass

            return False

    def reload_config(self) -> bool:
        """
        热重载配置文件

        重新加载配置文件并更新定时任务，无需重启 TaskTimer。

        Returns:
            bool: 重载是否成功

        使用方式:
            task_timer.reload_config()
        """
        old_jobs = list(self._jobs)  # 记录旧任务列表

        try:
            print("[INFO] Reloading TaskTimer configuration...")

            # 重新加载配置
            self._load_config()

            # 移除所有现有任务
            self.scheduler.remove_all_jobs()
            self._jobs.clear()
            print("[INFO] Removed all existing jobs")

            # 重新添加任务
            self._add_jobs()

            print(f"[INFO] Configuration reloaded successfully. Active jobs: {len(self._jobs)}")

            # 发送重载成功通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    "TaskTimer配置重载成功",
                    level="INFO",
                    module="TaskTimer",
                    details={
                        "节点ID": self.node_id,
                        "旧任务列表": old_jobs,
                        "新任务列表": self._jobs,
                        "任务数量变化": f"{len(old_jobs)} → {len(self._jobs)}",
                        "重载时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            except Exception as notify_error:
                print(f"[WARN] Failed to send reload notification: {notify_error}")

            return True

        except Exception as e:
            print(f"[ERROR] Failed to reload configuration: {e}")

            # 发送重载失败通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"TaskTimer配置重载失败: {e}",
                    level="ERROR",
                    module="TaskTimer",
                    details={
                        "节点ID": self.node_id,
                        "错误信息": str(e),
                    },
                )
            except Exception:
                pass

            return False

    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                print(f"[WARN] Config file not found: {self.config_path}, using defaults")
                self._config = self._get_default_config()
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)

            print(f"[INFO] Config loaded from {self.config_path}")

        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "scheduled_tasks": [
                {
                    "name": "heartbeat_test",
                    "cron": "0 0 * * *",  # 每天 00:00
                    "command": "heartbeat_test",
                    "enabled": True,
                },
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
                    print(f"[WARN] Invalid task config: {task_config}")
                    continue

                # 解析cron表达式
                cron_parts = cron_expr.split()
                if len(cron_parts) != 5:
                    print(f"[WARN] Invalid cron expression: {cron_expr}")
                    continue

                # 创建CronTrigger
                trigger = CronTrigger(
                    minute=cron_parts[0],
                    hour=cron_parts[1],
                    day=cron_parts[2],
                    month=cron_parts[3],
                    day_of_week=cron_parts[4],
                    timezone='Asia/Shanghai',
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
                    print(f"[INFO] Added job: {job_name} ({cron_expr})")
                else:
                    # command不存在，记录警告日志
                    print(f"[WARN] Unknown command '{command}' for task '{job_name}', job not registered")
                    print(f"[WARN] Valid commands are: {', '.join(self._get_valid_commands())}")

        except Exception as e:
            print(f"[ERROR] Failed to add jobs: {e}")

    def _get_job_function(self, command: str) -> Optional[callable]:
        """
        获取任务函数

        Args:
            command: 命令类型

        Returns:
            任务函数
        """
        job_functions = {
            "stockinfo": self._stockinfo_job,
            "adjustfactor": self._adjustfactor_job,
            "bar_snapshot": self._bar_snapshot_job,
            "tick": self._tick_job,
            "update_selector": self._selector_update_job,
            "update_data": self._data_update_job,
            "heartbeat_test": self._heartbeat_test_job,
        }

        return job_functions.get(command)

    def _get_valid_commands(self) -> List[str]:
        """获取有效的命令列表"""
        return ["stockinfo", "adjustfactor", "bar_snapshot", "tick", "update_selector", "update_data", "heartbeat_test"]

    @safe_job_wrapper
    def _stockinfo_job(self) -> None:
        """
        股票信息更新任务（21:00触发）

        发送stockinfo命令到Kafka（ginkgo.data.commands），
        DataWorker接收后更新所有股票的基本信息。
        """
        try:
            # stockinfo 不需要指定 code，会同步所有股票
            command_dto = ControlCommandDTO(
                command=ControlCommandDTO.Commands.STOCKINFO,
                params={},
                source="task_timer"
            )

            # 直接发送到 ginkgo.data.commands
            self._publish_to_data_commands(command_dto.model_dump_json())
            print("[INFO] Sent stockinfo command to DataWorker")

            # 发送Discord通知
            self._send_notification("股票信息更新命令已发送", "STOCKINFO")

        except Exception as e:
            print(f"[ERROR] Stockinfo job failed: {e}")
            self._send_error_notification("股票信息更新任务执行失败", e)

    @safe_job_wrapper
    def _adjustfactor_job(self) -> None:
        """
        复权因子更新任务（21:05触发）

        获取所有股票代码，批量发送adjustfactor命令到Kafka（ginkgo.data.commands），
        DataWorker接收后批量更新复权因子数据。
        """
        try:
            # 获取所有股票代码
            stock_codes = self._get_all_stock_codes()

            if not stock_codes:
                print("[WARN] No stocks found, skipping adjustfactor update")
                return

            total = len(stock_codes)
            print(f"[INFO] Sending adjustfactor commands for {total} stocks")

            # 批量发送命令（batch_size=100）
            self._send_batch_commands("adjustfactor", stock_codes, batch_size=100)

            print(f"[INFO] Completed adjustfactor update for {total} stocks")
            self._send_notification(f"复权因子更新完成，共 {total} 只股票", "ADJUSTFACTOR")

        except Exception as e:
            print(f"[ERROR] Adjustfactor job failed: {e}")
            self._send_error_notification("复权因子更新任务执行失败", e)

    @safe_job_wrapper
    def _bar_snapshot_job(self) -> None:
        """
        K线数据更新任务（21:10触发）

        获取所有股票代码，批量发送bar_snapshot命令到Kafka（ginkgo.data.commands），
        DataWorker接收后批量更新日K线数据。
        """
        try:
            # 获取所有股票代码
            stock_codes = self._get_all_stock_codes()

            if not stock_codes:
                print("[WARN] No stocks found, skipping bar_snapshot update")
                return

            total = len(stock_codes)
            print(f"[INFO] Sending bar_snapshot commands for {total} stocks")

            # 批量发送命令（batch_size=50，默认参数：当日K线，不强制覆盖）
            payload = {"full": False, "force": False}
            self._send_batch_commands("bar_snapshot", stock_codes, batch_size=50, payload=payload)

            print(f"[INFO] Completed bar_snapshot update for {total} stocks")
            self._send_notification(f"K线数据更新完成，共 {total} 只股票", "BAR_SNAPSHOT")

        except Exception as e:
            print(f"[ERROR] Bar snapshot job failed: {e}")
            self._send_error_notification("K线数据更新任务执行失败", e)

    @safe_job_wrapper
    def _tick_job(self) -> None:
        """
        Tick数据更新任务（21:15触发，可选）

        获取所有股票代码，批量发送tick命令到Kafka（ginkgo.data.commands），
        DataWorker接收后批量更新tick数据（耗时较长）。
        """
        try:
            # 获取所有股票代码
            stock_codes = self._get_all_stock_codes()

            if not stock_codes:
                print("[WARN] No stocks found, skipping tick update")
                return

            total = len(stock_codes)
            print(f"[INFO] Sending tick commands for {total} stocks (this may take a while)")

            # 批量发送命令（batch_size=10，默认参数：增量同步，不强制覆盖）
            payload = {"full": False, "overwrite": False}
            self._send_batch_commands("tick", stock_codes, batch_size=10, payload=payload)

            print(f"[INFO] Completed tick update for {total} stocks")
            self._send_notification(f"Tick数据更新完成，共 {total} 只股票", "TICK")

        except Exception as e:
            print(f"[ERROR] Tick job failed: {e}")
            self._send_error_notification("Tick数据更新任务执行失败", e)

    @safe_job_wrapper
    def _adjustfactor_job(self) -> None:
        """
        复权因子更新任务（21:05触发）

        发送adjustfactor控制命令到Kafka，
        DataManager接收后向DataWorker发送adjustfactor命令，
        批量更新所有股票的复权因子数据。
        """
        try:
            command_dto = ControlCommandDTO(
                command=ControlCommandDTO.Commands.ADJUSTFACTOR,
                params={"timestamp": datetime.now().isoformat()},
            )

            # 发布到Kafka（带重试）
            self._publish_to_kafka(command_dto.model_dump_json())
            print("[INFO] Sent adjustfactor command to Kafka")

            # 发送Discord通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    "复权因子更新命令已发送",
                    level="INFO",
                    module="TaskTimer",
                    details={
                        "命令": "ADJUSTFACTOR",
                        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            except Exception as notify_error:
                print(f"[WARN] Failed to send notification: {notify_error}")

        except Exception as e:
            print(f"[ERROR] Adjustfactor job failed: {e}")
            # 发送错误通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"复权因子更新任务执行失败: {e}",
                    level="ERROR",
                    module="TaskTimer",
                )
            except Exception:
                pass

    @safe_job_wrapper
    def _tick_job(self) -> None:
        """
        Tick数据更新任务（21:15触发，可选）

        发送tick控制命令到Kafka，
        DataManager接收后向DataWorker发送tick命令，
        批量更新所有股票的tick数据（耗时较长）。
        """
        try:
            command_dto = ControlCommandDTO(
                command=ControlCommandDTO.Commands.TICK,
                params={"timestamp": datetime.now().isoformat()},
            )

            # 发布到Kafka（带重试）
            self._publish_to_kafka(command_dto.model_dump_json())
            print("[INFO] Sent tick command to Kafka")

            # 发送Discord通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    "Tick数据更新命令已发送（预计耗时较长）",
                    level="INFO",
                    module="TaskTimer",
                    details={
                        "命令": "TICK",
                        "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            except Exception as notify_error:
                print(f"[WARN] Failed to send notification: {notify_error}")

        except Exception as e:
            print(f"[ERROR] Tick job failed: {e}")
            # 发送错误通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"Tick数据更新任务执行失败: {e}",
                    level="ERROR",
                    module="TaskTimer",
                )
            except Exception:
                pass

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
                params={},
                source="task_timer"
            )

            # 发布到Kafka（带重试）
            self._publish_to_kafka(command_dto.model_dump_json())
            print("[INFO] Sent update_selector command to Kafka")
            self._send_notification("Selector更新命令已发送", "UPDATE_SELECTOR")

        except Exception as e:
            print(f"[ERROR] Selector update job failed: {e}")
            self._send_error_notification("Selector更新任务执行失败", e)

    @safe_job_wrapper
    def _data_update_job(self) -> None:
        """
        数据更新任务（已弃用）

        注意：此命令已弃用，请使用独立的 stockinfo/adjustfactor/bar_snapshot/tick 命令。
        """
        print("[WARN] _data_update_job is deprecated, use individual commands instead")

    @safe_job_wrapper
    def _heartbeat_test_job(self) -> None:
        """
        心跳测试任务（每天00:00触发）

        用于验证TaskTimer正常运行的测试任务，仅发送Discord通知。
        """
        try:
            # 发送Discord通知
            from ginkgo.notifier.core.notification_service import notify
            notify(
                "TaskTimer心跳测试 - TaskTimer运行正常",
                level="INFO",
                module="TaskTimer",
                details={
                    "测试任务": "HEARTBEAT_TEST",
                    "节点ID": self.node_id,
                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "运行中任务数": len(self._jobs),
                },
            )
            print("[INFO] Heartbeat test notification sent")

        except Exception as e:
            print(f"[ERROR] Heartbeat test job failed: {e}")
            self._send_error_notification("心跳测试任务执行失败", e)

    def _get_all_stock_codes(self) -> list:
        """
        获取所有股票代码列表

        Returns:
            股票代码列表
        """
        try:
            from ginkgo import service_hub

            stockinfo_service = service_hub.data.stockinfo_service
            stocks = stockinfo_service.get_stockinfos()

            if not stocks:
                return []

            return [stock.code for stock in stocks]

        except Exception as e:
            print(f"[ERROR] Failed to get stock codes: {e}")
            return []

    def _send_batch_commands(self, command: str, codes: list, batch_size: int = 50,
                           payload: dict = None) -> None:
        """
        批量发送命令到 DataWorker

        Args:
            command: 命令类型
            codes: 股票代码列表
            batch_size: 每批次处理的股票数量
            payload: 额外的命令参数
        """
        try:
            payload = payload or {}
            total = len(codes)
            processed = 0

            while processed < total:
                # 获取当前批次
                batch = codes[processed:processed + batch_size]

                # 为每个股票发送命令
                for code in batch:
                    cmd_payload = {**payload, "code": code}
                    command_dto = ControlCommandDTO(
                        command=command,
                        params=cmd_payload,
                        source="task_timer"
                    )
                    self._publish_to_data_commands(command_dto.model_dump_json())

                processed += len(batch)
                print(f"[INFO] Progress: {processed}/{total} ({processed*100//total}%)")

                # 短暂延迟，避免 Kafka 压力过大
                import time
                time.sleep(0.1)

        except Exception as e:
            print(f"[ERROR] Failed to send batch {command} commands: {e}")

    def _publish_to_data_commands(self, message: str) -> None:
        """
        发布命令到 ginkgo.data.commands topic（带重试）

        Args:
            message: JSON格式的命令
        """
        if self._producer:
            try:
                self._producer.send(
                    topic=KafkaTopics.DATA_COMMANDS,
                    msg=message,
                )
            except Exception as e:
                print(f"[ERROR] Failed to publish to data.commands: {e}")

    def _send_notification(self, message: str, command_name: str) -> None:
        """
        发送Discord通知

        Args:
            message: 通知消息
            command_name: 命令名称
        """
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                message,
                level="INFO",
                module="TaskTimer",
                details={
                    "命令": command_name,
                    "时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
        except Exception as e:
            print(f"[WARN] Failed to send notification: {e}")

    def _send_error_notification(self, message: str, error: Exception) -> None:
        """
        发送错误通知

        Args:
            message: 错误消息
            error: 异常对象
        """
        try:
            from ginkgo.notifier.core.notification_service import notify
            notify(
                message,
                level="ERROR",
                module="TaskTimer",
                details={
                    "错误": str(error),
                },
            )
        except Exception:
            pass

    def validate_config(self) -> bool:
        """
        验证配置文件

        Returns:
            bool: 配置是否有效
        """
        try:
            if not os.path.exists(self.config_path):
                print(f"[ERROR] Config file not found: {self.config_path}")
                return False

            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            # 验证scheduled_tasks
            scheduled_tasks = config.get("scheduled_tasks", [])
            if not isinstance(scheduled_tasks, list):
                print("[ERROR] scheduled_tasks must be a list")
                return False

            for task in scheduled_tasks:
                # 验证必需字段
                if "name" not in task or "cron" not in task or "command" not in task:
                    print(f"[ERROR] Task missing required fields: {task}")
                    return False

                # 验证命令类型
                if task["command"] not in self._get_valid_commands():
                    print(f"[ERROR] Invalid command: {task['command']}")
                    return False

            print("[INFO] Config validation passed")
            return True

        except Exception as e:
            print(f"[ERROR] Config validation failed: {e}")
            return False

    @retry(max_try=3, backoff_factor=2)
    def _publish_to_kafka(self, message: str) -> None:
        """
        发布控制命令到Kafka（带重试）

        根据命令类型自动路由到正确的 topic：
        - 数据采集命令 (bar_snapshot, stockinfo, adjustfactor, tick) → ginkgo.data.commands
        - 其他控制命令 → ginkgo.live.control.commands

        Args:
            message: JSON格式的控制命令
        """
        if self._producer:
            # 解析消息判断命令类型
            try:
                import json
                message_data = json.loads(message)
                command = message_data.get("command", "")

                # 数据采集命令发送到专用 topic
                if command in ("bar_snapshot", "stockinfo", "adjustfactor", "tick"):
                    topic = KafkaTopics.DATA_COMMANDS
                else:
                    topic = KafkaTopics.CONTROL_COMMANDS

                self._producer.send(
                    topic=topic,
                    msg=message,
                )
            except json.JSONDecodeError:
                # 如果解析失败，发送到默认 topic
                self._producer.send(
                    topic=KafkaTopics.CONTROL_COMMANDS,
                    msg=message,
                )
