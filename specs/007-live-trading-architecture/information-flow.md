# 实盘交易系统信息流转视图

**Purpose**: 描述实盘交易系统各组件之间的信息流转关系
**Created**: 2026-01-04
**Updated**: 2026-01-04 (所有路径已确认，Topic命名统一为ginkgo.live.xxxx)
**Feature**: 007-live-trading-architecture

---

## 核心组件信息流转图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              实盘交易系统架构                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────┐
│ API Gateway │ ← HTTP API控制入口
└──────┬──────┘
       │ Kafka/Redis
       ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                           LiveCore                                     │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌──────────────┐       │
│  │   Data    │  │   Trade   │  │  Live    │  │  Scheduler  │       │
│  │  Module   │  │  Gateway  │  │  Engine  │  │             │       │
│  └─────┬─────┘  └─────┬─────┘  └────┬─────┘  └──────┬──────┘       │
│        │              │             │               │              │
└────────┼──────────────┼─────────────┼───────────────┼──────────────┘
         │              │             │               │
         │ Kafka        │ Kafka       │               │ Redis
         │              │             │               │
┌────────▼─────────────────────────────────────────────────────────────┐
│                         Kafka Message Bus                              │
│  market.data.*  │  orders.*  │  portfolio.*  │  ginkgo.live.schedule.updates    │
└────────┬──────────────────────────────────────────────────────────────┘
         │
         │ Kafka Subscribe
         ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                        ExecutionNode (x10)                              │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │         Kafka消费线程 → interest_map路由                     │    │
│  └──────────────────────────────────────────────────────────────┘    │
│         │
│         ▼
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │    PortfolioProcessor线程池 (每个Portfolio一个线程)           │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │    │
│  │  │ Thread-A │  │ Thread-B │  │ Thread-C │  ... (3-5个)        │    │
│  │  │ Queue    │  │ Queue    │  │ Queue    │                   │    │
│  │  └──────────┘  └──────────┘  └──────────┘                   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  心跳: Redis(heartbeat:node:{id})    状态: Redis(portfolio:*:status)  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 关键信息流转路径

### 路径1: 市场数据 → Portfolio → 订单

```
外部数据源（Tushare/券商）
    ↓
LiveCore.Data
    └─ 发布: ginkgo.live.market.data (A股行情)
    ↓
Kafka (ginkgo.live.market.data)
    ↓
ExecutionNode (Kafka Consumer)
    ├─ interest_map: {code: [portfolio_ids]} 路由
    ├─ 两级警告机制:
    │   ├─ 70% (700/1000): 发送警告，5分钟间隔
    │   └─ 95% (950/1000): 丢弃最新消息 + 发送警告，1分钟间隔
    └─ queue.put(event)
    ↓
Portfolio Queue (有界Queue，maxsize=1000)
    ↓
Portfolio (on_price_update)
    ├─ 策略计算: strategy.cal() → Signal
    ├─ 风控检查: apply_risk_managements(signal)
    ├─ Sizer计算: sizer.cal(signal) → Order
    └─ 订单提交: ExecutionNode.submit_order(order)
    ↓
Kafka (ginkgo.live.orders.submission)
    ↓
LiveCore.LiveEngine (Kafka Consumer)
    ↓
LiveCore.TradeGateway
    ↓
真实交易所 (券商API)
```

**关键设计点**:
- **interest_map**: ExecutionNode维护，汇总所有Portfolio的兴趣集
- **两级警告机制**:
  - 70%阈值: `queue.qsize() >= 700` → 发送警告，5分钟间隔
  - 95%阈值: `queue.qsize() >= 950` → 丢弃最新消息 + 发送警告，1分钟间隔
- **Order传递**: Portfolio直接调用`ExecutionNode.submit_order()`，不经过额外队列
- **Queue用途**: 仅用于接收市场数据事件，不是Order发送队列

**信息类型**: EventPriceUpdate
**频率**: ~5000条/秒

---

### 路径2: 订单回报 → Portfolio

