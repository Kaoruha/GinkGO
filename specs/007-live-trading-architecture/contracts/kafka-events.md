# Kafka Events Contracts

**Feature**: 007-live-trading-architecture
**Date**: 2026-01-04
**Version**: 1.0.0

本文档定义所有Kafka消息的事件格式和契约。

---

## Kafka Topic概览

### 实盘专用Topics (ginkgo.live.*)

| Topic | 消息类型 | 发布者 | 订阅者 |
|-------|---------|--------|--------|
| `ginkgo.live.market.data` | EventPriceUpdate | LiveCore.Data | ExecutionNode |
| `ginkgo.live.orders.submission` | EventOrderSubmission | ExecutionNode | LiveEngine |
| `ginkgo.live.orders.feedback` | EventOrderAck, EventOrderFilled | LiveEngine | ExecutionNode |
| `ginkgo.live.control.commands` | EventControlCommand | API Gateway | ExecutionNode, LiveEngine |
| `ginkgo.live.schedule.updates` | EventScheduleUpdate | Scheduler | ExecutionNode |
| `ginkgo.live.system.events` | EventSystem | ExecutionNode, Data, Scheduler | ExecutionNode, Data |

### 全局Topics (ginkgo.*)

| Topic | 消息类型 | 发布者 | 订阅者 |
|-------|---------|--------|--------|
| `ginkgo.alerts` | EventAlert | 所有模块 | Notification系统 |

---

## 1. 市场数据事件

### EventPriceUpdate

**Topic**: `ginkgo.live.market.data`
**方向**: Data → ExecutionNode
**频率**: ~5000条/秒

**消息格式**:
```json
{
  "event_type": "price_update",
  "code": "000001.SZ",
  "timestamp": "2026-01-04T10:00:00.000Z",
  "price": 10.50,
  "volume": 1000000,
  "open": 10.30,
  "high": 10.60,
  "low": 10.20,
  "close": 10.50,
  "bid_price": 10.49,
  "ask_price": 10.51,
  "bid_volume": 10000,
  "ask_volume": 10000
}
```

**字段说明**:
- `event_type`: 固定值"price_update"
- `code`: 股票代码（格式：XXXXXX.SZ/SH）
- `timestamp`: 事件时间戳（RFC3339格式，毫秒精度）
- `price`: 最新成交价
- `volume`: 成交量
- `open/high/low/close`: OHLC数据
- `bid_price/ask_price`: 买卖一价
- `bid_volume/ask_volume`: 买卖一量

**路由机制**: ExecutionNode使用`interest_map`路由到对应的Portfolio

---

## 2. 订单提交事件

### EventOrderSubmission

**Topic**: `ginkgo.live.orders.submission`
**方向**: ExecutionNode → LiveEngine
**触发**: Portfolio生成订单后

**消息格式**:
```json
{
  "event_type": "order_submission",
  "order_id": "order_uuid",
  "portfolio_id": "portfolio_uuid",
  "code": "000001.SZ",
  "direction": 1,
  "volume": 1000,
  "price": 10.50,
  "order_type": "limit",
  "timestamp": "2026-01-04T10:00:00.000Z"
}
```

**字段说明**:
- `event_type`: 固定值"order_submission"
- `order_id`: 订单唯一标识（UUID）
- `portfolio_id`: Portfolio唯一标识（UUID）
- `code`: 股票代码
- `direction`: 方向（1=LONG, -1=SHORT）
- `volume`: 订单数量
- `price`: 订单价格
- `order_type`: 订单类型（limit/market）
- `timestamp`: 订单生成时间戳

**处理流程**: LiveEngine接收到后调用TradeGateway执行订单

---

## 3. 订单回报事件

### EventOrderAck

**Topic**: `ginkgo.live.orders.feedback`
**方向**: LiveEngine → ExecutionNode
**触发**: 交易所确认订单

**消息格式**:
```json
{
  "event_type": "order_ack",
  "order_id": "order_uuid",
  "portfolio_id": "portfolio_uuid",
  "status": "acknowledged",
  "timestamp": "2026-01-04T10:00:01.000Z"
}
```

**字段说明**:
- `event_type`: 固定值"order_ack"
- `status`: 状态（acknowledged/rejected/cancelled）

---

### EventOrderPartiallyFilled

**Topic**: `ginkgo.live.orders.feedback`
**方向**: LiveEngine → ExecutionNode
**触发**: 订单部分成交

**消息格式**:
```json
{
  "event_type": "order_partially_filled",
  "order_id": "order_uuid",
  "portfolio_id": "portfolio_uuid",
  "code": "000001.SZ",
  "filled_volume": 500,
  "remaining_volume": 500,
  "filled_price": 10.50,
  "filled_amount": 5250.00,
  "timestamp": "2026-01-04T10:00:02.000Z"
}
```

---

### EventOrderFilled

