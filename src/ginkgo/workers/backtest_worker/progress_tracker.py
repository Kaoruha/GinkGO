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

from ginkgo.workers.backtest_worker.models import BacktestTask, EngineStage
from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, worker_id: str, kafka_producer: GinkgoProducer,
                 task_service=None):
        self.worker_id = worker_id
        self.producer = kafka_producer
        self.task_service = task_service  # BacktestTaskService 实例
        self.lock = Lock()

        # 上报频率控制
        self.report_interval = 2.0  # 每2秒
        self.last_report_time: Dict[str, float] = {}

    def report_progress(self, task: BacktestTask, progress: float, current_date: str,
                        total_pnl: str = "0", total_orders: int = 0, total_signals: int = 0):
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

        # 同时写入数据库（用于SSE推送）
        self._write_progress_to_db(
            task.task_uuid, progress=progress, current_date=current_date,
            total_pnl=total_pnl, total_orders=total_orders, total_signals=total_signals
        )

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

        # 第一个阶段时，更新状态为 running 并设置 start_time
        if stage == EngineStage.DATA_PREPARING:
            self._write_status_to_db(task.task_uuid, "running", current_stage=stage.value)
        else:
            # 其他阶段只更新 current_stage
            self._write_progress_to_db(task.task_uuid, current_stage=stage.value)

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

        # 更新数据库状态为 completed
        self._write_status_to_db(task.task_uuid, "completed", result=result)

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

        # 更新数据库状态为 failed
        self._write_status_to_db(task.task_uuid, "failed", error_message=error)

    def report_cancelled(self, task: BacktestTask):
        """上报取消"""
        self._send_to_kafka({
            "type": "cancelled",
            "task_uuid": task.task_uuid,
            "worker_id": self.worker_id,
            "timestamp": task.completed_at.isoformat() if task.completed_at else None,
        })
        print(f"[{task.task_uuid[:8]}] Reported cancellation")

        # 更新数据库状态为 stopped
        self._write_status_to_db(task.task_uuid, "stopped")

    def report_failed_by_uuid(self, task_uuid: str, error: str):
        """通过 UUID 上报失败（无需完整 BacktestTask 对象）"""
        short_uuid = task_uuid[:8] if task_uuid else "unknown"
        self._send_to_kafka({
            "type": "failed",
            "task_uuid": task_uuid,
            "worker_id": self.worker_id,
            "error": error,
            "timestamp": None,
        })
        print(f"[{short_uuid}] Reported failure by UUID: {error}")

        # 更新数据库状态为 failed
        self._write_status_to_db(task_uuid, "failed", error_message=error)

    def _send_to_kafka(self, message: dict):
        """发送消息到Kafka"""
        try:
            import json
            self.producer.send_async(
                topic="backtest.progress",
                msg=json.dumps(message),
            )
        except Exception as e:
            print(f"Failed to report progress: {e}")

    def _write_progress_to_db(self, task_id: str, progress: float = None,
                               current_stage: str = None, current_date: str = None,
                               total_pnl: str = "0", total_orders: int = 0, total_signals: int = 0):
        """写入进度到数据库（用于SSE推送）"""
        if self.task_service is None:
            return

        try:
            result = self.task_service.update_progress(
                uuid=task_id,  # task_id 与 uuid 等价
                progress=progress,
                current_stage=current_stage,
                current_date=current_date
            )
            if not result.success:
                print(f"Failed to write progress to DB: {result.message}")

            # 通知 WebSocket 客户端
            self._notify_ws_clients(
                task_id, "progress",
                progress=int(progress or 0),
                total_pnl=total_pnl, total_orders=total_orders, total_signals=total_signals
            )
        except Exception as e:
            print(f"Error writing progress to DB: {e}")

    def _notify_ws_clients(self, task_id: str, event_type: str = "progress", progress: int = 0,
                            total_pnl: str = "0", total_orders: int = 0, total_signals: int = 0):
        """通过 API 通知 WebSocket 客户端有更新"""
        try:
            import requests
            # 异步发送通知，不阻塞主流程
            requests.post(
                f"http://localhost:8000/api/v1/backtest/{task_id}/notify",
                params={
                    "event_type": event_type,
                    "progress": progress,
                    "total_pnl": total_pnl,
                    "total_orders": total_orders,
                    "total_signals": total_signals,
                },
                timeout=1  # 1秒超时
            )
        except Exception as e:
            # 通知失败不影响主流程
            pass

    def _write_status_to_db(self, task_id: str, status: str, error_message: str = "", result: dict = None,
                              current_stage: str = None):
        """写入任务状态到数据库"""
        if self.task_service is None:
            return

        try:
            from datetime import datetime

            # 构建结果字段
            result_fields = {}

            # 状态为 running 时，设置 start_time 和 current_stage
            if status == "running":
                result_fields["start_time"] = datetime.now()
                if current_stage:
                    result_fields["current_stage"] = current_stage

            # 完成状态时，设置结果字段
            if result:
                result_fields.update({
                    "total_pnl": str(result.get("total_pnl", "0")),
                    "total_orders": result.get("total_orders", 0),
                    "total_signals": result.get("total_signals", 0),
                    "total_positions": result.get("total_positions", 0),
                    "total_events": result.get("total_events", 0),
                    "final_portfolio_value": str(result.get("final_portfolio_value", "0")),
                    "max_drawdown": str(result.get("max_drawdown", "0")),
                    "sharpe_ratio": str(result.get("sharpe_ratio", "0")),
                    "annual_return": str(result.get("annual_return", "0")),
                    "win_rate": str(result.get("win_rate", "0")),
                })

            result_obj = self.task_service.update_status(
                uuid=task_id,  # task_id 与 uuid 等价
                status=status,
                error_message=error_message,
                **result_fields
            )
            if not result_obj.is_success():
                print(f"Failed to write status to DB: {result_obj.message}")

            # 通知 WebSocket 客户端状态变化
            if result:
                self._notify_ws_clients(
                    task_id, status,
                    progress=100,
                    total_pnl=str(result.get("total_pnl", "0")),
                    total_orders=result.get("total_orders", 0),
                    total_signals=result.get("total_signals", 0)
                )
            else:
                self._notify_ws_clients(task_id, status)
        except Exception as e:
            print(f"Error writing status to DB: {e}")

    def get_task_status(self, task_uuid: str) -> Optional[str]:
        """
        查询任务当前状态

        Args:
            task_uuid: 任务UUID

        Returns:
            Optional[str]: 任务状态 (completed/failed/running/pending/created)，如果查询失败返回 None
        """
        if self.task_service is None:
            return None

        try:
            result = self.task_service.get(task_uuid)
            if result.is_success() and result.data:
                # result.data 可能是 MBacktestTask 对象或列表
                if isinstance(result.data, list):
                    if len(result.data) > 0:
                        task_obj = result.data[0]
                    else:
                        return None
                else:
                    task_obj = result.data

                # 尝试获取 status 属性
                if hasattr(task_obj, 'status'):
                    # status 可能是枚举类型，转换为字符串
                    status = task_obj.status
                    return str(status) if not hasattr(status, 'value') else str(status.value)
                elif hasattr(task_obj, 'get'):
                    return task_obj.get("status")
            return None
        except Exception as e:
            print(f"Error getting task status for {task_uuid[:8]}: {e}")
            return None