```
真实交易所
    ↓
LiveCore.TradeGateway
    ↓
LiveCore.LiveEngine
    └─ 发布: ginkgo.live.orders.feedback
        ├─ "ack" - 订单确认
        ├─ "partially_filled" - 部分成交
        └─ "filled" - 完全成交
    ↓
Kafka (ginkgo.live.orders.feedback)
    ↓
ExecutionNode (Kafka Consumer)
    ├─ 订阅 ginkgo.live.orders.feedback
    └─ 根据 portfolio_id 路由到对应Portfolio
    ↓
Portfolio (on_order_filled)
    ├─ 更新内存状态:
    │   ├─ position.volume += filled_volume
    │   └─ portfolio.cash -= filled_amount
    └─ 同步写入数据库
        ├─ UPDATE positions SET volume = ...
        └─ UPDATE portfolios SET cash = ...

[并行情径 - 订单提交]
Portfolio (生成Order)
    ↓
ExecutionNode.submit_order()
    ↓
Kafka (ginkgo.live.orders.submission)
    ↓
LiveCore.LiveEngine (Kafka Consumer)
    ↓
LiveCore.TradeGateway
    ↓
真实交易所
```

**关键设计点**:
- **两个独立Topic**:
  - `ginkgo.live.orders.submission`: 订单提交（ExecutionNode → LiveEngine）
  - `ginkgo.live.orders.feedback`: 订单回报（LiveEngine → ExecutionNode）
- **双向解耦**: 订单提交和回报使用不同的topic，降低耦合
- **同步持久化**: Portfolio收到订单回报后同步写入数据库，保证数据一致性
- **路由机制**: ExecutionNode通过portfolio_id将订单回报路由到对应Portfolio

**信息类型**: EventOrderAck, EventOrderPartiallyFilled, EventOrderFilled
**触发**: 订单成交后

---

### 路径3: Portfolio配置更新 (优雅重启)

```
API Gateway (更新Portfolio配置)
    ├─ 1. 写入数据库
    │   ├─ portfolios表: Portfolio基本信息
    │   ├─ portfolio_components表: 所有组件配置
    │   │   └─ component_type区分: strategy | risk_management | sizer | selector | analyzer
    │   └─ updated_at: 自动更新时间戳
    └─ 2. 主动发送控制命令
        └─ Kafka.publish("ginkgo.live.control.commands",
                         {command_type: "portfolio.reload",
                          target_id: portfolio_id,
                          reason: "user_api_update"})

ExecutionNode (双重保障机制)
    ├─ Kafka消费: ginkgo.live.control.commands
    │   └─ 收到portfolio.reload → 立即触发重新加载
    └─ 定期轮询 (30s, 可配置)
        ├─ 遍历所有Portfolio
        ├─ 第一阶段: 检查 updated_at (轻量级)
        ├─ 第二阶段: updated_at变化则加载完整配置
        ├─ 比对逻辑: TODO (多层配置对比)
        └─ 值变化 → 触发Portfolio重启

Portfolio重启流程
    ├─ 状态: RUNNING → STOPPING
    ├─ 缓存Kafka消息到buffer
    ├─ 等待Queue清空 (timeout 30s)
    ├─ 从数据库加载新配置
    ├─ 重新初始化Portfolio
    ├─ 重放缓存消息 (按时间戳顺序)
    └─ 状态: RELOADING → RUNNING
```

**关键设计点**:
- **双重保障机制**:
  - 主动推送: API Gateway更新配置后立即发送控制命令
  - 定期轮询: 30s间隔检查数据库updated_at，防止Kafka消息丢失
- **两阶段检查**:
  - 第一阶段: 只查updated_at时间戳 (快速)
  - 第二阶段: updated_at变化才加载完整配置对比
- **数据库存储**: 统一存储，没有version字段，只保存最新状态
- **通用Topic**: 使用ginkgo.live.control.commands topic，通过command_type区分

**信息类型**: 控制命令 (portfolio.reload)
**触发**: API更新Portfolio配置 / 定期轮询发现变更
**切换时间**: < 30秒 (可配置)

---

### 路径4: Portfolio调度分配

