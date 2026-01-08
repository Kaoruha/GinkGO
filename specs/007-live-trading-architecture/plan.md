# Implementation Plan: 实盘多Portfolio架构支持

**Branch**: `007-live-trading-architecture` | **Date**: 2026-01-04 | **Spec**: [spec.md](/home/kaoru/Ginkgo/specs/007-live-trading-architecture/spec.md)
**Input**: Feature specification from `/specs/007-live-trading-architecture/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

**架构澄清（2026-01-04更新）**:
1. **双队列模式已实现** ✅ - PortfolioProcessor已完成从callback模式到双队列模式的切换：
   - Portfolio使用put()发布事件 → PortfolioProcessor._handle_portfolio_event() → output_queue
   - ExecutionNode监听output_queue，序列化事件并发送到Kafka
   - 完全符合六边形架构约束（Domain Kernel不依赖Adapter）
   - Portfolio不再持有ExecutionNode引用，submit_order()方法已移除

2. **架构违反的暂时接受** ⚠️ - 增量交付原则：
   - Portfolio内部的Selector/Sizer/Strategy可能查询数据库（获取历史数据）
   - 这是技术债务，在Feature完成后进行独立重构任务（非Phase 8）
   - 重构将分析ExecutionNode如何预加载数据并组装完整上下文DTO

3. **其他组件严格约束** ✅ - ExecutionNode、API Gateway、DataManager、TradeGatewayAdapter、Scheduler、Redis、Kafka都严格按照六边形架构边界执行

## Summary

本特性旨在为 Ginkgo 量化交易库实现完整的实盘交易架构支持，支持多Portfolio并行运行、动态调度和实时风控。

**核心目标**:
1. **三大容器架构**: API Gateway（控制层） + LiveCore（业务逻辑层） + ExecutionNode（执行层）
2. **Kafka消息总线**: 7个Topic实现组件解耦和异步通信
3. **无状态设计**: 所有状态持久化到数据库（MySQL/ClickHouse/Redis）
4. **水平扩展**: ExecutionNode可扩展至10+实例，支持Portfolio动态调度
5. **实时风控**: 支持止损、止盈、仓位控制等风控模块实时执行

**技术方案**:
- **事件驱动架构**: PriceUpdate → Strategy → Signal → Portfolio → Order → Fill
- **Kafka通信**: 市场数据、订单、控制命令、调度更新、系统事件、异常告警
- **InterestMap路由**: ExecutionNode内部使用interest_map高效路由市场数据到Portfolio
- **Backpressure机制**: 两级警告（70%/95%）防止消息溢出
- **优雅重启**: Portfolio配置更新时无感知重启（< 30秒）
- **控制入口扩展性**: 支持HTTP API、CLI、Data模块等多种控制入口，通过Kafka统一发布命令，零改造成本接入

**阶段组织策略**:
- 本特性共 5 个User Story，按优先级分为 P1-P3
- US1 (P1): 单Portfolio实盘运行 - MVP验证
- US2 (P2): 多Portfolio并行运行 - 资源利用率
- US3 (P3): Portfolio动态调度 - 高可用和扩展
- US4 (P2): 实时风控执行 - 风险管理
- US5 (P3): 系统监控和告警 - 运维保障

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse, MySQL, Redis, Kafka, MongoDB, Typer, Rich, Pydantic
**Storage**: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存)
**Testing**: pytest with TDD workflow, unit/integration/database/network标记分类
**Target Platform**: Linux server (量化交易后端)
**Project Type**: single (Python量化交易库)
**Performance Goals**:
- PriceUpdate → Signal: < 200ms
- Signal → Order: < 100ms
- Order → Kafka: < 100ms
- 配置变更切换: < 30秒
- 故障恢复: < 60秒
**Constraints**: 必须启用debug模式进行数据库操作, 遵循事件驱动架构, 支持分布式worker
**Scale/Scope**: 支持10+ExecutionNode并行运行, 每Node运行3-5个Portfolio, 处理5000条/秒市场数据

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查（Kafka凭证、券商API密钥存储在 `~/.ginkgo/secure.yml`，已添加到 .gitignore）
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理（Webhook URL、SMTP凭证、券商API密钥存储在 secure.yml）
- [x] 敏感配置文件已添加到.gitignore（`~/.ginkgo/secure.yml`）

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构（实盘交易通过 Kafka 事件驱动，异步处理市场数据、订单、控制命令）
- [x] **服务容器强制规范**：所有Service必须从ServiceContainer获取，通过`service_hub.xxx()`或`services.xxx()`访问，禁止直接实例化（PortfolioService、PositionCRUD等）
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责（数据层：MySQL/ClickHouse模型，服务层：LiveEngine、Scheduler，执行层：ExecutionNode）
- [x] **六边形架构约束**：除PortfolioProcessor暂时放宽外，其他组件严格按六边形架构边界执行（ExecutionNode、API Gateway、DataManager、TradeGatewayAdapter、Scheduler、Redis、Kafka）

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器（Kafka 生产者/消费者、Portfolio处理、数据库操作）
- [x] 提供类型注解，支持静态类型检查（所有 Pydantic 模型、CRUD 类、服务类）
- [x] 禁止使用hasattr等反射机制回避类型错误（使用正确的类型检查和 Optional 类型）
- [x] 遵循既定命名约定（MPportfolio/MPosition MySQL模型，Event* Kafka事件，CRUD操作前缀 add_/get_/update_/delete_）

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能（使用 `@pytest.mark.tdd` 标记，先写失败测试再实现）
- [x] 测试按unit、integration、database、network标记分类（Kafka 测试 @pytest.mark.network，数据库测试 @pytest.mark.database）
- [x] 数据库测试使用测试数据库，避免影响生产数据（使用独立的测试数据库 `ginkgo_test`）

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法（ClickHouse 批量插入持仓记录，批量查询Portfolio状态）
- [x] 合理使用多级缓存（Redis 缓存Portfolio状态、ExecutionNode信息，方法级缓存 @cache_with_expiration）
- [x] 使用懒加载机制优化启动时间（Kafka 消费者懒加载，Portfolio 按需加载）

### 任务管理原则 (Task Management Excellence)
- [x] 采用分阶段管理策略，每个阶段最多5个活跃任务（5个User Story分为多个阶段）
- [x] 已完成任务立即从活跃列表移除（完成一个任务后立即标记完成并移除）
- [x] 任务优先级明确，高优先级任务优先显示（P1 单Portfolio实盘运行、P2 多Portfolio并行、P3 动态调度）
- [x] 任务状态实时更新，确保团队协作效率（使用 tasks.md 跟踪任务状态）

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文（spec.md、plan.md、research.md、data-model.md、quickstart.md 全部使用中文）
- [x] 核心API提供详细使用示例和参数说明（quickstart.md 包含完整的 CLI 和 Python API 示例）
- [x] 重要组件有清晰的架构说明和设计理念文档（research.md 包含 Kafka 集成、InterestMap路由、Backpressure机制等技术决策）

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述（MPportfolio/MPosition/ExecutionNode/PortfolioProcessor 等模型）
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述（LiveEngine、Scheduler、API Gateway）
- [x] 代码审查过程中检查头部信息的准确性（CI/CD 流程包含头部检查）
- [x] 定期运行`scripts/verify_headers.py`检查头部一致性（每次提交前运行）
- [x] CI/CD流程包含头部准确性检查（GitHub Actions 集成）
- [x] 使用`scripts/generate_headers.py --force`批量更新头部（重构代码后运行）

## Project Structure

### Documentation (this feature)

```text
specs/007-live-trading-architecture/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api-gateway.md   # API Gateway API contracts
│   └── kafka-events.md  # Kafka events contracts
├── information-flow.md  # 信息流转视图
├── scenarios.md         # 所有场景列表
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Ginkgo 量化交易库结构
src/
├── ginkgo/                          # 主要库代码
│   ├── core/                        # 核心组件（复用）
│   │   └── events/                  # 事件系统（复用）
│   │       ├── price_update.py      # EventPriceUpdate ✅ 复用
│   │       └── order_lifecycle_events.py  # EventOrderPartiallyFilled ✅ 复用
│   ├── trading/                     # 交易执行层（复用和扩展）
│   │   ├── bases/                   # 基础类
│   │   │   └── portfolio_base.py    # PortfolioBase抽象基类 ✅ 复用
│   │   └── portfolios/              # 投资组合实现
│   │       └── portfolio_live.py    # PortfolioLive实盘投资组合 ✅ 扩展（移除回测逻辑）
│   ├── messages/                    # 🆕 Kafka消息传输（DTO，非Event）
│   │   ├── __init__.py
│   │   └── control_command.py      # ControlCommand消息（用于ginkgo.live.control.commands）
│   ├── data/                        # 数据层（复用）
│   │   ├── models/                  # 数据模型
│   │   │   ├── model_portfolio.py   # MPortfolio ✅ 复用
│   │   │   └── model_position.py    # MPosition ✅ 复用
│   │   ├── crud/                    # CRUD操作
│   │   │   └── portfolio_crud.py    # PortfolioCRUD ✅ 复用
│   │   └── drivers/                 # 数据驱动
│   │       └── ginkgo_kafka.py      # GinkgoProducer/Consumer ✅ 复用（改造acks）
│   ├── trading/                     # 交易执行层（复用）
│   │   ├── engines/                 # 引擎
│   │   │   └── engine_live.py       # 实盘引擎基类 ✅ 复用
│   │   └── gateway/                 # 交易网关
│   │       └── trade_gateway.py     # TradeGateway ✅ 复用
│   ├── workers/                     # 🆕 Worker类型（独立进程）
│   │   └── execution_node/          # ExecutionNode Worker
│   │       ├── node.py              # ExecutionNode主类
│   │       ├── portfolio_processor.py # Portfolio处理线程
│   │       ├── interest_map.py      # 兴趣集路由
│   │       ├── backpressure.py      # 反压机制
│   │       └── metrics.py           # 监控指标（留空，未来Prometheus）
│   └── livecore/                    # 🆕 LiveCore容器（多线程）
│       ├── main.py                  # LiveCore主入口（启动所有组件线程）
│       ├── data_manager.py          # 数据源管理器（发布市场数据到Kafka）
│       ├── trade_gateway_adapter.py # 交易网关适配器（订阅Kafka订单，封装TradeGateway执行）
│       └── scheduler.py             # 调度器（无状态，调度数据存储在Redis）

