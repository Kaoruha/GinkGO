# Task Breakdown: 实盘多Portfolio架构支持

**Feature**: 007-live-trading-architecture
**Branch**: `007-live-trading-architecture`
**Generated**: 2026-01-04
**Updated**: 2026-01-04 (重构为总分结构)

---

## 📊 总体统计

| 指标 | 数值 |
|------|------|
| 总阶段数 | 8 |
| 总任务数 | 74 |
| 已完成任务 | 8 |
| 进行中任务 | 0 |
| 待办任务 | 66 |
| 完成进度 | 10.8% |
| 预计工期 | 6-8周 (MVP 2-3周) |

---

## 🎯 阶段概览

### Phase 1: Setup (项目初始化)
- **状态**: ✅ 已完成
- **任务数**: 8 (T001-T008)
- **优先级**: P1
- **预计工期**: 1周
- **详细文档**: [tasks_phase1.md](./tasks_phase1.md)
- **验收标准**:
  - [x] 所有依赖库已安装
  - [x] Kafka集群可以连接并创建topic
  - [x] MySQL/ClickHouse/Redis/MongoDB数据库可以连接
  - [x] 项目结构已创建

---

### Phase 2: Foundational (核心基础设施)
- **状态**: ⚪ 未开始
- **任务数**: 8 (T009-T016)
- **优先级**: P1
- **预计工期**: 1周
- **依赖**: Phase 1完成
- **详细文档**: [tasks_phase2.md](./tasks_phase2.md)
- **验收标准**:
  - [ ] Kafka Producer/Consumer可以正常发送和接收消息
  - [ ] 实盘交易事件类已创建
  - [ ] 数据模型已就绪
  - [ ] Portfolio基类已扩展支持实盘交易

---

### Phase 3: User Story 1 - 单Portfolio实盘运行 (P1)
- **状态**: ⚪ 未开始
- **任务数**: 14 (T017-T030)
- **优先级**: P1 (MVP)
- **预计工期**: 2-3周
- **依赖**: Phase 1-2完成
- **详细文档**: [tasks_phase3.md](./tasks_phase3.md)
- **验收标准**:
  - [ ] ExecutionNode可以启动并加载Portfolio配置
  - [ ] ExecutionNode订阅Kafka market.data topic并接收EventPriceUpdate
  - [ ] Portfolio.on_price_update()方法可以处理事件并生成Signal
  - [ ] Signal通过Sizer计算生成Order
  - [ ] Order通过ExecutionNode.submit_order()提交到Kafka orders.submission topic
  - [ ] LiveEngine订阅orders.submission topic并处理订单
  - [ ] TradeGateway模拟执行订单并返回EventOrderFilled
  - [ ] Portfolio.on_order_filled()更新持仓和现金
  - [ ] 持仓和现金同步写入ClickHouse和MySQL
  - [ ] 端到端延迟 < 200ms

---

### Phase 4: User Story 2 - 多Portfolio并行运行 (P2)
- **状态**: ⚪ 未开始
- **任务数**: 10 (T031-T040)
- **优先级**: P2
- **预计工期**: 1-2周
- **依赖**: Phase 3完成
- **详细文档**: [tasks_phase4.md](./tasks_phase4.md)
- **验收标准**:
  - [ ] ExecutionNode可以加载和运行3-5个Portfolio
  - [ ] 每个Portfolio有独立的PortfolioProcessor线程
  - [ ] InterestMap机制正确路由消息到对应的Portfolio
  - [ ] Portfolio之间的状态完全隔离
  - [ ] Backpressure机制正常工作（70%警告，95%丢弃）

---

### Phase 5: User Story 3 - Portfolio动态调度 (P3)
- **状态**: ⚪ 未开始
- **任务数**: 16 (T041-T056)
- **优先级**: P3
- **预计工期**: 2-3周
- **依赖**: Phase 3-4完成
- **详细文档**: [tasks_phase5.md](./tasks_phase5.md)
- **验收标准**:
  - [ ] Scheduler可以定期执行调度算法（每30秒）
  - [ ] ExecutionNode心跳正常（每10秒上报，TTL=30秒）
  - [ ] Portfolio配置更新时触发优雅重启（< 30秒）
  - [ ] ExecutionNode故障时Portfolio自动迁移到健康Node（< 60秒）
  - [ ] 手动迁移Portfolio功能正常

---

### Phase 6: User Story 4 - 实时风控执行 (P2)
- **状态**: ⚪ 未开始
- **任务数**: 4 (T057-T060)
- **优先级**: P2
- **预计工期**: 1周
- **依赖**: Phase 3完成
- **详细文档**: [tasks_phase6.md](./tasks_phase6.md)
- **验收标准**:
  - [ ] 风控模块可以集成到Portfolio
  - [ ] 订单提交前依次通过所有风控模块检查
  - [ ] 风控可以拦截订单并调整订单量
  - [ ] 风控可以生成平仓信号

