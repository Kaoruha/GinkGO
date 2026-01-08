# Research & Analysis: 实盘多Portfolio架构支持

**Feature**: 007-live-trading-architecture
**Date**: 2026-01-04
**Status**: Completed

本文档记录实盘交易架构设计过程中的技术研究、架构决策和技术选型分析。

---

## 架构设计研究

### 1. 分布式架构选型

#### 研究问题：实盘交易应该采用什么样的分布式架构？

**选项对比**:

| 架构模式 | 优点 | 缺点 | 适用性 |
|---------|------|------|--------|
| **集中式架构** | 部署简单，状态管理容易 | 单点故障，扩展性差 | ❌ 不适合实盘高可用 |
| **微服务架构** | 独立部署，技术栈灵活 | 复杂度高，运维成本高 | ⚠️ 过度设计 |
| **事件驱动架构** | 解耦，异步，可扩展 | 调试复杂，消息一致性 | ✅ **推荐** |
| **Actor模型** | 天然并发，容错性强 | 学习曲线陡峭 | ⚠️ 暂不考虑 |

**决策**: 采用**事件驱动架构**，基于Kafka消息总线实现组件解耦和异步通信。

**理由**:
1. 符合Ginkgo现有的事件驱动设计（EventPriceUpdate → Signal → Order）
2. Kafka天然支持水平扩展和故障恢复
3. 可以逐步从单机到分布式演进

---

### 2. 组件划分研究

#### 研究问题：如何划分实盘交易系统的组件？

**设计原则**:
- **单一职责**: 每个组件只负责一个核心功能
- **无状态设计**: 便于水平扩展和故障恢复
- **通信解耦**: 通过Kafka异步通信，避免直接依赖

**最终组件划分**:

```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (控制层)                     │
│  职责: HTTP API + 认证鉴权 + 请求路由 + 限流防刷              │
└────────────────────┬────────────────────────────────────────┘
                     │ Kafka/Redis
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   LiveCore (业务逻辑层)                      │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │   Data    │  │ TradeGate │  │LiveEngine│  │Scheduler │ │
│  │  数据源   │  │ 交易网关  │  │ 实盘引擎 │  │ 调度器  │ │
│  └───────────┘  └───────────┘  └──────────┘  └──────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │ Kafka
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                ExecutionNode (执行层 - x10)                  │
│  职责: 运行3-5个Portfolio实例 + 订阅Kafka + interest_map    │
└─────────────────────────────────────────────────────────────┘
```

**组件职责明确**:
- **API Gateway**: 纯控制层，不处理业务逻辑
- **LiveCore.Data**: 数据源管理，发布市场数据到Kafka
- **LiveCore.TradeGateway**: 交易执行，调用券商API
- **LiveCore.LiveEngine**: 订单处理，订阅Kafka订单Topic
- **LiveCore.Scheduler**: 调度决策，分配Portfolio到ExecutionNode
- **ExecutionNode**: Portfolio运行，订阅Kafka市场数据

---

### 3. Kafka Topic设计研究

#### 研究问题：如何设计Kafka Topic结构？

**关键考虑**:
1. **Topic数量**: 不能太多（管理成本），不能太少（耦合严重）
2. **分区策略**: 如何保证消息顺序和负载均衡
3. **命名规范**: 统一命名，便于理解和扩展

**设计演进**:

**方案A: 按股票分区（Rejected）**
```
Topic: market.data.000001.SZ
Topic: market.data.000002.SZ
...（5000个Topic）
```
❌ 问题: Topic数量爆炸，管理成本高

**方案B: 单一市场Topic（Rejected）**
```
Topic: market.data (所有股票混在一起)
```
❌ 问题: 无法按市场隔离，A股/港股/美股混在一起

**方案C: 市场级别Topic（Accepted）✅**
```
Topic: ginkgo.live.market.data (A股)
Topic: ginkgo.live.market.data.hk (港股)
Topic: ginkgo.live.market.data.us (美股)
Topic: ginkgo.live.market.data.futures (期货)
```
✅ 优点: 清晰的隔离，合理的数量（3-10个Topic）

**最终Topic命名规范**:
- **实盘专用**: `ginkgo.live.*` (如 ginkgo.live.market.data)
- **全局共享**: `ginkgo.*` (如 ginkgo.alerts，跨实盘/回测)

**完整Topic列表**:
1. `ginkgo.live.market.data` - A股市场数据
2. `ginkgo.live.orders.submission` - 订单提交
3. `ginkgo.live.orders.feedback` - 订单回报
4. `ginkgo.live.control.commands` - 控制命令
5. `ginkgo.live.schedule.updates` - 调度计划
6. `ginkgo.live.system.events` - 系统事件
7. `ginkgo.alerts` - 异常告警（全局）

---

### 4. ExecutionNode并发模型研究

#### 研究问题：ExecutionNode如何并发处理多个Portfolio？

