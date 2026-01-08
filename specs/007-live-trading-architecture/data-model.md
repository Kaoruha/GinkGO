# Data Model: 实盘多Portfolio架构支持

**Feature**: 007-live-trading-architecture
**Date**: 2026-01-04
**Status**: Final

本文档定义实盘交易系统的所有数据实体、关系模型和存储策略。

---

## 核心数据实体

### 1. Portfolio相关实体

#### MPportfolio (MySQL)

**表名**: `portfolios`
**存储**: MySQL
**用途**: Portfolio配置和元数据

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| `uuid` | CHAR(36) | Portfolio唯一标识 | PRIMARY KEY |
| `name` | VARCHAR(255) | Portfolio名称 | NOT NULL |
| `user_id` | CHAR(36) | 所属用户UUID | FOREIGN KEY → users.uuid |
| `initial_cash` | DECIMAL(20,8) | 初始资金 | NOT NULL |
| `current_cash` | DECIMAL(20,8) | 当前现金 | NOT NULL |
| `status` | ENUM | 状态 (created/running/stopping/stopped/reloading/error) | NOT NULL |
| `config` | JSON | 完整配置（策略、风控、Sizer等） | NOT NULL |
| `updated_at` | TIMESTAMP | 配置更新时间戳 | INDEX |
| `created_at` | TIMESTAMP | 创建时间 | NOT NULL |

**索引设计**:
- PRIMARY KEY: `uuid`
- INDEX: `user_id` - 用户查询自己的Portfolio
- INDEX: `status` - 按状态筛选
- INDEX: `updated_at` - 配置更新检测（定期轮询）

**config JSON结构**:
```json
{
  "strategy": {
    "strategy_id": "uuid",
    "name": "TrendFollowStrategy",
    "params": {
      "short_period": 5,
      "long_period": 20
    }
  },
  "risk_managements": [
    {
      "risk_id": "uuid",
      "name": "PositionRatioRisk",
      "params": {
        "max_position_ratio": 0.2
      }
    }
  ],
  "sizer": {
    "sizer_id": "uuid",
    "name": "FixedAmountSizer",
    "params": {
      "amount": 10000
    }
  }
}
```

---

#### MPportfolioState (Redis)

**Key Pattern**: `portfolio:{portfolio_id}:state`
**存储**: Redis
**用途**: Portfolio实时状态缓存

**数据结构**:
```
{
  "portfolio_id": "uuid",
  "status": "running",
  "cash": 100000.00,
  "total_value": 150000.00,
  "position_count": 5,
  "last_update": "2026-01-04T10:00:00Z"
}
```

**TTL**: 无（持久化，但由ExecutionNode定期刷新）

---

#### MPosition (ClickHouse)

**表名**: `positions`
**存储**: ClickHouse
**用途**: Portfolio持仓历史记录

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `portfolio_id` | String | Portfolio UUID |
| `code` | String | 股票代码 |
| `direction` | Int8 | 方向 (1=LONG, -1=SHORT) |
| `volume` | Int64 | 持仓量 |
| `available_volume` | Int64 | 可用数量 |
| `cost_price` | Decimal(18,4) | 成本价 |
| `current_price` | Decimal(18,4) | 当前价 |
| `market_value` | Decimal(20,8) | 市值 |
| `profit_loss` | Decimal(20,8) | 浮动盈亏 |
| `timestamp` | DateTime64(3) | 记录时间 |

**索引设计**:
- PRIMARY KEY: `(portfolio_id, code, timestamp)` - 按Portfolio+股票查询最新状态
- ORDER BY: `timestamp` - 按时间排序

---

### 2. ExecutionNode相关实体

#### MExecutionNode (Redis)

**Key Pattern**: `execution_node:{node_id}:info`
**存储**: Redis
**用途**: ExecutionNode信息缓存

**数据结构**:
```
{
  "node_id": "execution_node_001",
  "host": "192.168.1.10",
  "port": 8001,
  "portfolio_count": 3,
  "status": "active",
  "last_heartbeat": "2026-01-04T10:00:00Z"
}
```

**TTL**: 无（由心跳机制更新）

---

#### Heartbeat (Redis)

**Key Pattern**: `heartbeat:node:{node_id}`
**存储**: Redis
**用途**: ExecutionNode心跳检测

**数据结构**:
```
Key: heartbeat:node:execution_node_001
Value: "alive"
TTL: 30秒
```

**更新机制**: ExecutionNode每10秒SET一次（EX 30）

---

#### ActiveNodes (Redis)

**Key Pattern**: `nodes:active`
**存储**: Redis Set
**用途**: 活跃ExecutionNode列表