```
Scheduler (定时30秒, 可配置)
    ├─ Redis读取:
    │   ├─ SMEMBERS nodes:active (活跃Node列表)
    │   ├─ heartbeat:node:{id} (心跳检查, TTL=30s)
    │   └─ schedule:plan:{node_id} (当前分配计划)
    ├─ 数据库读取: 待分配Portfolio列表
    ├─ 计算分配算法 (负载均衡/故障恢复)
    ├─ Redis更新: schedule:plan:{node_id}
    │   └─ 写入该Node应该运行的Portfolio ID列表
    └─ Kafka发布: ginkgo.live.schedule.updates
        └─ {node_id, portfolio_ids: [...], timestamp: ...}
    ↓
Kafka (ginkgo.live.schedule.updates)
    ↓
ExecutionNode (Kafka Consumer)
    ├─ 读取: SMEMBERS schedule:plan:{node_id}
    ├─ 对比: planned (调度计划) vs actual (实际运行)
    │   ├─ 新增: planned中有但actual中没有
    │   └─ 移除: actual中有但planned中没有
    ├─ 启动: 新增Portfolio
    │   ├─ 从数据库加载配置
    │   ├─ 初始化Portfolio实例
    │   └─ 启动事件处理
    └─ 停止: 移除Portfolio
        ├─ 状态: RUNNING → STOPPING
        ├─ 等待Queue清空
        └─ 释放资源
```

**关键设计点**:
- **定时调度**: 30秒间隔 (可配置)
- **心跳检测**: 30秒TTL，心跳停止超过30秒判定Node离线
- **分配算法**: 负载均衡 + 故障恢复
- **Redis存储**: schedule:plan:{node_id} 存储每个Node的Portfolio分配计划
- **增量更新**: ExecutionNode对比planned vs actual，只处理差异部分

**信息类型**: 调度计划更新
**频率**: 每30秒 (可配置) + 事件触发
**故障检测**: 30秒心跳超时 (可配置)

---

### 路径5: 兴趣集同步

```
ExecutionNode (汇总所有Portfolio兴趣集)
    ├─ Portfolio变更时主动上报
    │   ├─ 新增Portfolio
    │   ├─ 删除Portfolio
    │   └─ Portfolio配置更新
    └─ 定期上报 (60s, 可配置)
        └─ Kafka.publish("system.events",
                         {event_type: "interest.update",
                          codes: ["000001.SZ", "000002.SZ", ...],  # 全量codes列表
                          node_id: "execution_node_001"})

LiveCore.Data
    ├─ 消费 ginkgo.live.system.events (event_type="interest.update")
    │   └─ 更新订阅列表（只增不减，记录所有出现过的code）
    ├─ 启动时主动请求
    │   └─ Kafka.publish("ginkgo.live.system.events",
    │                    {event_type: "interest.sync_request",
    │                     source: "livecore_data"})
    ├─ 定时清理 + 重同步 (8h, 可配置)
    │   ├─ 加锁: 避免多个清理逻辑同时触发
    │   ├─ 拿到当前所有活跃节点: SMEMBERS nodes:active
    │   ├─ 发送同步请求
    │   │   └─ Kafka.publish("ginkgo.live.system.events",
    │   │                    {event_type: "interest.sync_request",
    │   │                     source: "livecore_data"})
    │   ├─ 等待所有ExecutionNode响应 (超时30s, 可配置)
    │   │   ├─ 使用Event.wait()同步等待
    │   │   ├─ 收集所有响应到responses列表
    │   │   └─ 超时则不更新，进入重试逻辑
    │   ├─ 拿到最新codes后更新订阅列表
    │   └─ 重试机制: 最多3次
    └─ 收到Node离线通知时触发清理
        └─ 消费 ginkgo.live.system.events (event_type="node.offline")
            └─ 清理该Node的codes

ExecutionNode (响应同步请求)
    └─ 消费 ginkgo.live.system.events (event_type="interest.sync_request")
        └─ Kafka.publish("ginkgo.live.system.events",
                         {event_type: "interest.update",
                          codes: self.get_all_interest_codes(),  # 全量codes
                          node_id: self.id})

Kafka (ginkgo.live.system.events)
    ├─ interest.update: ExecutionNode上报兴趣集
    ├─ interest.sync_request: Data请求同步
    └─ node.offline: Scheduler发布Node离线通知
    ↓
LiveCore.Data / ExecutionNode (消费相应消息)
```

**关键设计点**:
- **三种上报机制**:
  1. 主动上报: Portfolio变更时立即上报
  2. 定期上报: 60秒间隔全量上报
  3. 响应请求: 收到sync_request时立即响应