**关键挑战**:
- 如何保证每个Portfolio独立处理（状态隔离）
- 如何高效路由市场数据到对应的Portfolio
- 如何防止慢Portfolio阻塞其他Portfolio

**方案对比**:

| 方案 | 优点 | 缺点 | 结论 |
|------|------|------|------|
| **单线程顺序处理** | 简单，无锁 | 慢Portfolio阻塞全部 | ❌ |
| **线程池处理** | 动态扩展 | 复杂，锁竞争 | ⚠️ |
| **每Portfolio一线程** | 简单，隔离性好 | 线程数固定（3-5个） | ✅ **推荐** |

**最终方案**: **单Kafka消费线程 + 多PortfolioProcessor线程**

```
ExecutionNode内部架构:
┌─────────────────────────────────────────────────────────┐
│ Kafka Consumer Thread (单线程)                          │
│ └─ 快速消费消息，路由到PortfolioProcessor Queue        │
└─────────────────────────────────────────────────────────┘
         │ interest_map路由
         ↓
┌─────────────────────────────────────────────────────────┐
│ PortfolioProcessor Thread Pool (每个Portfolio一线程)    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Thread-A │  │ Thread-B │  │ Thread-C │             │
│  │ Queue    │  │ Queue    │  │ Queue    │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
```

**关键设计**:
1. **Kafka消费线程**: 专注快速消费和路由，不处理业务逻辑
2. **interest_map**: `{code: [portfolio_ids]}`，O(1)查找
3. **PortfolioProcessor**: 每个Portfolio独立线程，独立Queue，完全并行处理

**性能分析**（5000条/秒场景）:
- Kafka消费线程: ~10ms路由500条消息
- Portfolio并行处理: 3个Portfolio同时处理，总时间=max(各自处理时间)
- 端到端延迟: ~100-200ms

---

### 5. InterestMap机制研究

#### 研究问题：如何高效地将市场数据路由到订阅的Portfolio？

**设计需求**:
1. 快速查找：O(1)时间复杂度
2. 动态更新：Portfolio启动/停止时更新
3. 线程安全：Kafka消费线程和PortfolioProcessor线程并发访问

**数据结构设计**:

```python
interest_map: Dict[str, List[str]] = {
    "000001.SZ": ["portfolio_1_uuid", "portfolio_3_uuid"],
    "000002.SZ": ["portfolio_2_uuid"],
    ...
}
```

**使用场景**:
```python
# Kafka消费线程调用
def route_message(event: EventPriceUpdate):
    code = event.code

    # 1. 查找订阅的Portfolio（O(1)）
    with self.interest_map_lock:
        portfolio_ids = self.interest_map.get(code, []).copy()

    # 2. 快速分发到各Processor Queue（非阻塞）
    for pid in portfolio_ids:
        processor = self.processors[pid]
        if not processor.queue.full():
            processor.queue.put(event, block=False)
```

**兴趣集同步机制**:
1. **主动上报**: Portfolio变更时立即上报
2. **定期上报**: 60秒间隔全量上报
3. **定时清理+重同步**: 8小时间隔，使用Event.wait()同步等待

---

### 6. Backpressure反压机制研究

#### 研究问题：当Portfolio处理速度 < 消息到达速度时，如何防止系统崩溃？

**三种实现方式**:

**方式1: 丢弃消息（激进反压）**
- 触发: Queue满（1000条）
- 行为: 拒绝接收新消息，直接丢弃
- 优点: ExecutionNode不会被阻塞，内存不会溢出
- 缺点: 会丢失数据
- 适用: 允许部分数据丢失的场景

**方式2: 阻塞等待（温和反压）**
- 触发: Queue满
- 行为: 阻塞等待Queue有空间（最长1秒）
- 优点: 不丢失数据（短期）
- 缺点: ExecutionNode会被阻塞，影响其他Portfolio
- 适用: 数据完整性要求高的场景

**方式3: 监控告警 + 优雅降级（推荐）✅**
- 触发: Queue使用率超过70%
- 行为:
  - 70-90%: 触发告警，记录慢日志
  - >90%: 丢弃消息，触发严重告警
- 优点: 兼顾性能和可靠性
- 适用: 生产环境推荐方案

**最终方案**: **两级警告机制**
1. **70%阈值**: `queue.qsize() >= 700` → 发送警告，5分钟间隔
2. **95%阈值**: `queue.qsize() >= 950` → 丢弃最新消息 + 发送警告，1分钟间隔

---

### 7. Portfolio状态管理研究

#### 研究问题：如何管理Portfolio的生命周期状态？

**状态机设计**:

```python
class PortfolioState(Enum):
    CREATED = "created"      # 数据库创建
    RUNNING = "running"      # 运行中
    STOPPING = "stopping"    # 停止中（等待队列清空）
    STOPPED = "stopped"      # 已停止
    RELOADING = "reloading"  # 重载中（配置更新）
    ERROR = "error"          # 异常
```

