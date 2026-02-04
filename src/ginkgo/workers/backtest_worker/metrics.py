"""
Backtest Worker Metrics

指标收集器（对应ExecutionNode的metrics.py）

职责：
- 收集Worker运行指标
- 收集任务执行统计
- 提供查询接口
"""

from threading import Lock
from time import time
from typing import Dict
from datetime import datetime


class BacktestMetrics:
    """回测Worker指标"""

    def __init__(self):
        self.lock = Lock()

        # Worker指标
        self.started_at: float = time()
        self.total_tasks_processed = 0
        self.total_tasks_failed = 0
        self.total_tasks_cancelled = 0

        # 当前运行的任务
        self.running_tasks: Dict[str, dict] = {}

    def record_task_start(self, task_uuid: str, task_name: str):
        """记录任务开始"""
        with self.lock:
            self.running_tasks[task_uuid] = {
                "name": task_name,
                "started_at": time(),
                "state": "RUNNING",
            }

    def record_task_complete(self, task_uuid: str, success: bool):
        """记录任务完成"""
        with self.lock:
            if task_uuid in self.running_tasks:
                del self.running_tasks[task_uuid]

            self.total_tasks_processed += 1
            if not success:
                self.total_tasks_failed += 1

    def record_task_cancelled(self, task_uuid: str):
        """记录任务取消"""
        with self.lock:
            if task_uuid in self.running_tasks:
                del self.running_tasks[task_uuid]

            self.total_tasks_cancelled += 1

    def get_metrics(self) -> dict:
        """获取指标"""
        with self.lock:
            uptime = time() - self.started_at

            return {
                # Worker信息
                "uptime_seconds": uptime,
                "started_at": datetime.fromtimestamp(self.started_at).isoformat(),

                # 任务统计
                "total_tasks_processed": self.total_tasks_processed,
                "total_tasks_failed": self.total_tasks_failed,
                "total_tasks_cancelled": self.total_tasks_cancelled,
                "running_tasks_count": len(self.running_tasks),

                # 成功率
                "success_rate": (
                    (self.total_tasks_processed - self.total_tasks_failed) / self.total_tasks_processed
                    if self.total_tasks_processed > 0
                    else 1.0
                ),

                # 运行中的任务
                "running_tasks": list(self.running_tasks.values()),
            }