- **定时清理机制** (8小时间隔, 可配置):
  - 加锁避免并发
  - Event.wait()同步等待响应
  - 超时30秒后重试，最多3次
  - 拿到最新响应后更新订阅列表
- **启动时请求**: Data启动时立即发送sync_request
- **Node离线清理**: 收到node.offline通知时清理该Node的codes
- **只增不减**: Data订阅列表只增加，不删除codes（除非Node离线或定时清理）
- **通用Topic**: 使用ginkgo.live.system.events topic，通过event_type区分
- **ExecutionNode上报**: 只发送codes列表，不发送完整的interest_map

**信息类型**: 兴趣集更新 / 同步请求 / Node离线
**频率**:
- 主动上报: Portfolio变更时
- 定期上报: 60秒 (可配置)
- 定时清理: 8小时 (可配置)
- 启动请求: Data启动时

---

### 路径6: 心跳上报 (Redis直接写入，不经过Kafka)

```
ExecutionNode (每10秒, 可配置)
    └─ Redis SET heartbeat:node:{id} "alive" EX 30
        ├─ key: heartbeat:node:{node_id}
        ├─ value: "alive"
        └─ TTL: 30秒 (可配置)

Scheduler (每30秒, 可配置)
    ├─ SMEMBERS nodes:active (获取所有活跃Node)
    ├─ 检查心跳过期
    │   ├─ 遍历 nodes:active 中的每个node_id
    │   ├─ 检查 EXISTS heartbeat:node:{node_id}
    │   ├─ 如果不存在 (TTL过期)
    │   │   ├─ 判定Node离线
    │   │   ├─ 从 nodes:active 中移除
    │   │   └─ Kafka发布: ginkgo.live.system.events
    │   │       └─ {event_type: "node.offline",
    │   │          node_id: "...",
    │   │          timestamp: "..."}
    │   └─ 触发Portfolio重新调度 (路径4)
    └─ 更新调度计划
        └─ 将离线Node的Portfolio分配到其他Node
```

**关键设计点**:
- **直接写Redis**: 不经过Kafka，减少延迟
- **心跳TTL**: 30秒 (可配置)
- **检测频率**: 30秒 (可配置)
- **离线处理**: Node离线后发布node.offline事件到ginkgo.live.system.events
  - Data收到后清理该Node的兴趣集
  - Scheduler触发Portfolio重新调度
- **无状态**: ExecutionNode重启后自动重新注册

**信息类型**: 心跳状态
**频率**:
- ExecutionNode上报: 每10秒 (可配置)
- Scheduler检测: 每30秒 (可配置)
- 心跳TTL: 30秒 (可配置)

**故障检测**: 30秒心跳超时 (可配置)

---

## Kafka Topic信息流总览

### 模块 × Topic × EventType 详细矩阵

#### 1. ginkgo.live.market.data (市场数据)

| 模块 | 角色 | 消息类型 |
|------|------|---------|
| **LiveCore.Data** | **发布** | EventPriceUpdate |
| **ExecutionNode** | **订阅** | 全部 |

---

#### 2. ginkgo.live.orders.submission (订单提交)

| 模块 | 角色 | 说明 |
|------|------|------|
| **ExecutionNode** | **发布** | Portfolio生成的订单 |
| **LiveEngine** | **订阅** | 接收订单并执行 |

#### 3. ginkgo.live.orders.feedback (订单回报)

| 模块 | 角色 | 消息类型 |
|------|------|---------|
| **LiveEngine** | **发布** | `ack`, `partially_filled`, `filled` |
| **ExecutionNode** | **订阅** | 根据portfolio_id路由到Portfolio |

---

#### 4. ginkgo.live.control.commands (控制命令)

| 模块 | 角色 | command_type |
|------|------|-------------|
| **API Gateway** | **发布** | `portfolio.reload`, `portfolio.start`, `portfolio.stop`, `engine.start`, `engine.stop` |
| **ExecutionNode** | **订阅** | `portfolio.*` |
| **LiveEngine** | **订阅** | `engine.*` |

---

#### 5. ginkgo.live.schedule.updates (调度计划)

| 模块 | 角色 | 消息格式 |
|------|------|---------|
| **Scheduler** | **发布** | `{node_id, portfolio_ids, timestamp}` |
| **ExecutionNode** | **订阅** | 过滤自己的node_id |

---

#### 6. ginkgo.live.system.events (系统事件)