---

### Phase 7: User Story 5 - 系统监控 (P3)
- **状态**: ⚪ 未开始
- **任务数**: 8 (T065-T072)
- **优先级**: P3
- **预计工期**: 1周
- **依赖**: Phase 3-4完成
- **详细文档**: [tasks_phase7.md](./tasks_phase7.md)
- **验收标准**:
  - [ ] ExecutionNode心跳正常上报
  - [ ] Portfolio状态实时更新到Redis
  - [ ] Queue满时触发通知（使用现有notification系统）
  - [ ] API Gateway提供监控查询接口

---

### Phase 8: Polish & Cross-Cutting Concerns
- **状态**: ⚪ 未开始
- **任务数**: 6 (T075-T080)
- **优先级**: -
- **预计工期**: 1周
- **依赖**: Phase 3-7完成
- **详细文档**: [tasks_phase8.md](./tasks_phase8.md)
- **验收标准**:
  - [ ] 所有代码符合Ginkgo编码规范（类型注解、装饰器、头部注释）
  - [ ] 所有测试通过（单元测试、集成测试、数据库测试、网络测试）
  - [ ] 文档完整（API文档、架构文档、快速开始指南）
  - [ ] 性能达到目标（端到端延迟 < 200ms）

---

## 📋 完整任务列表

### Phase 1: Setup (T001-T008)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T001 | - | 安装Python依赖库到requirements.txt | requirements.txt | ✅ 完成 |
| T002 | [P] | 创建实盘交易模块目录结构 | 新增: workers/execution_node/, livecore/; 复用: trading/engines/, trading/gateway/, trading/events/, api/ | ✅ 完成 |
| T003 | [P] | 扩展Kafka topic配置 | src/ginkgo/data/drivers/ginkgo_kafka.py | ✅ 完成 |
| T004 | [P] | 编写Kafka连接测试脚本 | tests/network/live/test_kafka_connection.py | ✅ 完成 |
| T005 | [P] | 创建数据库配置模板 | ~/.ginkgo/config.yml | ✅ 完成 |
| T006 | [P] | 编写数据库连接测试脚本 | tests/network/live/test_database_connection.py | ✅ 完成 |
| T007 | - | 创建.env.example模板文件 | .env.example | ✅ 完成 |
| T008 | - | 编写Docker Compose配置文件 | (Kafka/Redis已运行) | ✅ 完成 |

**详细任务**: [tasks_phase1.md](./tasks_phase1.md)

---

### Phase 2: Foundational (T009-T016)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T009 | [P] | 验证EventPriceUpdate和EventOrderPartiallyFilled可复用 | src/ginkgo/trading/events/ | ⚪ 待办 |
| T010 | [P] | 创建EventControlCommand事件类 | src/ginkgo/trading/events/event_control_command.py | ⚪ 待办 |
| T011 | [P] | 验证MPortfolio和MPortfolioFileMapping可支持实盘交易 | src/ginkgo/data/models/model_portfolio.py | ⚪ 待办 |
| T012 | [P] | 验证PortfolioCRUD可支持实盘交易 | src/ginkgo/data/crud/portfolio_crud.py | ⚪ 待办 |
| T013 | [P] | 验证MPosition模型可复用于实盘交易 | src/ginkgo/data/models/model_position.py | ⚪ 待办 |
| T014 | - | 验证GinkgoProducer可支持实盘交易（需改造acks） | src/ginkgo/data/drivers/ginkgo_kafka.py | ⚪ 待办 |
| T015 | - | 验证GinkgoConsumer可支持实盘交易 | src/ginkgo/data/drivers/ginkgo_kafka.py | ⚪ 待办 |
| T016 | - | 编写Kafka集成测试 | tests/network/live/test_kafka_integration.py | ⚪ 待办 |

**详细任务**: [tasks_phase2.md](./tasks_phase2.md)

---

### Phase 3: User Story 1 - 单Portfolio实盘运行 (T017-T030)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T017 | [P] | 创建ExecutionNode主类 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T018 | [P] | 创建PortfolioProcessor线程类 | src/ginkgo/workers/execution_node/portfolio_processor.py | ⚪ 待办 |
| T019 | - | 实现ExecutionNode.load_portfolio()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T020 | - | 实现ExecutionNode.subscribe_market_data()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T021 | - | 实现PortfolioProcessor.run()主循环 | src/ginkgo/workers/execution_node/portfolio_processor.py | ⚪ 待办 |
| T022 | [P] | 扩展Portfolio添加on_price_update()方法 | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T023 | [P] | 扩展Portfolio添加on_order_filled()方法 | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T024 | - | 实现Portfolio.sync_state_to_db()方法 | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T025 | [P] | 编写Portfolio事件处理单元测试 | tests/unit/live/test_portfolio_events.py | ⚪ 待办 |
| T026 | - | 实现ExecutionNode.submit_order()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T027 | [P] | 创建LiveCore主入口（多线程容器） | src/ginkgo/livecore/main.py | ⚪ 待办 |
| T028 | [P] | 创建LiveEngine容器线程 | src/ginkgo/livecore/live_engine.py | ⚪ 待办 |
| T029 | [P] | 创建TradeGateway适配器 | src/ginkgo/livecore/trade_gateway_adapter.py | ⚪ 待办 |
| T030 | - | 改造GinkgoProducer的acks=1为acks=all | src/ginkgo/data/drivers/ginkgo_kafka.py | ⚪ 待办 |

