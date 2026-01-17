# Implementation Plan: 实盘数据模块完善

**Branch**: `008-live-data-module` | **Date**: 2026-01-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-live-data-module/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

完善实盘数据模块，支持两种数据触发模式：
1. **实时触发**: Tick数据通过WebSocket推送触发策略计算（延迟<100ms）
2. **定时触发**: 盘后K线数据通过定时任务触发策略分析（每天19:00数据更新，21:00K线分析）

**技术方案**：
- **DataManager**: 实时数据管理器，维护订阅标的，管理LiveDataFeeder实例，通过Queue消费线程发布数据到Kafka
- **TaskTimer**: 定时任务调度器，使用APScheduler执行硬编码任务（数据更新、K线分析）
- **LiveDataFeeder**: 数据源适配器基类，具体实现包括EastMoneyFeeder(CN)、FuShuFeeder(HK)、AlpacaFeeder(US)
- **DTO系统**: 统一数据传输对象（PriceUpdateDTO、BarDTO、InterestUpdateDTO）
- **Kafka集成**: 通过 `ginkgo.live.interest.updates` 接收订阅更新，通过 `ginkgo.live.market.data` 发布实时行情

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic, APScheduler, websocket-client
**Storage**: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存)
**Testing**: pytest with TDD workflow, unit/integration/database/network标记分类
**Target Platform**: Linux server (量化交易后端)
**Project Type**: single (Python量化交易库)
**Performance Goals**: 高频数据处理 (<100ms延迟), 批量数据操作 (>10K records/sec), 内存优化 (<2GB)
**Constraints**: 必须启用debug模式进行数据库操作, 遵循事件驱动架构, 支持分布式worker
**Scale/Scope**: 支持多策略并行回测, 处理千万级历史数据, 实时风控监控

**Kafka Topics**: 统一使用 `KafkaTopics` 类定义的常量，避免硬编码字符串
**Concurrency**: 多线程容器（LiveCore），DataManager和TaskTimer独立线程，Queue生产者-消费者模式
**Data Flow**: Portfolio → Kafka(interest.updates) → [DataManager, TaskTimer] → LiveDataFeeder/BarService → Kafka(market.data) → ExecutionNode

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理
- [x] 敏感配置文件已添加到.gitignore
- [ ] **Action**: 确保数据源API Key通过环境变量传递（~/.ginkgo/secure.yml）

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import services`访问服务组件
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责
- [ ] **Action**: 确保DataManager作为Driven Adapter不包含业务逻辑，只负责数据转换和分发

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [x] 提供类型注解，支持静态类型检查
- [x] 禁止使用hasattr等反射机制回避类型错误
- [x] 遵循既定命名约定 (CRUD前缀、模型继承等)
- [ ] **Action**: 为DataManager、TaskTimer、LiveDataFeeder添加完整的类型注解

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能
- [x] 测试按unit、integration、database、network标记分类
- [x] 数据库测试使用测试数据库，避免影响生产数据
- [ ] **Action**: LiveDataFeeder不需测试（由实际使用验证），其他组件需完整TDD测试

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法 (如add_bars) 而非单条操作
- [x] 合理使用多级缓存 (Redis + Memory + Method级别)
- [x] 使用懒加载机制优化启动时间
- [ ] **Action**: Queue满时丢弃当前数据（warn日志），确保<100ms延迟

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确，高优先级任务优先显示
- [x] 任务状态实时更新，确保团队协作效率

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [x] 核心API提供详细使用示例和参数说明
- [x] 重要组件有清晰的架构说明和设计理念文档
- [ ] **Action**: 为LiveDataFeeder基类添加接口说明文档

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述
- [x] 代码审查过程中检查头部信息的准确性
- [ ] **Action**: 定期运行`scripts/verify_headers.py`检查头部一致性
- [ ] **Action**: 所有新建文件必须包含三行头部注释（Upstream/Downstream/Role）

### 验证完整性原则 (Verification Integrity)
- [x] 配置类功能验证包含配置文件检查（不仅检查返回值）
- [x] 验证配置文件包含对应配置项（如 grep config.yml notifications.timeout）
- [x] 验证值从配置文件读取，而非代码默认值（打印原始配置内容）
- [x] 验证用户可通过修改配置文件改变行为（修改配置后重新运行）
- [x] 验证缺失配置时降级到默认值（删除配置项后验证）
- [x] 外部依赖验证包含存在性、正确性、版本兼容性检查
- [x] 禁止仅因默认值/Mock使测试通过就认为验证完成
- [ ] **Action**: DataManager配置验证需检查data_sources.yml存在性和正确性

## Project Structure

### Documentation (this feature)

```text
specs/008-live-data-module/
├── spec.md              # Feature specification (已完成)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (待生成)
├── data-model.md        # Phase 1 output (待生成)
├── quickstart.md        # Phase 1 output (待生成)
├── contracts/           # Phase 1 output (待生成)
│   ├── data_manager_interface.md
│   ├── live_data_feeder_interface.md
│   └── dtos.md
└── checklists/          # Quality checklists
    ├── requirements.md  # (已完成)
    └── design.md        # (待生成)
