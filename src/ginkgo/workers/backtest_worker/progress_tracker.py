# Upstream: BacktestProcessor (任务执行中上报进度)
# Downstream: Kafka (BACKTEST_PROGRESS topic), BacktestTaskService (数据库)
# Role: 回测任务进度跟踪和上报(Kafka+DB+SSE通知)

"""
Progress Tracker

进度跟踪和上报器（对应ExecutionNode的backpressure.py）

职责：
- 跟踪任务进度
- 上报进度到Kafka（每2秒 + 关键节点）
- 写入进度到数据库（用于SSE实时推送）
- 记录重要阶段变化
"""

from threading import Lock
from time import time
from typing import Dict, Optional

from ginkgo.libs import GLOG
from ginkgo.workers.backtest_worker.models import BacktestTask, EngineStage
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.data.services.base_service import ServiceResult


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, worker_id: str, kafka_producer: GinkgoProducer, task_service=None):
        GLOG.set_log_category("component")
        self.worker_id = worker_id
        self.producer = kafka_producer
        self.task_service = task_service  # BacktestTaskService 实例
        self.lock = Lock()

        # 上报频率控制
        self.report_interval = 2.0  # 每2秒
        self.last_report_time: Dict[str, float] = {}

    def report_progress(
        self,
        task: BacktestTask,
        progress: float,
        current_date: str,
        total_pnl: str = "0",
        total_orders: int = 0,
        total_signals: int = 0,
    ):
        """上报进度（频率限制）"""
        with self.lock:
            now = time()
            last_time = self.last_report_time.get(task.task_uuid, 0)

            # 检查是否需要上报
            if now - last_time < self.report_interval:
                return

            self.last_report_time[task.task_uuid] = now

        # 发送到Kafka
        self._send_to_kafka(
            {
                "type": "progress",
                "task_uuid": task.task_uuid,
                "worker_id": self.worker_id,
                "progress": progress,
                "current_date": current_date,
                "state": task.state.value,
                "timestamp": task.started_at.isoformat() if task.started_at else None,
            }
        )

        # 同时写入数据库（用于SSE推送）
        self._write_progress_to_db(
            task.task_uuid,
            progress=progress,
            current_date=current_date,
            total_pnl=total_pnl,
            total_orders=total_orders,
            total_signals=total_signals,
        )

    def report_stage(self, task: BacktestTask, stage: EngineStage, message: str):
        """上报关键阶段（立即上报）"""
        self._send_to_kafka(
            {
                "type": "stage",
                "task_uuid": task.task_uuid,
                "worker_id": self.worker_id,
                "stage": stage.value,
                "message": message,
                "state": task.state.value,
                "timestamp": task.started_at.isoformat() if task.started_at else None,
            }
        )
        GLOG.INFO(f"[{task.task_uuid[:8]}] Stage: {stage.value} - {message}")

        # 第一个阶段时，更新状态为 running 并设置 start_time
        if stage == EngineStage.DATA_PREPARING:
            self._write_status_to_db(task.task_uuid, "running", current_stage=stage.value)
        else:
            # 其他阶段只更新 current_stage
            self._write_progress_to_db(task.task_uuid, current_stage=stage.value)

    def report_completed(self, task: BacktestTask, result: dict) -> ServiceResult:
        """上报完成。#6845: 返回状态回写结果，调用方据此 WARN 告警（不再 fire-and-forget 撒谎）。"""
        self._send_to_kafka(
            {
                "type": "completed",
                "task_uuid": task.task_uuid,
                "worker_id": self.worker_id,
                "result": result,
                "timestamp": task.completed_at.isoformat() if task.completed_at else None,
            }
        )
        GLOG.INFO(f"[{task.task_uuid[:8]}] Reported completion")

        # 更新数据库状态为 completed（传播结果供调用方判定）
        return self._write_status_to_db(task.task_uuid, "completed", result=result)

    def report_failed(self, task: BacktestTask, error: str) -> ServiceResult:
        """上报失败。#6845: 返回状态回写结果（DB 写失败时调用方可感知）。"""
        self._send_to_kafka(
            {
                "type": "failed",
                "task_uuid": task.task_uuid,
                "worker_id": self.worker_id,
                "error": error,
                "timestamp": task.completed_at.isoformat() if task.completed_at else None,
            }
        )
        GLOG.ERROR(f"[{task.task_uuid[:8]}] Reported failure: {error}")

        # 更新数据库状态为 failed（传播结果供调用方判定）
        return self._write_status_to_db(task.task_uuid, "failed", error_message=error)

    def report_cancelled(self, task: BacktestTask) -> ServiceResult:
        """上报取消。#6845: 返回状态回写结果。"""
        self._send_to_kafka(
            {
                "type": "cancelled",
                "task_uuid": task.task_uuid,
                "worker_id": self.worker_id,
                "timestamp": task.completed_at.isoformat() if task.completed_at else None,
            }
        )
        GLOG.INFO(f"[{task.task_uuid[:8]}] Reported cancellation")

        # 更新数据库状态为 stopped（传播结果供调用方判定）
        return self._write_status_to_db(task.task_uuid, "stopped")

    def report_failed_by_uuid(self, task_uuid: str, error: str) -> ServiceResult:
        """通过 UUID 上报失败（无需完整 BacktestTask 对象）。#6845: 返回状态回写结果。"""
        short_uuid = task_uuid[:8] if task_uuid else "unknown"
        self._send_to_kafka(
            {
                "type": "failed",
                "task_uuid": task_uuid,
                "worker_id": self.worker_id,
                "error": error,
                "timestamp": None,
            }
        )
        GLOG.ERROR(f"[{short_uuid}] Reported failure by UUID: {error}")

        # 更新数据库状态为 failed（传播结果供调用方判定）
        return self._write_status_to_db(task_uuid, "failed", error_message=error)

    def _send_to_kafka(self, message: dict):
        """发送消息到Kafka"""
        try:
            import json

            self.producer.send_async(
                topic=KafkaTopics.BACKTEST_PROGRESS,
                msg=json.dumps(message),
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to report progress: {e}")

    def _write_progress_to_db(
        self,
        task_id: str,
        progress: float = None,
        current_stage: str = None,
        current_date: str = None,
        total_pnl: str = "0",
        total_orders: int = 0,
        total_signals: int = 0,
    ):
        """写入进度到数据库（用于SSE推送）。

        刻意保持 fire-and-forget（与 _write_status_to_db 不同）：进度写入是瞬态
        SSE 订阅流，丢一次只会让前端进度卡 2s，不会导致任务状态分歧（终态 status
        写在 _write_status_to_db，那里才须诚实传播失败）。
        """
        if self.task_service is None:
            return

        try:
            result = self.task_service.update_progress(
                uuid=task_id,  # task_id 与 uuid 等价
                progress=progress,
                current_stage=current_stage,
                current_date=current_date,
            )
            if not result.success:
                GLOG.ERROR(f"Failed to write progress to DB: {result.message}")
        except Exception as e:
            GLOG.ERROR(f"Error writing progress to DB: {e}")

    def _write_status_to_db(
        self, task_id: str, status: str, error_message: str = "", result: dict = None, current_stage: str = None
    ) -> ServiceResult:
        """写入任务状态到数据库。

        #6845: 状态回写失败必须可见——不再撒谎。返回 ServiceResult 供调用方判定：
        - 成功：success
        - 任务不存在（update_status code=NOT_FOUND）：success（预期容许，任务可能未预先创建）
        - DB 写失败 / 异常：failure（真故障，调用方须 WARN 告警）
        """
        if self.task_service is None:
            return ServiceResult.success(message="task_service not configured, status write skipped")

        try:
            from datetime import datetime

            # 构建结果字段
            result_fields = {}

            # 状态为 running 时，设置 start_time 和 current_stage
            if status == "running":
                result_fields["start_time"] = datetime.now()
                if current_stage:
                    result_fields["current_stage"] = current_stage

            # 完成状态时，设置结果字段和进度 100%
            if status == "completed":
                result_fields["progress"] = 100
                # ADR-016 铁律 2: 回测完成回写 engine_id = task_uuid（task_id 与 uuid 等价），
                # 维持 engine_id ≡ task_id 不变量。baseline 管线 / get_tasks_by_engine 等依赖此列非空。
                result_fields["engine_id"] = task_id
            if result:
                result_fields.update(
                    {
                        "total_pnl": result.get("total_pnl", 0.0),
                        "total_orders": result.get("total_orders", 0),
                        "total_signals": result.get("total_signals", 0),
                        "total_positions": result.get("total_positions", 0),
                        "total_events": result.get("total_events", 0),
                        "final_portfolio_value": result.get("final_portfolio_value", 0.0),
                        "max_drawdown": result.get("max_drawdown", 0.0),
                        "sharpe_ratio": result.get("sharpe_ratio", 0.0),
                        "annual_return": result.get("annual_return", 0.0),
                        "win_rate": result.get("win_rate", 0.0),
                    }
                )

            result_obj = self.task_service.update_status(
                uuid=task_id, status=status, error_message=error_message, **result_fields  # task_id 与 uuid 等价
            )
            if not result_obj.is_success():
                # #6845: 区分"任务不存在"(容许) vs "DB 写失败"(真故障)。
                # 任务可能未预先创建（aggregator 路径），not-found 不算故障，避免假告警。
                if result_obj.code == "NOT_FOUND":
                    GLOG.INFO(f"Task {task_id[:8]}... not found, status write skipped (tolerable)")
                    return ServiceResult.success()
                GLOG.ERROR(f"Failed to write status to DB: {result_obj.message}")
                return ServiceResult.error(f"Failed to write status to DB: {result_obj.message}")
            return ServiceResult.success(result_obj.data, f"Status {status} written for {task_id[:8]}...")
        except Exception as e:
            GLOG.ERROR(f"Error writing status to DB: {e}")
            return ServiceResult.error(f"Error writing status to DB: {e}")

    def get_task_status(self, task_uuid: str) -> Optional[str]:
        """
        查询任务当前状态

        Args:
            task_uuid: 任务UUID (实际是 task_id)

        Returns:
            Optional[str]: 任务状态 (completed/failed/running/pending/created)，如果查询失败返回 None
        """
        if self.task_service is None:
            return None

        try:
            # 使用 get_by_id 而不是 get，因为 get_by_id 更可靠（先尝试 uuid，再尝试 task_id）
            result = self.task_service.get_by_id(task_uuid)
            if result.is_success() and result.data:
                # result.data 是单个 MBacktestTask 对象
                task_obj = result.data

                # 尝试获取 status 属性
                if hasattr(task_obj, "status"):
                    # status 可能是枚举类型，转换为字符串
                    status = task_obj.status
                    return str(status) if not hasattr(status, "value") else str(status.value)
                elif hasattr(task_obj, "get"):
                    return task_obj.get("status")
            return None
        except Exception as e:
            GLOG.ERROR(f"Error getting task status for {task_uuid[:8]}: {e}")
            return None
