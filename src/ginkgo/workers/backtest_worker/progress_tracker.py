"""
Progress Tracker

进度跟踪和上报器（对应ExecutionNode的backpressure.py）

职责：
- 跟踪任务进度
- 上报进度到Kafka（每2秒 + 关键节点）
- 记录重要阶段变化
"""

from threading import Lock
from time import time
from typing import Dict

from ginkgo.workers.backtest_worker.models import BacktestTask, EngineStage
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
# GLOG removed


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, worker_id: str, kafka_producer: GinkgoProducer):
        self.worker_id = worker_id
        self.producer = kafka_producer
        self.lock = Lock()

        # 上报频率控制
        self.report_interval = 2.0  # 每2秒
        self.last_report_time: Dict[str, float] = {}

    def report_progress(self, task: BacktestTask, progress: float, current_date: str):
        """上报进度（频率限制）"""
        with self.lock:
            now = time()
            last_time = self.last_report_time.get(task.task_uuid, 0)

            # 检查是否需要上报
            if now - last_time < self.report_interval:
                return

            self.last_report_time[task.task_uuid] = now

        # 发送到Kafka
        self._send_to_kafka({
            "type": "progress",
            "task_uuid": task.task_uuid,
            "worker_id": self.worker_id,
            "progress": progress,
            "current_date": current_date,
            "state": task.state.value,
            "timestamp": task.started_at.isoformat() if task.started_at else None,
        })

    def report_stage(self, task: BacktestTask, stage: EngineStage, message: str):
        """上报关键阶段（立即上报）"""
        self._send_to_kafka({
            "type": "stage",
            "task_uuid": task.task_uuid,
            "worker_id": self.worker_id,
            "stage": stage.value,
            "message": message,
            "state": task.state.value,
            "timestamp": task.started_at.isoformat() if task.started_at else None,
        })
        print(f"[{task.task_uuid[:8]}] Stage: {stage.value} - {message}")

    def report_completed(self, task: BacktestTask, result: dict):
        """上报完成"""
        self._send_to_kafka({
            "type": "completed",
            "task_uuid": task.task_uuid,
            "worker_id": self.worker_id,
            "result": result,
            "timestamp": task.completed_at.isoformat() if task.completed_at else None,
        })
        print(f"[{task.task_uuid[:8]}] Reported completion")

    def report_failed(self, task: BacktestTask, error: str):
        """上报失败"""
        self._send_to_kafka({
            "type": "failed",
            "task_uuid": task.task_uuid,
            "worker_id": self.worker_id,
            "error": error,
            "timestamp": task.completed_at.isoformat() if task.completed_at else None,
        })
        print(f"[{task.task_uuid[:8]}] Reported failure: {error}")

    def report_cancelled(self, task: BacktestTask):
        """上报取消"""
        self._send_to_kafka({
            "type": "cancelled",
            "task_uuid": task.task_uuid,
            "worker_id": self.worker_id,
            "timestamp": task.completed_at.isoformat() if task.completed_at else None,
        })
        print(f"[{task.task_uuid[:8]}] Reported cancellation")

    def _send_to_kafka(self, message: dict):
        """发送消息到Kafka"""
        try:
            import json
            self.producer.produce(
                topic="backtest.progress",
                key=message.get("task_uuid"),
                value=json.dumps(message),
            )
            self.producer.flush(timeout=1.0)
        except Exception as e:
            print(f"Failed to report progress: {e}")
