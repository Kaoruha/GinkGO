# Upstream: DeploymentService, PortfolioService, TaskTimer (构造控制命令)
# Downstream: PaperTradingWorker, ExecutionNode (消费控制命令)
# Role: 统一的 Kafka 控制命令 DTO，提供工厂方法和序列化

"""
Kafka 控制命令消息 DTO

所有 Kafka CONTROL_COMMANDS topic 的消息统一使用此类构造和解析。
发送方使用工厂方法（deploy/unload/daily_cycle），消费方使用 from_dict() 解析。
"""

import json
import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class ControlCommand:
    """Kafka 控制命令消息

    命令类型：
    - deploy: 加载 Portfolio 到引擎
    - unload: 从引擎卸载 Portfolio
    - paper_trading: 触发日循环
    """

    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "params": self.params,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ControlCommand":
        return cls(
            command=data.get("command", ""),
            params=data.get("params", {}),
            timestamp=data.get("timestamp"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ControlCommand":
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def deploy(cls, portfolio_id: str) -> "ControlCommand":
        return cls(command="deploy", params={"portfolio_id": portfolio_id})

    @classmethod
    def unload(cls, portfolio_id: str) -> "ControlCommand":
        return cls(command="unload", params={"portfolio_id": portfolio_id})

    @classmethod
    def daily_cycle(cls) -> "ControlCommand":
        return cls(command="paper_trading", params={})

    def __repr__(self) -> str:
        pid = self.params.get("portfolio_id", "")
        if pid:
            pid = pid[:8]
        return f"ControlCommand(command={self.command}, portfolio_id={pid}...)"