api/                                # 🆕 API Gateway（复用现有api/目录）
└── routers/                         # API路由
    ├── engine.py                    # 引擎控制API 🆕 新建
    ├── schedule.py                  # 调度管理API 🆕 新建
    └── monitoring.py                # 监控查询API 🆕 新建

tests/                               # 测试目录
├── unit/                            # 单元测试
│   └── live/                        # 实盘模块测试 🆕
├── integration/                     # 集成测试
│   └── live/                        # 实盘集成测试 🆕
└── network/                         # 网络测试
    └── live/                        # Kafka网络测试 🆕
```

**Structure Decision**: 采用集成式目录结构，最大化复用现有trading/data/events组件。新增workers/和livecore/目录实现实盘交易功能，避免创建新的根目录。Scheduler采用无状态设计，调度数据存储在Redis，支持LiveCore重启后从Redis恢复状态。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Kafka消息总线 | 需要解耦三大容器（API Gateway、LiveCore、ExecutionNode），支持水平扩展和故障恢复 | 直接HTTP调用会导致紧耦合，无法支持水平扩展和异步处理 |
| InterestMap路由 | ExecutionNode需要高效路由市场数据到对应的Portfolio（~5000条/秒） | 简单的轮询或广播方式性能不足，无法满足实时性要求 |
| Backpressure机制 | 防止Portfolio处理慢导致内存溢出，保护系统稳定性 | 无界Queue会导致内存溢出，阻塞方式会影响其他Portfolio |
| 无状态设计 | ExecutionNode可以水平扩展，故障时Portfolio可以快速迁移 | 有状态设计会导致单点故障，无法支持弹性伸缩 |
| 优雅重启 | Portfolio配置更新时不丢失消息，保证交易连续性 | 直接重启会导致Queue中消息丢失，可能错过交易机会 |

---

## Implementation Strategy

### MVP范围（最小可用产品）

**Phase 1: 基础设施（US1 - 单Portfolio实盘运行）**

目标：验证实盘交易架构的基础功能

**核心组件**:
1. ExecutionNode（运行单个Portfolio）
2. PortfolioProcessor（单线程处理）
3. LiveCore.Data（发布市场数据）
4. LiveCore.LiveEngine（处理订单）
5. LiveCore.TradeGateway（模拟券商）

**Kafka Topics**:
- `ginkgo.live.market.data` - 市场数据
- `ginkgo.live.orders.submission` - 订单提交
- `ginkgo.live.orders.feedback` - 订单回报

**数据库**:
- MySQL: Portfolio配置
- ClickHouse: 持仓历史
- Redis: 状态缓存

**成功标准**:
- Portfolio能够接收实时行情
- 策略生成信号并提交订单
- 订单成交后更新持仓和资金
- 端到端延迟 < 200ms

---

### 增量交付计划

**Phase 2: 多Portfolio并行（US2）**

目标：在单个ExecutionNode内运行多个Portfolio

**新增功能**:
1. PortfolioProcessor线程池（每个Portfolio独立线程）
2. InterestMap路由机制
3. Backpressure反压机制（两级警告）

**成功标准**:
- 单Node运行3-5个Portfolio
- 消息路由正确（interest_map）
- 队列满时触发告警

---

**Phase 3: Portfolio动态调度（US3）**

目标：支持Portfolio在Node间迁移和故障恢复

**新增组件**:
1. Scheduler（调度器，无状态设计）
   - 调度数据存储在Redis（execution_nodes, portfolio_assignments）
   - LiveCore重启后从Redis恢复状态
2. API Gateway（控制层）
3. 心跳检测机制

**Kafka Topics**:
- `ginkgo.live.control.commands` - 控制命令
- `ginkgo.live.schedule.updates` - 调度更新
- `ginkgo.live.system.events` - 系统事件

**成功标准**:
- Portfolio配置更新时优雅重启（< 30秒）
- Node故障时Portfolio自动迁移（< 60秒）
- 手动迁移Portfolio
- LiveCore重启后Scheduler从Redis恢复状态（< 5秒）

---

**Phase 4: 实时风控执行（US4）**

目标：集成风控模块到实盘交易

**风控模块**:
1. PositionRatioRisk（仓位控制）
2. LossLimitRisk（止损）
3. ProfitLimitRisk（止盈）

**成功标准**:
- 风控实时拦截订单
- 风控生成平仓信号
- 风控日志记录

---

**Phase 5: 系统监控和告警（US5）**

目标：提供完整的监控和告警能力

**新增功能**:
1. 监控指标收集（Prometheus集成）
2. 告警发布到Kafka（`ginkgo.alerts`）
3. API Gateway监控查询API

**成功标准**:
- ExecutionNode心跳正常
- Queue满时触发告警
- 查询历史告警

---

## Dependencies

### 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **kafka-python** | 2.0.2+ | Kafka客户端 |
| **redis-py** | 5.0.0+ | Redis客户端 |
| **pymongo** | 4.6.0+ | MongoDB客户端 |
| **clickhouse-driver** | 0.2.6+ | ClickHouse客户端 |
| **fastapi** | 0.109.0+ | API Gateway框架 |
| **uvicorn** | 0.27.0+ | ASGI服务器 |

### 内部依赖

| 依赖模块 | 版本 | 用途 |
|---------|------|------|
| **ginkgo.core** | 当前版本 | 事件系统、Portfolio基类 |
| **ginkgo.data** | 当前版本 | 数据模型、CRUD |
| **ginkgo.trading** | 当前版本 | 券商接口、订单管理 |
| **ginkgo.libs** | 当前版本 | 装饰器、工具函数 |

---

## Risk Assessment

### 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Kafka消息丢失 | 订单丢失、数据不一致 | 使用acks=all + 幂等性 + 手动提交offset |
| ExecutionNode崩溃 | Portfolio停止运行 | 心跳检测 + 自动迁移 + 状态持久化 |
| 市场数据延迟 | 错过交易机会 | 优化InterestMap路由 + 增加Kafka分区 |
| Redis故障 | 状态丢失 | Redis持久化 + 数据库兜底 |
| 数据库连接池耗尽 | 无法写入订单回报 | 连接池监控 + 自动重试 |

### 业务风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 策略Bug导致亏损 | 资金损失 | 风控模块 + 模拟盘测试 + 限仓 |
| 券商API故障 | 无法下单 | 券商API监控 + 自动重试 + 告警 |
| 网络分区 | 消息积压 | Kafka副本机制 + 消息压缩 |
| 恶意攻击 | 系统被控制 | API认证 + Rate Limiting + 日志审计 |

---

## Testing Strategy

### 单元测试（@pytest.mark.unit）

- ExecutionNode: InterestMap路由、Backpressure机制
- PortfolioProcessor: 消息处理、状态管理
- LiveEngine: 订单处理、风控集成
- Scheduler: 调度算法、心跳检测

### 集成测试（@pytest.mark.integration）

- 市场数据流: Data → Kafka → ExecutionNode → Portfolio
- 订单流: Portfolio → ExecutionNode → Kafka → LiveEngine → TradeGateway
- 回报流: TradeGateway → LiveEngine → Kafka → ExecutionNode → Portfolio
- 控制流: API Gateway → Kafka → ExecutionNode

### 数据库测试（@pytest.mark.database）

- Portfolio CRUD: MySQL操作
- Position CRUD: ClickHouse操作
- Redis缓存: 状态读写

### 网络测试（@pytest.mark.network）

- Kafka Producer/Consumer: 消息发送和接收
- Redis连接: 心跳上报
- API调用: RESTful API请求

---

## Rollout Plan

### 阶段1: 开发环境（1-2周）

- 部署开发环境（单机）
- 实现US1核心功能
- 单元测试 + 集成测试

### 阶段2: 测试环境（2-3周）

- 部署测试环境（Docker Compose）
- 实现US2-US5全部功能
- 端到端测试 + 性能测试

### 阶段3: 预生产环境（1-2周）

- 部署预生产环境（Kubernetes）
- 压力测试 + 故障演练
- 监控告警验证

### 阶段4: 生产环境（逐步上线）

- 部署生产环境（Kubernetes）
- 灰度发布（10% → 50% → 100%）
- 7x24监控 + 运维值守

---

## Success Metrics

### 功能指标

- [ ] US1: 单Portfolio能够接收实时行情、生成信号、提交订单、更新持仓
- [ ] US2: 单Node运行3-5个Portfolio，消息路由正确
- [ ] US3: Portfolio配置更新时优雅重启（< 30秒），故障迁移（< 60秒）
- [ ] US4: 风控实时拦截订单、生成平仓信号
- [ ] US5: 心跳正常、告警触发、监控查询

### 性能指标

- [ ] PriceUpdate → Signal: < 200ms (p95)
- [ ] Signal → Order: < 100ms (p95)
- [ ] Order → Kafka: < 100ms (p95)
- [ ] 配置变更切换: < 30秒
- [ ] 故障恢复: < 60秒

### 可靠性指标

- [ ] Kafka消息可靠性: 99.9%（acks=all + 幂等性）
- [ ] ExecutionNode可用性: 99%（心跳检测 + 自动迁移）
- [ ] 数据库写入成功率: 99.9%（@retry装饰器）

---

## Progress Tracking

### Phase 1: Setup (项目初始化) - ✅ 完成
- [x] T001-T008: 所有8个任务已完成
- [x] 依赖库安装、目录结构创建、Kafka/数据库配置、连接测试

### Phase 2: Foundational (核心基础设施) - ✅ 完成
- [x] T009-T016: 所有8个任务已完成
- [x] Event复用验证、ControlCommand创建、数据模型验证、Kafka集成测试

### Phase 3: User Story 1 - 单Portfolio实盘运行 - 🔄 进行中 (85%完成)
**已完成 (11/13任务)**:
- [x] T017: 创建ExecutionNode主类
- [x] T018: 创建PortfolioProcessor线程类
- [x] T019: 实现ExecutionNode.load_portfolio()方法
- [x] T020: 实现ExecutionNode.subscribe_market_data()方法
- [x] T021: 实现PortfolioProcessor.run()主循环
- [x] T022: 扩展Portfolio添加on_price_update()方法
- [x] T023: 扩展Portfolio添加on_order_filled()方法
- [x] T024: 实现Portfolio.sync_state_to_db()方法
- [x] T026: 实现双队列模式（移除callback）✅ **架构改进完成**
- [x] T027: 创建LiveCore主入口（多线程容器）✅ **完成**
- [x] T028: 创建TradeGateway适配器
- [x] T029: 改造GinkgoProducer的acks=all

**待办 (2/13任务)**:
- [ ] T025: 编写Portfolio事件处理单元测试

### 关键里程碑
- ✅ **2026-01-04**: 双队列模式架构改进完成，PortfolioProcessor完全符合六边形架构约束
- ✅ **2026-01-04**: ExecutionNode移除callback机制，改用output_queue监听器模式
- ✅ **2026-01-04**: PortfolioLive清理完成，移除回测专用逻辑（reset_positions, cal_signals, cal_suggestions, advance_time, on_price_received）
- ⚠️ **技术债务确认**: Portfolio内部组件数据库访问问题将在Feature完成后重构

---

## Next Steps

### 立即执行 (当前优先级)
1. **T025: 编写Portfolio事件处理单元测试** - 完成测试覆盖率

### 短期计划 (Phase 3剩余)
1. Phase 3基础框架已完成（85%），剩余T025测试任务
2. 运行端到端集成测试验证实盘交易流程
3. 性能测试和优化（目标：端到端延迟 < 200ms）

### 中期计划 (Phase 4-8)
1. Phase 4: 多Portfolio并行运行（InterestMap、Backpressure）
2. Phase 5: Portfolio动态调度（Scheduler、心跳、优雅重启）
3. Phase 6: 实时风控执行
4. Phase 7: 系统监控和告警
5. Phase 8: Polish和跨领域关注点

### 长期计划 (Feature完成后)
1. **独立重构任务**: 分析并设计ExecutionNode如何预加载数据并组装完整上下文DTO
2. **移除数据库访问**: 重构Portfolio内部组件，使其符合Domain Kernel纯内存计算约束
3. **架构优化**: 完全消除PortfolioProcessor的架构违反

---

**文档版本**: 2.0.0
**最后更新**: 2026-01-04 (架构调整和进度更新)
**负责人**: Ginkgo开发团队