**数据结构**:
```
SMEMBERS nodes:active
→ ["execution_node_001", "execution_node_002", ...]
```

**维护者**:
- ExecutionNode启动时: `SADD nodes:active {node_id}`
- Scheduler检测到离线时: `SREM nodes:active {node_id}`

---

#### SchedulePlan (Redis)

**Key Pattern**: `schedule:plan:{node_id}`
**存储**: Redis Set
**用途**: 调度计划（每个Node应该运行的Portfolio列表）

**数据结构**:
```
SMEMBERS schedule:plan:execution_node_001
→ ["portfolio_001", "portfolio_002", "portfolio_003"]
```

**维护者**: Scheduler每30秒更新

---

#### InterestMap (ExecutionNode内存)

**存储**: ExecutionNode内存字典
**用途**: 股票代码 → Portfolio ID列表映射

**数据结构**:
```python
interest_map: Dict[str, List[str]] = {
    "000001.SZ": ["portfolio_1_uuid", "portfolio_3_uuid"],
    "000002.SZ": ["portfolio_2_uuid"],
    ...
}
```

**线程安全**: 使用 `threading.Lock` 保护

**更新触发**:
- Portfolio启动时
- Portfolio配置更新时
- Portfolio停止时

---

### 3. Kafka消息实体

#### EventPriceUpdate (市场数据)

**Topic**: `ginkgo.live.market.data`
**发布者**: LiveCore.Data
**订阅者**: ExecutionNode

**消息格式**:
```json
{
  "event_type": "price_update",
  "code": "000001.SZ",
  "timestamp": "2026-01-04T10:00:00Z",
  "price": 10.50,
  "volume": 1000000,
  "open": 10.30,
  "high": 10.60,
  "low": 10.20,
  "close": 10.50
}
```

---

#### EventOrderSubmission (订单提交)

**Topic**: `ginkgo.live.orders.submission`
**发布者**: ExecutionNode
**订阅者**: LiveCore.LiveEngine