| 模块 | 角色 | event_type |
|------|------|-----------|
| **ExecutionNode** | **发布** | `interest.update` |
| **ExecutionNode** | **订阅** | `interest.sync_request` |
| **LiveCore.Data** | **发布** | `interest.sync_request` |
| **LiveCore.Data** | **订阅** | `interest.update`, `node.offline` |
| **Scheduler** | **发布** | `node.offline` |

---

#### 7. ginkgo.alerts (异常告警与通知)

| 模块 | 角色 | 消息类型 |
|------|------|---------|
| **所有模块** | **发布** | Queue满、超时、组件故障、数据异常等 |
| **Notification系统** | **订阅** | 接收告警并通知用户 |

---

### 汇总矩阵

| Topic \ 模块 | API Gateway | LiveCore.Data | LiveEngine | ExecutionNode | Scheduler | Notification |
|--------------|-------------|---------------|------------|---------------|-----------|--------------|
| **ginkgo.live.market.data** | - | 发布 | - | 订阅 | - | - |
| **ginkgo.live.orders.submission** | - | - | 订阅 | 发布 | - | - |
| **ginkgo.live.orders.feedback** | - | - | 发布 | 订阅 | - | - |
| **ginkgo.live.control.commands** | 发布 | - | 订阅 | 订阅 | - | - |
| **ginkgo.live.schedule.updates** | - | - | - | 订阅 | 发布 | - |
| **ginkgo.live.system.events** | - | 发布/订阅 | - | 发布/订阅 | 发布 | - |
| **ginkgo.alerts** | 发布 | 发布 | 发布 | 发布 | 发布 | 订阅 |

---

## Redis信息流总览

| Key Pattern | 写入者 | 读取者 | 信息类型 | TTL |
|-------------|--------|--------|---------|-----|
| **heartbeat:node:{id}** | ExecutionNode | Scheduler | 心跳状态 | 30秒 (可配置) |
| **nodes:active** | ExecutionNode<br>Scheduler | Scheduler<br>API Gateway | 活跃Node集合 | 持久 |
| **schedule:plan:{node_id}** | Scheduler | ExecutionNode | Portfolio分配计划 | 持久 |
| **portfolio:{id}:status** | ExecutionNode | API Gateway<br>Scheduler | Portfolio状态<br>(RUNNING/STOPPING/RELOADING) | 持久 |
| **engine:live:*:status** | LiveEngine | API Gateway | 引擎状态 | 持久 |

---

## 关键状态流转

### Portfolio状态流转
```
CREATED (数据库创建)
    ↓
RUNNING (ExecutionNode启动)
    ├─ 正常处理事件
    └─ 生成订单/持仓
    ↓
STOPPING (配置变更/迁移)
    ├─ 缓存消息到buffer
    ├─ 等待Queue清空
    └─ 停止处理新事件
    ↓
STOPPED (优雅停止完成)
    ├─ 加载新配置
    └─ 重新初始化
    ↓
RELOADING (重载中)
    ├─ 重放缓存消息
    └─ 恢复处理
    ↓
RUNNING (恢复正常)
    ↓
ERROR (异常)
    └─ Scheduler重新分配
```

### Node状态流转
```
启动
    ↓
REGISTERED (Redis注册: nodes:active)
    ↓
ACTIVE (发送心跳: heartbeat:node:{id})
    ├─ 正常运行Portfolio
    └─ 每10秒刷新心跳
    ↓
INACTIVE (心跳停止 > 30秒)
    ├─ Scheduler检测到
    └─ Portfolio迁移到其他Node
    ↓
REMOVED (从nodes:active移除)
```

---

## 信息流转优先级

### 信号处理优先级
```
1. 主动风控信号 (止损/止盈) → 最高优先级
2. 被动风控拦截/调整
3. 策略信号 → 正常优先级
```

### 事件处理优先级
```
1. 控制事件 (CONFIG_UPDATES, SCHEDULE_UPDATES) → 最高
2. 订单回报事件 (ORDER_ACK, FILLED) → 高
3. 市场数据事件 (PRICE_UPDATE) → 正常
```

---

## 关键时序要求