```

### Source Code (repository root)

```text
src/ginkgo/
├── interfaces/                      # 接口定义
│   ├── kafka_topics.py              # (已完成) Kafka Topic常量定义
│   └── dtos.py                      # (待创建) DTO定义（PriceUpdateDTO、BarDTO、InterestUpdateDTO）
│
├── livecore/                        # 实盘交易核心模块
│   ├── main.py                      # (已存在) LiveCore容器主入口
│   ├── data_manager.py              # (待创建) DataManager - 实时数据管理器
│   ├── task_timer.py                # (待创建) TaskTimer - 定时任务调度器
│   ├── data_feeders/                # (待创建) LiveDataFeeder数据源适配器
│   │   ├── __init__.py
│   │   ├── base_feeder.py           # LiveDataFeeder基类
│   │   ├── eastmoney_feeder.py      # EastMoney数据源（A股，WebSocket）
│   │   ├── fushu_feeder.py          # FuShu数据源（港股，HTTP轮询）
│   │   └── alpaca_feeder.py         # Alpaca数据源（美股，WebSocket）
│   └── queue_consumers/             # (待创建) Queue消费者线程
│       ├── __init__.py
│       └── tick_consumer.py         # Tick数据消费者（转换为DTO并发布Kafka）
│
└── data/                            # 数据层
    └── services/                    # (待扩展) 数据服务
        └── bar_service.py           # (待实现) BarService - K线数据服务（供TaskTimer使用）