**状态流转**:
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
```

**优雅重启流程**:
```
1. 用户通过API更新Portfolio配置
   POST /api/portfolio/portfolio_001

2. API Gateway更新数据库
   UPDATE portfolios SET config = {...}, updated_at = NOW()

3. API Gateway发送Kafka通知
   PRODUCE ginkgo.live.control.commands {
     "command_type": "portfolio.reload",
     "target_id": "portfolio_001",
     "reason": "user_api_update"
   }

4. ExecutionNode收到通知
   CONSUME ginkgo.live.control.commands

5. ExecutionNode执行优雅重启流程
   ├─ 状态: RUNNING → STOPPING
   ├─ 缓存Kafka消息到buffer
   ├─ 等待Queue清空 (timeout 30s)
   ├─ 从数据库加载新配置
   ├─ 重新初始化Portfolio
   ├─ 重放缓存消息 (按时间戳顺序)
   └─ 状态: RELOADING → RUNNING
```

---

### 8. 数据持久化策略研究

#### 研究问题：如何选择数据持久化方案？

**数据分类**:

| 数据类型 | 存储选择 | 理由 |
|---------|---------|------|
| **Portfolio配置** | MySQL | 关系数据，事务支持 |
| **Portfolio状态** | Redis | 热数据，快速查询 |
| **Portfolio历史** | ClickHouse | 时序数据，分析查询 |
| **ExecutionNode心跳** | Redis (TTL) | 临时数据，自动过期 |
| **调度计划** | Redis | 快速查询，Set结构 |
| **通知记录** | MongoDB | 文档数据，7天TTL |

**关键设计决策**:
1. **Portfolio配置**: MySQL存储，支持版本管理（updated_at）
2. **Portfolio状态**: Redis缓存，快速查询当前状态
3. **订单回报**: Portfolio收到后同步写入数据库（保证一致性）
4. **心跳机制**: Redis直接写入，TTL=30秒（不经过Kafka）

---

## 技术选型总结

### 核心技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.12.8 | 主要开发语言 |
| **Kafka** | 2.8+ | 消息总线，组件通信 |
| **Redis** | 7.0+ | 状态存储，缓存，心跳 |
| **MySQL** | 8.0+ | Portfolio配置，关系数据 |
| **ClickHouse** | 23.0+ | 时序数据，历史记录 |
| **MongoDB** | 4.4+ | 通知记录，文档数据 |

### 关键依赖库

| 库 | 用途 |
|------|------|
| **kafka-python** | Kafka客户端 |
| **redis-py** | Redis客户端 |
| **pymongo** | MongoDB客户端 |
| **Pydantic** | 数据验证 |
| **Typer** | CLI框架 |
| **Rich** | 终端美化 |

---

## 架构原则确认

### 设计原则

1. **事件驱动**: 所有组件通过Kafka异步通信
2. **无状态设计**: 组件本身不存储状态，所有状态持久化到数据库
3. **水平可扩展**: ExecutionNode可水平扩展至10+实例
4. **故障隔离**: 单个Portfolio/ExecutionNode故障不影响其他
5. **优雅降级**: Kafka不可用时自动降级为同步发送

### 性能目标

| 指标 | 目标值 |
|------|--------|
| PriceUpdate → Signal | < 200ms |
| Signal → Order | < 100ms |
| Order → Kafka | < 100ms |
| 配置变更切换 | < 30秒 |
| 故障恢复 | < 60秒 |
| 心跳检测 | 30秒超时 |

---

## 未解决问题（TODO）

### 需要进一步研究

1. **Kafka分区策略**: 如何保证同一股票的消息顺序？
2. **幂等处理**: Kafka消息重复投递时，Portfolio如何幂等处理？
3. **时钟同步**: 分布式环境下如何保证事件时间戳一致性？
4. **内存管理**: 长时间运行如何避免内存泄漏？
5. **监控指标**: 需要采集哪些关键指标？（Prometheus集成）

### 未来优化方向

1. **WebSocket推送**: 替代轮询，提供实时状态更新
2. **动态分区**: Kafka Topic根据负载动态调整分区数
3. **智能路由**: 基于Portfolio负载动态调整调度策略
4. **容错增强**: Portfolio状态快照 + 定期恢复演练

---

## 参考资料

### 内部文档
- `/specs/007-live-trading-architecture/spec.md` - 完整功能规格
- `/specs/007-live-trading-architecture/information-flow.md` - 信息流转视图
- `/specs/007-live-trading-architecture/scenarios.md` - 所有场景列表

### 外部参考
- Kafka官方文档: https://kafka.apache.org/documentation/
- Redis最佳实践: https://redis.io/topics/best-practices
- 事件驱动架构: https://martinfowler.com/articles/201701-event-driven.html

---

**结论**: 本文档确认了实盘交易架构的核心技术方案，为后续实施提供了明确的指导。所有关键设计决策已经经过充分讨论和验证，可以进入下一阶段的任务分解。