| 信息流 | 延迟要求 | 说明 |
|--------|---------|------|
| PriceUpdate → Signal | < 200ms | SC-014 |
| Signal → Order | < 100ms | SC-016 |
| Order → Kafka | < 100ms | SC-016 |
| 配置变更切换 | < 30秒 | SC-009 |
| 故障恢复 | < 60秒 | SC-010 |
| 心跳检测 | 30秒超时 | 系统设计 |

---

## 信息一致性保证

### 1. Kafka消息可靠性
```python
# Producer配置
enable.idempotence = true  # 幂等性
acks = "all"               # 所有副本确认
retries = 3                # 重试3次

# Consumer配置
enable.auto.commit = false  # 手动提交
auto.offset.reset = "earliest"  # 从最早开始
```

### 2. Redis状态一致性
```python
# 心跳机制
SET heartbeat:node:{id} "alive" EX 30  # 30秒TTL

# 连接池
ConnectionPool(
    retry_on_timeout = True,
    socket_connect_timeout = 5
)
```

### 3. 数据库持久化
```python
@retry(max_try=3, delay=1)
def save_portfolio_state():
    db.execute("UPDATE portfolios SET ...")
    db.commit()
```

---

## 总结

**核心信息流**:
1. **市场数据流**: Data → Kafka(ginkgo.live.market.data) → ExecutionNode → Portfolio (最高频，~5000条/秒)
2. **订单流**: Portfolio → ExecutionNode.submit_order() → Kafka(orders.cn) → LiveEngine → TradeGateway → 交易所
3. **回报流**: 交易所 → TradeGateway → LiveEngine → Kafka(orders.cn) → ExecutionNode → Portfolio (同步写数据库)
4. **控制流**: API Gateway → Kafka(ginkgo.live.control.commands) → ExecutionNode (配置更新、控制命令)
5. **调度流**: Scheduler → Kafka(ginkgo.live.schedule.updates) → ExecutionNode (Portfolio分配)
6. **兴趣集流**: ExecutionNode → Kafka(ginkgo.live.system.events) → Data (订阅同步)
7. **状态流**: ExecutionNode → Redis(heartbeat) → Scheduler (心跳检测)
8. **告警流**: 各模块 → Kafka(ginkgo.alerts) → 通知系统

**关键设计决策**:
- **两级警告机制**: 70%警告，95%丢弃消息 (可配置间隔)
- **Order传递方式**: Portfolio直接调用ExecutionNode.submit_order()，不经过额外队列
- **订单双向Topic**:
  - ginkgo.live.orders.submission: ExecutionNode → LiveEngine
  - ginkgo.live.orders.feedback: LiveEngine → ExecutionNode
- **订单回报同步持久化**: Portfolio收到订单回报后同步写入数据库
- **配置更新双重保障**: Kafka主动推送 + 定期轮询数据库 (30s, 可配置)
- **通用Topic设计**:
  - ginkgo.live.control.commands: 所有控制命令
  - ginkgo.live.system.events: 系统事件 (兴趣集同步、Node离线等)
  - ginkgo.alerts: 异常告警 (各模块异常、通知消息)
- **兴趣集同步三种机制**:
  1. 主动上报 (Portfolio变更时)
  2. 定期上报 (60s, 可配置)
  3. 定时清理+重同步 (8h, 可配置，加锁、超时、重试3次)
- **心跳直接写Redis**: 不经过Kafka，减少延迟 (10s上报，30s检测，均可配置)
- **Event.wait()同步机制**: 用于定时清理等待ExecutionNode响应

**架构特点**:
- Kafka: 事件驱动异步通信，解耦组件
  - 实盘专用topic (6个): ginkgo.live.market.data, ginkgo.live.orders.submission, ginkgo.live.orders.feedback, ginkgo.live.control.commands, ginkgo.live.schedule.updates, ginkgo.live.system.events
  - 全局topic (1个): ginkgo.alerts (跨实盘/回测)
  - 统一命名规范: `ginkgo.live.*` 实盘专用, `ginkgo.*` 全局
- Redis: 状态存储和心跳检测 (TTL自动过期)
- 数据库: 持久化和配置 (无version，只保存最新状态)
- 每Portfolio一线程: 无锁、状态隔离
- 消息缓存机制: 优雅重启不丢失数据
- 所有间隔可配置: 便于根据实际情况调优
- 告警统一接入: ginkgo.alerts topic，Notification系统订阅
