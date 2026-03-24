# Live Trading DTO Definitions

**Feature**: 014-okx-live-account
**Date**: 2026-03-13
**Purpose**: 定义实盘交易相关的Kafka消息DTO

---

## 1. Broker控制DTO

### BrokerCommandDTO

用于控制Broker实例的命令消息。

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
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
    """Broker控制命令DTO

    通过Kafka发送的Broker控制命令消息
    """
    # 命令标识
    command: BrokerCommand = Field(..., description="命令类型")
    timestamp: datetime = Field(default_factory=datetime.now)

    # 目标标识
    broker_instance_id: Optional[str] = Field(None, description="Broker实例ID")
    portfolio_id: Optional[str] = Field(None, description="Portfolio ID")
    live_account_id: Optional[str] = Field(None, description="LiveAccount ID")

    # 命令参数
    params: Dict[str, Any] = Field(default_factory=dict)

    # 来源标识
    source: str = Field(default="api", description="命令来源")
    correlation_id: Optional[str] = Field(None, description="关联ID")

    # 命令常量
    class Commands:
        START = "broker_start"
        STOP = "broker_stop"
        PAUSE = "broker_pause"
        RESUME = "broker_resume"
        RESTART = "broker_restart"
        EMERGENCY_STOP = "broker_emergency_stop"

    # 类型判断方法
    def is_start(self) -> bool:
        return self.command == BrokerCommand.START

    def is_stop(self) -> bool:
        return self.command == BrokerCommand.STOP

    def is_pause(self) -> bool:
        return self.command == BrokerCommand.PAUSE

    def is_resume(self) -> bool:
        return self.command == BrokerCommand.RESUME

    def is_restart(self) -> bool:
        return self.command == BrokerCommand.RESTART

    def is_emergency_stop(self) -> bool:
        return self.command == BrokerCommand.EMERGENCY_STOP

    def is_bind_account(self) -> bool:
        return self.command == BrokerCommand.BIND_ACCOUNT

    def is_unbind_account(self) -> bool:
        return self.command == BrokerCommand.UNBIND_ACCOUNT

    # 参数获取方法
    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)

    # 序列化方法
    def to_json(self) -> str:
        """序列化为JSON字符串，用于Kafka发送"""
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> "BrokerCommandDTO":
        """从JSON字符串反序列化，用于Kafka接收"""
        return cls(**json.loads(json_str))

    @classmethod
    def from_dict(cls, data: dict) -> "BrokerCommandDTO":
        """从字典反序列化"""
        return cls(**data)
```

**使用示例**:
```python
# 发送启动命令
dto = BrokerCommandDTO(
    command=BrokerCommand.START,
    broker_instance_id="xxx-uuid",
    source="web_ui"
)
producer.send("ginkgo.broker.commands", dto.to_json())

# 接收命令
message = consumer.poll()
dto = BrokerCommandDTO.from_dict(message.value)
if dto.is_start():
    broker_id = dto.broker_instance_id
    # 启动broker...
```

---

## 2. Broker状态事件DTO

### BrokerEventDTO

用于发布Broker状态变化事件。

```python
class BrokerEventType(str, Enum):
    """Broker事件类型"""
    STATUS_CHANGED = "status_changed"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_FILLED = "order_filled"
    DATA_SYNCED = "data_synced"

class BrokerEventDTO(BaseModel):
    """Broker事件DTO

    Broker实例发布的状态变化事件
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
    error_message: Optional[str] = Field(None)
    error_code: Optional[str] = Field(None)

    # 类型判断方法
    def is_status_changed(self) -> bool:
        return self.event_type == BrokerEventType.STATUS_CHANGED

    def is_heartbeat(self) -> bool:
        return self.event_type == BrokerEventType.HEARTBEAT

    def is_error(self) -> bool:
        return self.event_type == BrokerEventType.ERROR

    def is_order_submitted(self) -> bool:
        return self.event_type == BrokerEventType.ORDER_SUBMITTED

    def is_order_filled(self) -> bool:
        return self.event_type == BrokerEventType.ORDER_FILLED

    def is_data_synced(self) -> bool:
        return self.event_type == BrokerEventType.DATA_SYNCED
```

---

## 3. 实盘数据同步DTO

### AccountDataDTO

用于同步实盘账户数据（余额、持仓）。

```python
class AccountDataType(str, Enum):
    """账户数据类型"""
    BALANCE = "balance"
    POSITION = "position"
    ORDER = "order"
    TRADE = "trade"

class AccountDataDTO(BaseModel):
    """账户数据同步DTO

    Broker向Portfolio同步的账户数据
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
        return self.data_type == AccountDataType.BALANCE

    def is_position(self) -> bool:
        return self.data_type == AccountDataType.POSITION

    def is_order(self) -> bool:
        return self.data_type == AccountDataType.ORDER

    def is_trade(self) -> bool:
        return self.data_type == AccountDataType.TRADE

    # 数据内容获取方法
    def get_data(self) -> Dict[str, Any]:
        return self.data
