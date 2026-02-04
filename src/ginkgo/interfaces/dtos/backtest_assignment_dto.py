"""
Backtest Assignment DTO

回测任务分配消息（API/Scheduler → BacktestWorker）
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class BacktestAssignmentDTO:
    """回测任务分配消息"""

    command: str  # "start" or "cancel"
    task_uuid: str
    portfolio_uuid: str
    name: str
    config: Dict[str, Any]

    # 可选字段
    priority: int = 0  # 优先级
    timeout: Optional[int] = None  # 超时时间（秒）

    def to_json(self) -> str:
        """转换为JSON"""
        import json
        return json.dumps({
            "command": self.command,
            "task_uuid": self.task_uuid,
            "portfolio_uuid": self.portfolio_uuid,
            "name": self.name,
            "config": self.config,
            "priority": self.priority,
            "timeout": self.timeout,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "BacktestAssignmentDTO":
        """从JSON创建"""
        import json
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class BacktestProgressDTO:
    """回测进度消息（BacktestWorker → API）"""

    type: str  # "progress", "stage", "completed", "failed", "cancelled"
    task_uuid: str
    worker_id: str

    # 进度信息
    progress: Optional[float] = None
    current_date: Optional[str] = None
    state: Optional[str] = None

    # 阶段信息
    stage: Optional[str] = None
    message: Optional[str] = None

    # 结果/错误
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    timestamp: Optional[str] = None

    def to_json(self) -> str:
        """转换为JSON"""
        import json
        data = {
            "type": self.type,
            "task_uuid": self.task_uuid,
            "worker_id": self.worker_id,
        }
        if self.progress is not None:
            data["progress"] = self.progress
        if self.current_date:
            data["current_date"] = self.current_date
        if self.state:
            data["state"] = self.state
        if self.stage:
            data["stage"] = self.stage
        if self.message:
            data["message"] = self.message
        if self.result:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        if self.timestamp:
            data["timestamp"] = self.timestamp
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> "BacktestProgressDTO":
        """从JSON创建"""
        import json
        data = json.loads(json_str)
        return cls(**data)
