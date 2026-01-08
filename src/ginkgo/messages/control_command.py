# Upstream: API Gateway, CLI, Data模块 (发布控制命令)
# Downstream: ExecutionNode, LiveEngine (接收并执行控制命令)
# Role: ControlCommand控制命令消息，用于Kafka传输组件生命周期控制命令


"""
控制命令消息

用于通过Kafka传输组件生命周期控制命令，支持：
- Portfolio管理：create, delete, reload, start, stop
- Engine管理：start, stop

与Event的区别：
- 不继承EventBase，不参与事件驱动引擎
- 专注于Kafka消息传输（DTO模式）
- 轻量级，支持JSON序列化/反序列化
"""

import json
import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ControlCommand:
    """控制命令消息，用于Kafka传输

    支持的命令类型：
    - portfolio.create: 创建新Portfolio
    - portfolio.delete: 删除Portfolio
    - portfolio.reload: Portfolio配置更新（优雅重启）
    - portfolio.start: 启动Portfolio
    - portfolio.stop: 停止Portfolio
    - engine.start: 启动实盘引擎
    - engine.stop: 停止实盘引擎
    """

    command_type: str  # 命令类型
    target_id: str  # 目标组件ID（portfolio_id或engine_id）
    params: Optional[Dict[str, Any]] = None  # 命令参数
    timestamp: Optional[datetime.datetime] = None  # 时间戳
    portfolio_id: Optional[str] = None  # Portfolio ID（用于路由）
    engine_id: Optional[str] = None  # Engine ID（用于路由）
    run_id: Optional[str] = None  # 运行ID（用于审计）
    message_id: Optional[str] = None  # 消息ID（用于去重）

    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()
        if self.params is None:
            self.params = {}

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于Kafka JSON序列化）"""
        return {
            "command_type": self.command_type,
            "target_id": self.target_id,
            "params": self.params,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "portfolio_id": self.portfolio_id,
            "engine_id": self.engine_id,
            "run_id": self.run_id,
            "message_id": self.message_id
        }

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlCommand":
        """从字典反序列化"""
        # 处理timestamp字符串转datetime
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.datetime.fromisoformat(data["timestamp"])

        return cls(
            command_type=data["command_type"],
            target_id=data["target_id"],
            params=data.get("params"),
            timestamp=timestamp,
            portfolio_id=data.get("portfolio_id"),
            engine_id=data.get("engine_id"),
            run_id=data.get("run_id"),
            message_id=data.get("message_id")
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ControlCommand":
        """从JSON字符串反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return f"ControlCommand(command_type={self.command_type}, target_id={self.target_id[:8]}..., params={self.params})"