```

**数据格式示例**:

余额数据:
```json
{
  "data_type": "balance",
  "broker_instance_id": "xxx",
  "portfolio_id": "yyy",
  "live_account_id": "zzz",
  "version": 12345,
  "is_snapshot": true,
  "data": {
    "total_equity": "10000.00",
    "available_balance": "9500.00",
    "frozen_balance": "500.00",
    "currency_balances": [
      {"currency": "USDT", "available": "9500.00", "frozen": "500.00"},
      {"currency": "BTC", "available": "0.1", "frozen": "0.0"}
    ]
  }
}
```

持仓数据:
```json
{
  "data_type": "position",
  "data": {
    "positions": [
      {
        "symbol": "BTC-USDT",
        "side": "long",
        "size": "0.1",
        "available": "0.1",
        "avg_price": "45000.00",
        "unrealized_pnl": "50.00"
      }
    ]
  }
}
```

---

## 4. Kafka Topic定义

### Topic列表

| Topic | 用途 | Key | Partition |
|-------|------|-----|-----------|
| ginkgo.broker.commands | Broker控制命令 | broker_instance_id | 3 |
| ginkgo.broker.events | Broker状态事件 | broker_instance_id | 3 |
| ginkgo.account.data | 账户数据同步 | portfolio_id | 10 |
| ginkgo.live.orders | 实盘订单事件 | portfolio_id | 10 |

### 消息流转

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Web UI     │  Cmd    │   Kafka     │  Event  │   Broker    │
│  (控制面板)  │────────▶│  Broker Cmd │────────▶│  Instance   │
└─────────────┘         └─────────────┘         └──────┬──────┘
                                                         │
                                                         │ Data
                                                         ▼
                                                   ┌─────────────┐
                                                   │   Kafka     │
                                                   │ Account Data│
                                                   └──────┬──────┘
                                                          │
                                                          │ Sync
                                                          ▼
                                                   ┌─────────────┐
                                                   │  Portfolio  │
                                                   │  (更新余额)  │
                                                   └─────────────┘
```

---

## 5. DTO最佳实践

### 发送端规范

```python
from ginkgo.interfaces.dtos import BrokerCommandDTO

# ✅ 正确：使用DTO
dto = BrokerCommandDTO(
    command=BrokerCommand.START,
    broker_instance_id=broker_id,
    source="web_ui"
)
producer.send("ginkgo.broker.commands", dto.to_json())

# ❌ 错误：直接发送字典
producer.send("ginkgo.broker.commands", json.dumps({
    "command": "start",
    "broker_id": broker_id
}))
```

### 接收端规范

```python
from ginkgo.interfaces.dtos import BrokerCommandDTO

# ✅ 正确：使用DTO解析
for message in consumer:
    dto = BrokerCommandDTO.from_dict(message.value)
    if dto.is_start():
        handle_start(dto)

# ❌ 错误：直接使用字典
for message in consumer:
    data = message.value
    if data["command"] == "start":  # 硬编码字符串
        handle_start(data)
```

### 错误处理

```python
try:
    dto = BrokerCommandDTO.from_dict(message)
except ValidationError as e:
    logger.error(f"Invalid DTO: {e}")
    # 跳过或发送到死信队列
    continue
```

---

## 6. DTO扩展指南

### 添加新命令类型

1. 在`BrokerCommand`枚举中添加新命令
2. 在`Commands`类中添加常量
3. 添加对应的`is_xxx()`方法
4. 更新文档

### 添加新事件类型

1. 在`BrokerEventType`枚举中添加新事件
2. 在`BrokerEventDTO`中添加对应的`is_xxx()`方法
3. 定义事件数据格式
4. 更新文档