**Topic**: `ginkgo.live.orders.feedback`
**方向**: LiveEngine → ExecutionNode
**触发**: 订单完全成交

**消息格式**:
```json
{
  "event_type": "order_filled",
  "order_id": "order_uuid",
  "portfolio_id": "portfolio_uuid",
  "code": "000001.SZ",
  "filled_volume": 1000,
  "filled_price": 10.50,
  "filled_amount": 10500.00,
  "commission": 5.25,
  "timestamp": "2026-01-04T10:00:03.000Z"
}
```

**字段说明**:
- `filled_volume`: 成交数量
- `filled_price`: 成交价格
- `filled_amount`: 成交金额
- `commission`: 手续费

**处理流程**: Portfolio收到后同步更新持仓和现金到数据库

---

## 4. 控制命令事件

### EventControlCommand

**Topic**: `ginkgo.live.control.commands`
**方向**: API Gateway → ExecutionNode, LiveEngine
**触发**: API请求或系统控制

**消息格式**:
```json
{
  "command_type": "portfolio.reload",
  "target_id": "portfolio_uuid",
  "timestamp": "2026-01-04T10:00:00.000Z",
  "params": {
    "reason": "user_api_update",
    "reload_config": true
  }
}
```

**command_type类型**:

| command_type | 目标 | 说明 |
|--------------|------|------|
| `portfolio.reload` | ExecutionNode | 重新加载Portfolio配置（优雅重启） |
| `portfolio.start` | ExecutionNode | 启动Portfolio |
| `portfolio.stop` | ExecutionNode | 停止Portfolio |
| `engine.start` | LiveEngine | 启动实盘引擎 |
| `engine.stop` | LiveEngine | 停止实盘引擎 |

**字段说明**:
- `command_type`: 命令类型
- `target_id`: 目标ID（portfolio_id或engine_id）
- `params`: 可选参数

**处理流程**: ExecutionNode收到`portfolio.reload`后触发优雅重启流程

---

## 5. 调度更新事件

### EventScheduleUpdate

**Topic**: `ginkgo.live.schedule.updates`
**方向**: Scheduler → ExecutionNode
**触发**: Scheduler更新调度计划（每30秒）

**消息格式**:
```json
{
  "node_id": "execution_node_001",
  "portfolio_ids": ["portfolio_001", "portfolio_002", "portfolio_003"],
  "action": "update",
  "timestamp": "2026-01-04T10:00:00.000Z"
}
```

**字段说明**:
- `node_id`: 目标ExecutionNode ID
- `portfolio_ids`: 应该运行的Portfolio ID列表
- `action`: 操作类型（update/migrate）

**处理流程**: ExecutionNode对比planned vs actual，增量更新

---

## 6. 系统事件

### EventSystem - 兴趣集更新

**Topic**: `ginkgo.live.system.events`
**方向**: ExecutionNode → Data
**触发**: Portfolio变更时主动上报 / 定期上报（60s）

**消息格式**:
```json
{
  "event_type": "interest.update",
  "node_id": "execution_node_001",
  "codes": ["000001.SZ", "000002.SZ", "600000.SH"],
  "timestamp": "2026-01-04T10:00:00.000Z"
}
```

**字段说明**:
- `event_type`: 固定值"interest.update"
- `codes`: 全量股票代码列表

**处理流程**: Data更新订阅列表（只增不减，除非Node离线或定时清理）

---

### EventSystem - 兴趣集同步请求

**Topic**: `ginkgo.live.system.events`
**方向**: Data → ExecutionNode
**触发**: Data启动时主动请求 / 定时清理（8h）

**消息格式**:
```json
{
  "event_type": "interest.sync_request",
  "source": "livecore_data",
  "timestamp": "2026-01-04T10:00:00.000Z"
}
```

**处理流程**: ExecutionNode收到后立即响应interest.update

---

### EventSystem - Node离线通知

**Topic**: `ginkgo.live.system.events`
**方向**: Scheduler → Data
**触发**: Scheduler检测到Node心跳超时

**消息格式**:
```json
{
  "event_type": "node.offline",
  "node_id": "execution_node_001",
  "timestamp": "2026-01-04T10:00:00.000Z",
  "reason": "heartbeat_timeout"
}
```

**处理流程**: Data清理该Node的兴趣集

---

## 7. 异常告警事件

### EventAlert

**Topic**: `ginkgo.alerts`
**方向**: 所有模块 → Notification系统
**触发**: 系统异常或告警

**消息格式**:
```json
{
  "alert_type": "queue_full",
  "severity": "critical",
  "source": "execution_node_001",
  "message": "Portfolio portfolio_001 queue is 95% full",
  "details": {
    "portfolio_id": "portfolio_001",
    "queue_size": 950,
    "queue_max": 1000,
    "node_id": "execution_node_001"
  },
  "timestamp": "2026-01-04T10:00:00.000Z"
}
```