**详细任务**: [tasks_phase3.md](./tasks_phase3.md)

---

### Phase 4: User Story 2 - 多Portfolio并行运行 (T031-T040)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T031 | [P] | 创建InterestMap类 | src/ginkgo/workers/execution_node/interest_map.py | ⚪ 待办 |
| T032 | - | 实现InterestMap.add_portfolio()方法 | src/ginkgo/workers/execution_node/interest_map.py | ⚪ 待办 |
| T033 | - | 实现InterestMap.get_portfolios()方法 | src/ginkgo/workers/execution_node/interest_map.py | ⚪ 待办 |
| T034 | - | 实现ExecutionNode.route_message()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T035 | [P] | 创建BackpressureChecker类 | src/ginkgo/workers/execution_node/backpressure.py | ⚪ 待办 |
| T036 | - | 实现BackpressureChecker.check_queue_status()方法 | src/ginkgo/workers/execution_node/backpressure.py | ⚪ 待办 |
| T037 | [P] | 编写Backpressure单元测试 | tests/unit/live/test_backpressure.py | ⚪ 待办 |
| T038 | - | 编写多Portfolio并行处理集成测试 | tests/integration/live/test_multi_portfolio.py | ⚪ 待办 |
| T039 | - | 编写InterestMap路由测试 | tests/integration/live/test_interest_map.py | ⚪ 待办 |
| T040 | - | 编写状态隔离测试 | tests/integration/live/test_state_isolation.py | ⚪ 待办 |

**详细任务**: [tasks_phase4.md](./tasks_phase4.md)

---

### Phase 5: User Story 3 - Portfolio动态调度 (T041-T056)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T041 | [P] | 创建Scheduler主类 | src/ginkgo/livecore/scheduler.py | ⚪ 待办 |
| T042 | - | 实现Scheduler.assign_portfolios()方法 | src/ginkgo/livecore/scheduler.py | ⚪ 待办 |
| T043 | - | 实现Scheduler.publish_schedule_update()方法 | src/ginkgo/livecore/scheduler.py | ⚪ 待办 |
| T044 | - | 实现Scheduler.check_heartbeat()方法 | src/ginkgo/livecore/scheduler.py | ⚪ 待办 |
| T045 | [P] | 实现ExecutionNode.send_heartbeat()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T046 | - | 实现ExecutionNode.subscribe_schedule_updates()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T047 | [P] | 编写心跳机制集成测试 | tests/integration/live/test_heartbeat.py | ⚪ 待办 |
| T048 | - | 实现ExecutionNode.handle_portfolio_reload()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T049 | - | 实现Portfolio.graceful_reload()方法（状态转换+消息缓存+重放） | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T050 | - | 实现ExecutionNode.migrate_portfolio()方法 | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T051 | [P] | 编写优雅重启集成测试 | tests/integration/live/test_graceful_reload.py | ⚪ 待办 |
| T052 | [P] | 创建引擎API路由 | api/routers/engine.py | ⚪ 待办 |
| T053 | - | 实现API Gateway通过Redis查询LiveEngine状态 | api/routers/engine.py | ⚪ 待办 |
| T054 | [P] | 创建调度API路由 | api/routers/schedule.py | ⚪ 待办 |
| T055 | - | 实现API Gateway通过Redis查询Scheduler状态 | api/routers/schedule.py | ⚪ 待办 |
| T056 | - | 实现API Gateway发布控制命令到Kafka | api/routers/engine.py, api/routers/schedule.py | ⚪ 待办 |

**详细任务**: [tasks_phase5.md](./tasks_phase5.md)

---

### Phase 6: User Story 4 - 实时风控执行 (T057-T060)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T057 | [P] | 扩展Portfolio添加apply_risk_managements()方法 | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T058 | [P] | 扩展Portfolio添加apply_risk_to_order()方法 | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T059 | - | 实现Portfolio.generate_risk_signals()方法 | src/ginkgo/core/portfolios/portfolio.py | ⚪ 待办 |
| T060 | [P] | 编写风控集成单元测试 | tests/unit/live/test_risk_integration.py | ⚪ 待办 |