```

**Structure Decision**: 采用Ginkgo量化交易库的标准单一项目结构，新增livecore模块容纳实盘交易组件，遵循事件驱动架构和六边形架构原则。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| LiveDataFeeder不写测试 | 实际数据源环境复杂，Mock无法覆盖真实场景 | 实际使用验证比Mock测试更可靠 |
| 硬编码配置 | MVP阶段快速实现，避免过度设计 | 配置系统增加复杂度，硬编码满足当前需求 |
| Queue满时丢弃数据 | 保证<100ms延迟，阻塞等待会影响实时性 | 丢弃当前数据比阻塞或丢弃旧数据更符合实时性要求 |

---

## Phase 0: Research & Technology Selection

**Goal**: 解决技术上下文中的未知项，验证技术可行性

### Research Tasks

1. **APScheduler集成研究**
   - [ ] 验证APScheduler在多线程环境中的安全性
   - [ ] 研究Cron表达式配置和时区处理
   - [ ] 确认APScheduler与Kafka Consumer的兼容性

2. **WebSocket客户端选型**
   - [ ] 对比websocket-client、websockets、aiohttp性能
   - [ ] 验证WebSocket断线重连机制实现
   - [ ] 确认线程安全性和心跳检测方案

3. **Kafka Consumer多线程模式**
   - [ ] 研究confluent-kafka在多线程环境中的使用模式
   - [ ] 验证多个Consumer订阅同一Topic的行为
   - [ ] 确认Consumer启动顺序和停止顺序的影响

4. **数据源API调研**
   - [ ] 调研EastMoney WebSocket接口文档
   - [ ] 调研FuShu HTTP API文档
   - [ ] 调研Alpaca WebSocket API文档
   - [ ] 确认数据格式和订阅机制

5. **队列机制验证**
   - [ ] 验证queue.Queue在多线程环境中的性能
   - [ ] 测试maxsize=10000的内存占用
   - [ ] 确认put()非阻塞和get()阻塞的行为

### Research Outputs

- **research.md**: 技术调研报告，包含选型结论和示例代码
- **PoC代码**: 验证关键技术的可行性（WebSocket连接、APScheduler调度、Kafka多Consumer）

---

## Phase 1: Design & Contracts

**Goal**: 完成数据模型设计和API契约定义

### Design Tasks

1. **数据模型设计** (data-model.md)
   - [ ] 定义DataManager核心数据结构
   - [ ] 定义LiveDataFeeder状态机（Disconnected → Connecting → Connected → Reconnecting）
   - [ ] 定义Queue数据流模型（Producer → Queue → Consumer → Kafka）
   - [ ] 定义TaskTimer任务模型（Task类型、Cron配置、失败重试）

2. **API契约定义** (contracts/)
   - [ ] DataManager接口契约
     - `start()` - 启动DataManager
     - `stop()` - 停止DataManager
     - `update_subscriptions()` - 更新订阅标的
   - [ ] LiveDataFeeder接口契约
     - `set_symbols()` - 增量更新订阅
     - `start()` - 启动连接
     - `stop()` - 停止连接
   - [ ] DTO契约（dtos.md）
     - InterestUpdateDTO - 订阅更新消息
     - PriceUpdateDTO - 实时Tick数据
     - BarDTO - K线数据

3. **Quickstart指南** (quickstart.md)
   - [ ] DataManager使用示例
   - [ ] LiveDataFeeder实现示例
   - [ ] TaskTimer配置示例
   - [ ] Kafka消息格式示例

4. **设计质量检查** (checklists/design.md)
   - [ ] 验证设计遵循六边形架构
   - [ ] 验证接口设计符合单一职责原则
   - [ ] 验证数据流符合事件驱动架构
   - [ ] 验证配置管理符合最佳实践

### Design Outputs

- **data-model.md**: 完整的数据模型设计文档
- **contracts/**: API契约定义文件
- **quickstart.md**: 快速入门指南
- **checklists/design.md**: 设计质量检查清单

---

## Phase 2: Implementation Tasks

**Goal**: 按照TDD流程实现所有功能组件

### Core Components (按优先级)

#### P1: DTO和Kafka Topics
1. [ ] 实现 `src/ginkgo/interfaces/dtos.py`
   - [ ] InterestUpdateDTO类（Pydantic模型）
   - [ ] PriceUpdateDTO类（Pydantic模型，完整版11个字段）
   - [ ] BarDTO类（Pydantic模型，完整版11个字段）
   - [ ] DTO工厂方法（从不同数据源格式转换为标准DTO）

2. [ ] 替换硬编码Kafka Topics
   - [ ] 搜索代码库中所有硬编码的Topic字符串
   - [ ] 替换为 `KafkaTopics.XXX` 常量引用
   - [ ] 验证替换后的代码功能正确性

#### P1: LiveDataFeeder基类及实现
3. [ ] 实现 `src/ginkgo/livecore/data_feeders/base_feeder.py`
   - [ ] LiveDataFeeder抽象基类（ABC）
   - [ ] `set_symbols()` - 增量更新订阅逻辑
   - [ ] `start()` - 异步启动连接
   - [ ] `stop()` - 设置停止标志位
   - [ ] `_connect()` - 抽象方法（子类实现）
   - [ ] `_subscribe()` - 抽象方法（子类实现）
   - [ ] `_unsubscribe()` - 抽象方法（子类实现）
   - [ ] 市场过滤逻辑（MARKET_MAPPING）

4. [ ] 实现 `src/ginkgo/livecore/data_feeders/eastmoney_feeder.py`
   - [ ] EastMoneyFeeder类（继承LiveDataFeeder）
   - [ ] WebSocket连接逻辑（websocket-client）
   - [ ] WebSocket消息解析（转换为Tick对象）
   - [ ] 断线重连机制（指数退避）
   - [ ] 心跳检测（ping/pong）

5. [ ] 实现 `src/ginkgo/livecore/data_feeders/fushu_feeder.py`
   - [ ] FuShuFeeder类（继承LiveDataFeeder）
   - [ ] HTTP轮询逻辑（5秒间隔）
   - [ ] HTTP响应解析（转换为Tick对象）
   - [ ] 错误处理和重试

6. [ ] 实现 `src/ginkgo/livecore/data_feeders/alpaca_feeder.py`
   - [ ] AlpacaFeeder类（继承LiveDataFeeder）
   - [ ] WebSocket连接逻辑（Alpaca API）
   - [ ] WebSocket消息解析（转换为Tick对象）
   - [ ] 断线重连和认证

#### P1: Queue消费者
7. [ ] 实现 `src/ginkgo/livecore/queue_consumers/tick_consumer.py`
   - [ ] TickConsumer类（线程）
   - [ ] Queue消费循环（阻塞等待）
   - [ ] Tick转换为PriceUpdateDTO
   - [ ] Kafka发布逻辑（带重试）
   - [ ] 队列满时处理（warn日志）

#### P1: DataManager
8. [ ] 实现 `src/ginkgo/livecore/data_manager.py`
   - [ ] DataManager类（Kafka Consumer线程）
   - [ ] Kafka Consumer订阅 `ginkgo.live.interest.updates`
   - [ ] all_symbols内存维护（Set[str]）
   - [ ] 定时器：每10秒更新Feeder订阅
   - [ ] LiveDataFeeder实例管理（硬编码：cn/hk/us）
   - [ ] Queue消费者线程启动和管理
   - [ ] `start()` - 启动Kafka Consumer、Queue消费者、Feeder
   - [ ] `stop()` - 停止Feeder、等待Queue消费完、停止Consumer

9. [ ] DataManager单元测试（TDD）
   - [ ] 测试Kafka Consumer订阅和消息接收
   - [ ] 测试订阅标的聚合和分发
   - [ ] 测试Feeder订阅更新逻辑
   - [ ] 测试Queue消费者线程启动和停止
   - [ ] 测试start()和stop()顺序

#### P1: TaskTimer
10. [ ] 实现 `src/ginkgo/livecore/task_timer.py`
    - [ ] TaskTimer类（Kafka Consumer线程 + APScheduler）
    - [ ] Kafka Consumer订阅 `ginkgo.live.interest.updates`
    - [ ] all_symbols内存维护（Set[str]）
    - [ ] APScheduler配置（BackgroundScheduler）
    - [ ] 硬编码任务：
      - [ ] 数据更新任务（Cron: "0 19 * * *"）
      - [ ] K线分析任务（Cron: "0 21 * * *"）
    - [ ] `start()` - 启动Kafka Consumer和APScheduler
    - [ ] `stop()` - 停止APScheduler和Kafka Consumer

11. [ ] TaskTimer单元测试（TDD）
    - [ ] 测试Kafka Consumer订阅和消息接收
    - [ ] 测试订阅标的聚合
    - [ ] 测试APScheduler任务调度
    - [ ] 测试硬编码任务触发逻辑
    - [ ] 测试start()和stop()顺序

#### P1: BarService
12. [ ] 实现 `src/ginkgo/data/services/bar_service.py`
    - [ ] BarService类（从ClickHouse查询K线）
    - [ ] `get_daily_bars(symbols, date)` - 批量获取日K线
    - [ ] `publish_to_kafka(bars)` - 发布到Kafka
    - [ ] 数据转换为BarDTO

13. [ ] BarService单元测试（TDD）
    - [ ] 测试ClickHouse K线查询
    - [ ] 测试批量数据获取
    - [ ] 测试BarDTO转换
    - [ ] 测试Kafka发布

#### P2: LiveCore集成
14. [ ] 更新 `src/ginkgo/livecore/main.py`
    - [ ] 替换DataManager占位符为真实DataManager实例
    - [ ] 集成TaskTimer启动和停止
    - [ ] 确保启动顺序：DataManager → TaskTimer → Scheduler
    - [ ] 确保停止顺序：Scheduler → TaskTimer → DataManager

15. [ ] LiveCore集成测试（TDD）
    - [ ] 测试LiveCore启动流程
    - [ ] 测试LiveCore停止流程
    - [ ] 测试DataManager、TaskTimer、Scheduler协同工作
    - [ ] 测试异常处理和优雅关闭

#### P3: 数据质量监控（可选）
16. [ ] 实现 `src/ginkgo/livecore/data_quality_monitor.py`
    - [ ] DataQualityMonitor类
    - [ ] 延迟监控（测量数据产生到接收的时间差）
    - [ ] 缺失检测（检测预期Tick未到达）
    - [ ] 异常值过滤（价格、成交量异常）
    - [ ] 时间戳校验（检测时间倒流）

17. [ ] DataQualityMonitor单元测试（TDD）
    - [ ] 测试延迟监控告警
    - [ ] 测试数据缺失检测
    - [ ] 测试异常值过滤
    - [ ] 测试时间戳校验

### Testing & Validation

- [ ] 单元测试（DataManager、TaskTimer、DTO、BarService）
- [ ] 集成测试（LiveCore组件协同）
- [ ] 网络测试（真实数据源连接，@pytest.mark.network）
- [ ] 性能测试（<100ms延迟验证）
- [ ] 代码覆盖率检查（>85%）

### Documentation

- [ ] 更新CLAUDE.md项目说明
- [ ] 添加LiveDataFeeder实现指南
- [ ] 添加DataManager配置说明
- [ ] 添加TaskTimer任务配置示例

---

## Success Metrics

**Phase 0 完成标志**:
- [ ] research.md包含所有选型结论和示例代码
- [ ] PoC代码验证关键技术可行性
- [ ] 技术风险已识别并有缓解方案

**Phase 1 完成标志**:
- [ ] data-model.md定义所有数据结构
- [ ] contracts/包含所有API契约
- [ ] quickstart.md提供完整使用示例
- [ ] checklists/design.md验证设计质量

**Phase 2 完成标志**:
- [ ] 所有P1组件实现并通过TDD测试
- [ ] LiveDataFeeder实例实现（EastMoney、FuShu、Alpaca）
- [ ] LiveCore集成测试通过
- [ ] 代码覆盖率>85%
- [ ] 性能测试通过（<100ms延迟）

**整体成功标志**:
- [ ] 实时Tick数据从数据源到Kafka端到端延迟<100ms
- [ ] 定时任务触发精度误差<1秒
- [ ] 数据源自动切换时间<5秒
- [ ] 支持至少10个并发数据源订阅
- [ ] Kafka数据发布吞吐量>10,000 messages/sec
- [ ] 数据可用性>99.9%，数据零丢失