**alert_type类型**:

| alert_type | severity | 触发条件 |
|------------|----------|---------|
| `queue_full` | critical/warning | Queue使用率超过95%/70% |
| `timeout` | critical | 操作超时（如TradeGateway调用） |
| `component_error` | critical | 组件故障（如Data连接失败） |
| `data_anomaly` | warning | 数据异常（如价格异常波动） |
| `node_offline` | critical | ExecutionNode离线 |

**severity级别**:
- `critical`: 严重告警（需要立即处理）
- `warning`: 警告告警（需要关注）
- `info`: 信息告警（记录即可）

**处理流程**: Notification系统订阅并通知用户

---

## Kafka配置规范

### Producer配置

**可靠性配置**:
```python
{
  "bootstrap.servers": "kafka1:9092,kafka2:9092,kafka3:9092",
  "acks": "all",                    # 所有副本确认
  "enable.idempotence": true,       # 幂等性
  "retries": 3,                     # 重试3次
  "max.in.flight.requests.per.connection": 5,
  "compression.type": "snappy"      # 压缩
}
```

---

### Consumer配置

**可靠性配置**:
```python
{
  "bootstrap.servers": "kafka1:9092,kafka2:9092,kafka3:9092",
  "group.id": "execution_node_group",  # Consumer Group
  "enable.auto.commit": false,         # 手动提交offset
  "auto.offset.reset": "earliest",     # 从最早开始
  "max.poll.records": 500,             # 每次最多500条
  "session.timeout.ms": 30000,
  "heartbeat.interval.ms": 10000
}
```

---

### Topic配置建议

**市场数据Topic** (`ginkgo.live.market.data`):
- **分区数**: 10（按股票代码哈希分区）
- **副本数**: 3
- **保留时间**: 7天
- **清理策略**: delete

**订单Topic** (`ginkgo.live.orders.submission/feedback`):
- **分区数**: 10（按portfolio_id哈希分区）
- **副本数**: 3
- **保留时间**: 30天
- **清理策略**: delete

**控制命令Topic** (`ginkgo.live.control.commands`):
- **分区数**: 3
- **副本数**: 3
- **保留时间**: 7天
- **清理策略**: delete

**系统事件Topic** (`ginkgo.live.system.events`):
- **分区数**: 3
- **副本数**: 3
- **保留时间**: 7天
- **清理策略**: delete

**告警Topic** (`ginkgo.alerts`):
- **分区数**: 3
- **副本数**: 3
- **保留时间**: 30天
- **清理策略**: delete

---

## 消息序列化

**推荐格式**: JSON（UTF-8编码）

**可选格式**（未来优化）:
- MessagePack（二进制，更小更快）
- Protobuf（强类型，向前兼容）

**消息Schema版本控制**:
- 所有消息包含`event_type`或`command_type`字段
- 新增字段保持向后兼容
- 重大变更使用新的event_type

---

## 错误处理

### Producer错误处理

```python
@retry(max_try=3)
def send_kafka_message(topic, message):
    try:
        producer.produce(topic, value=json.dumps(message))
        producer.flush()
    except KafkaError as e:
        GLOG.ERROR(f"Failed to send message to {topic}: {e}")
        raise
```

### Consumer错误处理

```python
def consume_kafka_messages():
    try:
        messages = consumer.consume(num_records=500, timeout=1.0)
        for msg in messages:
            try:
                process_message(msg)
            except Exception as e:
                GLOG.ERROR(f"Failed to process message: {e}")
                # 继续处理下一条消息，不阻塞
        # 手动提交offset
        consumer.commit()
    except KafkaError as e:
        GLOG.ERROR(f"Failed to consume messages: {e}")
        # 重试逻辑
```

---

## 总结

### Topic分类

1. **市场数据**: `ginkgo.live.market.data`
2. **订单提交**: `ginkgo.live.orders.submission`
3. **订单回报**: `ginkgo.live.orders.feedback`
4. **控制命令**: `ginkgo.live.control.commands`
5. **调度更新**: `ginkgo.live.schedule.updates`
6. **系统事件**: `ginkgo.live.system.events`
7. **异常告警**: `ginkgo.alerts`

### 关键设计

- **命名规范**: `ginkgo.live.*`实盘专用，`ginkgo.*`全局
- **事件类型**: 使用`event_type`或`command_type`区分
- **路由机制**: interest_map路由市场数据，portfolio_id路由订单
- **可靠性**: acks=all + 幂等性 + 手动提交offset
- **错误处理**: @retry装饰器 + 日志记录

### 性能目标

- **市场数据**: ~5000条/秒
- **订单提交**: ~100条/秒
- **订单回报**: ~100条/秒
- **端到端延迟**: < 200ms

---

**下一步**: 参考`quickstart.md`了解Kafka事件使用示例。