**详细任务**: [tasks_phase6.md](./tasks_phase6.md)

---

### Phase 7: User Story 5 - 系统监控 (T065-T072)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T065 | [P] | 创建metrics.py（留空） | src/ginkgo/workers/execution_node/metrics.py | ⚪ 待办 |
| T066 | - | 实现ExecutionNode.collect_metrics()方法 | src/ginkgo/workers/execution_node/metrics.py | ⚪ 待办 |
| T067 | - | 实现PortfolioState缓存到Redis | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T068 | - | 实现ExecutionNode状态缓存到Redis | src/ginkgo/workers/execution_node/node.py | ⚪ 待办 |
| T069 | [P] | 编写监控指标单元测试 | tests/unit/live/test_metrics.py | ⚪ 待办 |
| T070 | [P] | 创建监控查询API路由 | api/routers/monitoring.py | ⚪ 待办 |
| T071 | - | 编写Redis故障恢复测试 | tests/integration/live/test_redis_failover.py | ⚪ 待办 |
| T072 | - | 编写Redis容错机制测试 | tests/integration/live/test_redis_tolerance.py | ⚪ 待办 |

**详细任务**: [tasks_phase7.md](./tasks_phase7.md)

---

### Phase 8: Polish & Cross-Cutting Concerns (T075-T080)

| ID | 并行 | 任务描述 | 文件路径 | 状态 |
|----|------|----------|----------|------|
| T075 | [P] | 为所有Kafka Producer/Consumer添加装饰器 | src/ginkgo/data/drivers/ginkgo_kafka.py, src/ginkgo/livecore/*.py | ⚪ 待办 |
| T076 | [P] | 为所有数据库操作添加装饰器 | src/ginkgo/data/crud/*.py, src/ginkgo/data/drivers/*.py | ⚪ 待办 |
| T077 | - | 为所有新增类添加头部注释 | 所有新增文件 | ⚪ 待办 |
| T078 | - | 运行所有单元测试 | tests/unit/live/ | ⚪ 待办 |
| T079 | - | 运行所有集成测试 | tests/integration/live/ | ⚪ 待办 |
| T080 | - | 编写性能基准测试 | tests/benchmark/test_live_performance.py | ⚪ 待办 |

**详细任务**: [tasks_phase8.md](./tasks_phase8.md)

---

## 🔄 依赖关系

```
Setup (Phase 1)
    ↓
Foundational (Phase 2)
    ↓
┌─────────────────────────────────────────────────────┐
│                                                     │
├────→ US1: 单Portfolio实盘运行 (Phase 3, P1) ◄───────┤ MVP
│                                                     │
├────→ US2: 多Portfolio并行运行 (Phase 4, P2) ◄───────┤
│      (依赖: US1)                                    │
│                                                     │
├────→ US4: 实时风控执行 (Phase 6, P2) ◄──────────────┤
│      (依赖: US1)                                    │
│                                                     │
├────→ US3: Portfolio动态调度 (Phase 5, P3) ◄─────────┤
│      (依赖: US1, US2)                               │
│                                                     │
└────→ US5: 系统监控和告警 (Phase 7, P3) ◄──────────────┘
       (依赖: US1, US2)

    ↓
Polish (Phase 8)
```

---

## 💡 使用说明

### 如何使用本文档

1. **查看总体进度**: 本文档提供所有任务的概览和完成状态
2. **查看详细任务**: 点击每个阶段的"详细文档"链接查看具体任务详情
3. **执行任务**: 按照阶段顺序执行，每阶段最多同时进行5个任务（符合Constitution任务管理原则）

### 任务管理原则

根据Constitution"任务管理原则"：
- ✅ 从当前阶段的任务池中**选择5个任务**开始开发
- ✅ 完成后标记为完成，再从任务池选择新的5个
- ✅ 始终保持"正在进行"的任务≤5个

### 状态标记

- ⚪ 待办 (Todo): 未开始的任务
- 🟡 进行中 (In Progress): 正在开发的任务（最多5个）
- 🔴 阻塞 (Blocked): 被依赖阻塞的任务
- ✅ 完成 (Done): 已完成的任务

---

## 📈 MVP范围

**MVP = Phase 1 + Phase 2 + Phase 3** (共30个任务)

- Phase 1: Setup (8任务)
- Phase 2: Foundational (8任务)
- Phase 3: User Story 1 - 单Portfolio实盘运行 (14任务)

**MVP目标**: Portfolio能够接收实时行情、生成信号、提交订单、更新持仓

---

**文档版本**: 2.1.0 (简化APIGateway、移除risk_logger和alerts)
**最后更新**: 2026-01-04
**总任务数**: 74
**预计工期**: 6-8周 (MVP 2-3周)
