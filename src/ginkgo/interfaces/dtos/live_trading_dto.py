# Upstream: BrokerManager, DataSyncService (实盘交易控制)
# Downstream: Kafka消息队列 (Broker控制命令/事件)
# Role: 实盘交易相关数据传输对象


from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class BrokerCommand(str, Enum):
    """Broker命令类型"""
    START = "broker_start"
    STOP = "broker_stop"
    PAUSE = "broker_pause"
    RESUME = "broker_resume"
    RESTART = "broker_restart"
    EMERGENCY_STOP = "broker_emergency_stop"
    BIND_ACCOUNT = "broker_bind_account"
    UNBIND_ACCOUNT = "broker_unbind_account"


class BrokerCommandDTO(BaseModel):
    """
    Broker控制命令DTO

    通过Kafka发送的Broker控制命令消息，用于控制Broker实例的启动、停止、暂停等操作。
    """
    # 命令标识
    command: BrokerCommand = Field(..., description="命令类型")
    timestamp: datetime = Field(default_factory=datetime.now)

    # 目标标识
    broker_instance_id: Optional[str] = Field(None, description="Broker实例ID")
    portfolio_id: Optional[str] = Field(None, description="Portfolio ID")
    live_account_id: Optional[str] = Field(None, description="LiveAccount ID")

    # 命令参数
    params: Dict[str, Any] = Field(default_factory=dict, description="命令参数")

    # 来源标识
    source: str = Field(default="api", description="命令来源")
    correlation_id: Optional[str] = Field(None, description="关联ID")

    # 命令常量
    class Commands:
        """预定义命令常量"""
        START = "broker_start"
        STOP = "broker_stop"
        PAUSE = "broker_pause"
        RESUME = "broker_resume"
        RESTART = "broker_restart"
        EMERGENCY_STOP = "broker_emergency_stop"

    # 类型判断方法
    def is_start(self) -> bool:
        """是否为启动命令"""
        return self.command == BrokerCommand.START

    def is_stop(self) -> bool:
        """是否为停止命令"""
        return self.command == BrokerCommand.STOP

    def is_pause(self) -> bool:
        """是否为暂停命令"""
        return self.command == BrokerCommand.PAUSE

    def is_resume(self) -> bool:
        """是否为恢复命令"""
        return self.command == BrokerCommand.RESUME

    def is_restart(self) -> bool:
        """是否为重启命令"""
        return self.command == BrokerCommand.RESTART

    def is_emergency_stop(self) -> bool:
        """是否为紧急停止命令"""
        return self.command == BrokerCommand.EMERGENCY_STOP

    def is_bind_account(self) -> bool:
        """是否为绑定账号命令"""
        return self.command == BrokerCommand.BIND_ACCOUNT

    def is_unbind_account(self) -> bool:
        """是否为解绑账号命令"""
        return self.command == BrokerCommand.UNBIND_ACCOUNT

    def get_param(self, key: str, default: Any = None) -> Any:
        """
        获取命令参数

        Args:
            key: 参数键
            default: 默认值

        Returns:
            参数值
        """
        return self.params.get(key, default)

    def to_json(self) -> str:
        """序列化为JSON字符串，用于Kafka发送"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> 'BrokerCommandDTO':
        """从JSON字符串反序列化，用于Kafka接收"""
        import json
        return cls(**json.loads(json_str))

    @classmethod
    def from_dict(cls, data: dict) -> 'BrokerCommandDTO':
        """从字典反序列化"""
        return cls(**data)


class BrokerEventType(str, Enum):
    """Broker事件类型"""
    STATUS_CHANGED = "status_changed"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    DATA_SYNCED = "data_synced"


class BrokerEventDTO(BaseModel):
    """
    Broker事件DTO

    Broker实例发布的状态变化事件，用于监控和追踪Broker运行状态。
    """
    # 事件标识
    event_type: BrokerEventType = Field(..., description="事件类型")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Broker信息
    broker_instance_id: str = Field(..., description="Broker实例ID")
    portfolio_id: str = Field(..., description="Portfolio ID")
    live_account_id: str = Field(..., description="LiveAccount ID")

    # 事件数据
    status: Optional[str] = Field(None, description="当前状态")
    previous_status: Optional[str] = Field(None, description="之前状态")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="事件详细数据")

    # 错误信息（仅ERROR事件）
    error_message: Optional[str] = Field(None, description="错误消息")
    error_code: Optional[str] = Field(None, description="错误代码")

    # 类型判断方法
    def is_status_changed(self) -> bool:
        """是否为状态变更事件"""
        return self.event_type == BrokerEventType.STATUS_CHANGED

    def is_heartbeat(self) -> bool:
        """是否为心跳事件"""
        return self.event_type == BrokerEventType.HEARTBEAT

    def is_error(self) -> bool:
        """是否为错误事件"""
        return self.event_type == BrokerEventType.ERROR

    def is_order_submitted(self) -> bool:
        """是否为订单已提交事件"""
        return self.event_type == BrokerEventType.ORDER_SUBMITTED

    def is_order_filled(self) -> bool:
        """是否为订单已成事件"""
        return self.event_type == BrokerEventType.ORDER_FILLED

    def is_data_synced(self) -> bool:
        """是否为数据同步完成事件"""
        return self.event_type == BrokerEventType.DATA_SYNCED

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict) -> 'BrokerEventDTO':
        """从字典反序列化"""
        return cls(**data)


class AccountDataType(str, Enum):
    """账户数据类型"""
    BALANCE = "balance"
    POSITION = "position"
    ORDER = "order"
    TRADE = "trade"


class AccountDataDTO(BaseModel):
    """
    账户数据同步DTO

    Broker向Portfolio同步的账户数据（余额、持仓、订单等）。
    """
    # 数据标识
    data_type: AccountDataType = Field(..., description="数据类型")
    timestamp: datetime = Field(default_factory=datetime.now)

    # 账户关联
    broker_instance_id: str = Field(..., description="Broker实例ID")
    portfolio_id: str = Field(..., description="Portfolio ID")
    live_account_id: str = Field(..., description="LiveAccount ID")

    # 数据内容
    data: Dict[str, Any] = Field(..., description="数据内容")

    # 数据版本（用于去重和一致性检查）
    version: int = Field(..., description="数据版本号")
    is_snapshot: bool = Field(default=False, description="是否为全量快照")

    # 类型判断方法
    def is_balance(self) -> bool:
        """是否为余额数据"""
        return self.data_type == AccountDataType.BALANCE

    def is_position(self) -> bool:
        """是否为持仓数据"""
        return self.data_type == AccountDataType.POSITION

    def is_order(self) -> bool:
        """是否为订单数据"""
        return self.data_type == AccountDataType.ORDER

    def is_trade(self) -> bool:
        """是否为成交数据"""
        return self.data_type == AccountDataType.TRADE

    def get_data(self) -> Dict[str, Any]:
        """获取数据内容"""
        return self.data

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: dict) -> 'AccountDataDTO':
        """从字典反序列化"""
        return cls(**data)


# Kafka Topic定义
class KafkaTopics:
    """实盘交易相关Kafka Topic"""
    BROKER_COMMANDS = "ginkgo.broker.commands"  # Broker控制命令
    BROKER_EVENTS = "ginkgo.broker.events"      # Broker状态事件
    ACCOUNT_DATA = "ginkgo.account.data"        # 账户数据同步
    LIVE_ORDERS = "ginkgo.live.orders"          # 实盘订单事件