**消息格式**:
```json
{
  "event_type": "order_submission",
  "order_id": "uuid",
  "portfolio_id": "uuid",
  "code": "000001.SZ",
  "direction": 1,
  "volume": 1000,
  "price": 10.50,
  "order_type": "limit",
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

#### EventOrderAck (订单确认)

**Topic**: `ginkgo.live.orders.feedback`
**发布者**: LiveCore.LiveEngine
**订阅者**: ExecutionNode

**消息格式**:
```json
{
  "event_type": "order_ack",
  "order_id": "uuid",
  "portfolio_id": "uuid",
  "status": "acknowledged",
  "timestamp": "2026-01-04T10:00:01Z"
}
```

---

#### EventOrderFilled (订单成交)

**Topic**: `ginkgo.live.orders.feedback`
**发布者**: LiveCore.LiveEngine
**订阅者**: ExecutionNode

**消息格式**:
```json
{
  "event_type": "order_filled",
  "order_id": "uuid",
  "portfolio_id": "uuid",
  "code": "000001.SZ",
  "filled_volume": 1000,
  "filled_price": 10.50,
  "filled_amount": 10500.00,
  "timestamp": "2026-01-04T10:00:02Z"
}
```

---

#### EventControlCommand (控制命令)

**Topic**: `ginkgo.live.control.commands`
**发布者**: API Gateway
**订阅者**: ExecutionNode, LiveCore.LiveEngine

**消息格式**:
```json
{
  "command_type": "portfolio.reload",  // portfolio.reload/start/stop, engine.start/stop
  "target_id": "portfolio_001",
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

#### EventScheduleUpdate (调度更新)

**Topic**: `ginkgo.live.schedule.updates`
**发布者**: Scheduler
**订阅者**: ExecutionNode

**消息格式**:
```json
{
  "node_id": "execution_node_001",
  "portfolio_ids": ["portfolio_001", "portfolio_002"],
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

#### EventSystem (系统事件)

**Topic**: `ginkgo.live.system.events`
**发布者**: ExecutionNode, LiveCore.Data, Scheduler
**订阅者**: ExecutionNode, LiveCore.Data

**消息类型**:

**1. 兴趣集更新**:
```json
{
  "event_type": "interest.update",
  "node_id": "execution_node_001",
  "codes": ["000001.SZ", "000002.SZ", ...],
  "timestamp": "2026-01-04T10:00:00Z"
}
```

**2. 兴趣集同步请求**:
```json
{
  "event_type": "interest.sync_request",
  "source": "livecore_data",
  "timestamp": "2026-01-04T10:00:00Z"
}
```

**3. Node离线通知**:
```json
{
  "event_type": "node.offline",
  "node_id": "execution_node_001",
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

#### EventAlert (异常告警)

**Topic**: `ginkgo.alerts`
**发布者**: 所有模块
**订阅者**: Notification系统

**消息格式**:
```json
{
  "alert_type": "queue_full",  // queue_full, timeout, component_error, data_anomaly
  "severity": "critical",      // critical, warning, info
  "source": "execution_node_001",
  "message": "Portfolio portfolio_001 queue is 95% full",
  "details": {
    "portfolio_id": "portfolio_001",
    "queue_size": 950,
    "queue_max": 1000
  },
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

### 4. 用户相关实体（复用006-notification-system）

#### MUser (MySQL)

**表名**: `users`
**存储**: MySQL
**用途**: 用户基本信息

**参考**: `/specs/006-notification-system/spec.md` - User Story 2

---

#### MUserContact (MySQL)

**表名**: `user_contacts`
**存储**: MySQL
**用途**: 用户联系方式

**参考**: `/specs/006-notification-system/spec.md` - User Story 2

---

## 数据关系图

```
┌─────────────────────────────────────────────────────────────┐
│                        MySQL                                 │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   users      │──────│ portfolios   │                    │
│  └──────────────┘      └──────────────┘                    │
│         │                       │                           │
│         │                       │                           │
│  ┌──────▼──────┐         ┌──────▼──────┐                   │
│  │user_contacts│         │  strategy   │                   │
│  └─────────────┘         │  risk_mgmt  │                   │
│                          │   sizer     │                   │
│                          └─────────────┘                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 同步
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        Redis                                 │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │portfolio:*:state │  │heartbeat:node:*  │               │
│  │schedule:plan:*   │  │nodes:active      │               │
│  │execution_node:*  │  └──────────────────┘               │
│  └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ 写入
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      ClickHouse                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  positions (portfolio_id, code, timestamp, ...)   │      │
│  │  orders (portfolio_id, code, timestamp, ...)      │      │
│  │  portfolio_history (portfolio_id, timestamp, ...) │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 数据流转路径

### 路径1: Portfolio配置更新

```
API Gateway
    ↓ (1. HTTP POST /api/portfolio/:id)
MySQL (UPDATE portfolios SET config={...}, updated_at=NOW())
    ↓ (2. Kafka PRODUCE)
ginkgo.live.control.commands {command_type: "portfolio.reload", target_id: "..."}
    ↓ (3. Kafka CONSUME)
ExecutionNode
    ↓ (4. 触发优雅重启)
Redis (portfolio:{id}:state = "stopping")
    ↓ (5. 等待Queue清空)
ExecutionNode (从MySQL加载新配置)
    ↓ (6. 重新初始化Portfolio)
Redis (portfolio:{id}:state = "running")
```

---

### 路径2: 市场数据流转

```
LiveCore.Data (从Tushare/券商获取实时行情)
    ↓ (1. Kafka PRODUCE)
ginkgo.live.market.data {code: "000001.SZ", price: 10.50, ...}
    ↓ (2. Kafka CONSUME)
ExecutionNode (Kafka Consumer Group自动分配)
    ↓ (3. interest_map路由 - O(1)查找)
PortfolioProcessor Queue (非阻塞put)
    ↓ (4. Portfolio处理)
Portfolio.on_price_update(event)
    ↓ (5. 策略计算 → Signal → Sizer → Order)
portfolio.put(order) → output_queue
    ↓ (6. ExecutionNode监听器序列化并发送)
ExecutionNode._start_output_queue_listener()
    ↓ (7. Kafka PRODUCE)
ginkgo.live.orders.submission {portfolio_id, code, volume, ...}
```

---

### 路径3: 订单回报流转

```
LiveCore.TradeGateway (调用券商API执行订单)
    ↓ (1. 收到交易所回报)
LiveCore.LiveEngine
    ↓ (2. Kafka PRODUCE)
ginkgo.live.orders.feedback {event_type: "filled", order_id, ...}
    ↓ (3. Kafka CONSUME)
ExecutionNode
    ↓ (4. 根据portfolio_id路由)
Portfolio.on_order_filled(event)
    ↓ (5. 更新内存状态)
Portfolio (position.volume += filled_volume)
Portfolio (cash -= filled_amount)
    ↓ (6. 同步写入数据库)
ClickHouse (INSERT INTO positions ...)
MySQL (UPDATE portfolios SET cash = ...)
```

---

### 路径4: 心跳检测

```
ExecutionNode (每10秒)
    ↓ (1. Redis SET)
heartbeat:node:execution_node_001 = "alive" EX 30
    ↓ (2. TTL自动过期)
    ↓ (3. Scheduler每30秒检测)
Scheduler (SMEMBERS nodes:active)
    ↓ (4. 检查心跳过期)
Scheduler (EXISTS heartbeat:node:{node_id})
    ↓ (5. 如果不存在 - Node离线)
Scheduler (SREM nodes:active {node_id})
    ↓ (6. Kafka PRODUCE)
ginkgo.live.system.events {event_type: "node.offline", node_id: "..."}
    ↓ (7. 触发Portfolio重新调度)
Scheduler (更新schedule:plan:*)
```

---

## 数据一致性保证

### 1. Portfolio配置一致性

**问题**: API Gateway更新配置后，如何保证ExecutionNode使用最新配置？

**解决方案**: Kafka通知 + 定期轮询（双重保障）
1. API Gateway更新MySQL后，立即发送Kafka通知
2. ExecutionNode收到通知后立即触发重新加载
3. ExecutionNode每30秒轮询MySQL的`updated_at`字段
4. 如果`updated_at`变化，加载完整配置并对比

**一致性级别**: 最终一致性（< 30秒）

---

### 2. 订单回报一致性

**问题**: Portfolio收到订单回报后，如何保证状态更新不丢失？

**解决方案**: 同步写入数据库
1. Portfolio收到EventOrderFilled事件
2. 更新内存状态（position, cash）
3. **同步写入**ClickHouse和MySQL（使用`@retry`装饰器）
4. 写入成功后才处理下一个事件

**一致性级别**: 强一致性

---

### 3. 兴趣集一致性

**问题**: Data模块如何保证订阅的是最新的兴趣集？

**解决方案**: 三种上报机制
1. **主动上报**: Portfolio变更时立即上报
2. **定期上报**: 60秒间隔全量上报
3. **定时清理+重同步**: 8小时间隔，使用Event.wait()同步等待所有ExecutionNode响应

**一致性级别**: 最终一致性（< 60秒正常，< 8小时兜底）

---

## 性能优化策略

### 1. 缓存策略

| 数据 | 缓存位置 | TTL | 更新策略 |
|------|----------|-----|----------|
| **Portfolio状态** | Redis | 无 | ExecutionNode定期刷新 |
| **ExecutionNode信息** | Redis | 无 | 心跳机制更新 |
| **调度计划** | Redis | 无 | Scheduler每30秒更新 |
| **Portfolio配置** | 内存 | 无 | 启动时加载，变更时重新加载 |

---

### 2. 批量写入策略

**ClickHouse批量插入**:
```python
@time_logger
@retry(max_try=3)
def batch_insert_positions(positions: List[MPosition]):
    """批量插入持仓记录"""
    client.execute("INSERT INTO positions VALUES", positions)
```

**触发时机**:
- Portfolio处理完一批市场数据事件后
- 定时批量（每10秒或每100条记录）

---

### 3. 索引策略

**MySQL索引**:
- PRIMARY KEY: `uuid`
- INDEX: `user_id` - 用户查询
- INDEX: `status` - 按状态筛选
- INDEX: `updated_at` - 配置更新检测

**ClickHouse索引**:
- PRIMARY KEY: `(portfolio_id, code, timestamp)` - 按Portfolio+股票查询
- ORDER BY: `timestamp` - 按时间排序

---

## 总结

### 核心实体

1. **MPportfolio** - Portfolio配置（MySQL）
2. **MPosition** - 持仓历史（ClickHouse）
3. **MExecutionNode** - ExecutionNode信息（Redis）
4. **Heartbeat** - 心跳检测（Redis）
5. **InterestMap** - 兴趣集映射（ExecutionNode内存）
6. **Kafka Events** - 所有组件间通信（Kafka）

### 存储策略

- **MySQL**: Portfolio配置，用户数据（关系数据）
- **ClickHouse**: 持仓历史，订单历史（时序数据）
- **Redis**: 实时状态，心跳，调度计划（热数据）
- **Kafka**: 所有组件间通信（消息总线）

### 数据流转

1. **市场数据流**: Data → Kafka → ExecutionNode → Portfolio
2. **订单流**: Portfolio → ExecutionNode → Kafka → LiveEngine → TradeGateway
3. **回报流**: TradeGateway → LiveEngine → Kafka → ExecutionNode → Portfolio
4. **控制流**: API Gateway → Kafka → ExecutionNode
5. **调度流**: Scheduler → Kafka → ExecutionNode
6. **心跳流**: ExecutionNode → Redis → Scheduler

### 一致性保证

- **Portfolio配置**: 最终一致性（< 30秒）
- **订单回报**: 强一致性（同步写入）
- **兴趣集**: 最终一致性（< 60秒正常，< 8小时兜底）

---

**下一步**: 参考`contracts/`文档了解API接口设计。
