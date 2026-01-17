# Tasks: 实盘数据模块完善

**Input**: Design documents from `/specs/008-live-data-module/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Tests**: TDD测试已要求在spec.md中定义（FR-051: DataManager、TaskTimer、DTO等组件必须包含完整的TDD测试）

**Organization**: 任务按用户故事组织，每个故事可独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行运行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1, US2, US3, US4）
- 描述包含精确文件路径

## Path Conventions

- **源代码**: `src/ginkgo/` (项目根目录)
- **测试**: `tests/unit/`, `tests/integration/`, `tests/database/`, `tests/network/`
- **配置**: `~/.ginkgo/` (用户配置目录)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: 项目初始化和基础结构

- [ ] T001 添加APScheduler依赖到pyproject.toml (apscheduler>=3.10.0)
- [ ] T002 创建LiveCore目录结构 src/ginkgo/livecore/ 及子目录 (data_feeders/, utils/)
- [ ] T003 [P] 创建tests目录结构 tests/unit/livecore/, tests/integration/livecore/
- [ ] T004 [P] 创建默认数据源配置文件模板 ~/.ginkgo/data_sources.yml.example
- [ ] T005 [P] 更新CLAUDE.md添加LiveCore模块文档（新增数据层说明）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事依赖的核心基础设施，必须完成后才能开始任何用户故事实现

**⚠️ CRITICAL**: 此阶段完成前，无法开始任何用户故事工作

### DTO定义（所有用户故事依赖）

- [ ] T006 [P] 创建PriceUpdateDTO in src/ginkgo/interfaces/dtos/price_update_dto.py (完整Tick字段：symbol, price, volume, amount, bid_price, ask_price, bid_volume, ask_volume, open_price, high_price, low_price, timestamp)
- [ ] T007 [P] 创建BarDTO in src/ginkgo/interfaces/dtos/bar_dto.py (K线字段：symbol, period, open, high, low, close, volume, amount, turnover, change, change_pct, timestamp)
- [ ] T008 [P] 创建InterestUpdateDTO in src/ginkgo/interfaces/dtos/interest_update_dto.py (订阅更新：portfolio_id, node_id, symbols, timestamp)
- [ ] T009 [P] 创建ControlCommandDTO in src/ginkgo/interfaces/dtos/control_command_dto.py (控制命令：command, params, timestamp)
- [ ] T010 更新src/ginkgo/interfaces/dtos/__init__.py导出所有DTO类

### DTO单元测试（TDD要求）

- [ ] T011 [P] 编写PriceUpdateDTO单元测试 in tests/unit/interfaces/test_price_update_dto.py (测试字段验证、from_tick方法、JSON序列化)
- [ ] T012 [P] 编写BarDTO单元测试 in tests/unit/interfaces/test_bar_dto.py (测试字段验证、from_bar方法、JSON序列化)
- [ ] T013 [P] 编写InterestUpdateDTO单元测试 in tests/unit/interfaces/test_interest_update_dto.py (测试字段验证、JSON序列化)
- [ ] T014 [P] 编写ControlCommandDTO单元测试 in tests/unit/interfaces/test_control_command_dto.py (测试字段验证、命令类型)

### Kafka Topics定义

- [ ] T015 确保Kafka Topics定义在 src/ginkgo/interfaces/kafka_topics.py (包含MARKET_DATA, INTEREST_UPDATES, CONTROL_COMMANDS)

**Checkpoint**: 基础设施就绪 - 用户故事实现现在可以并行开始

---

## Phase 3: User Story 1 - 实时行情数据订阅与处理 (Priority: P1) 🎯 MVP

**Goal**: 量化交易员能够实时接收市场行情数据（Tick级别），策略基于最新价格做出交易决策

**Independent Test**: 模拟数据源发送实时Tick数据，验证DataManager能够接收、解析并发布EventPriceUpdate到Kafka

### Tests for User Story 1 (TDD - 先写测试，确保失败) ⚠️

- [ ] T016 [P] [US1] 编写DataManager单元测试 in tests/unit/livecore/test_data_manager.py (测试初始化、订阅管理、Kafka消费、线程安全)
- [ ] T017 [P] [US1] 编写LiveDataFeederFactory单元测试 in tests/unit/livecore/test_factory.py (测试工厂创建、装饰器注册、配置文件加载、环境变量替换)
- [ ] T018 [P] [US1] 编写DataManager集成测试 in tests/integration/livecore/test_data_manager_integration.py (测试完整数据流：Kafka订阅→LiveDataFeeder→Queue→Kafka发布)

### Implementation for User Story 1

**工厂模式实现**:
- [ ] T019 [P] [US1] 创建LiveDataFeederFactory in src/ginkgo/livecore/data_feeders/factory.py (类注册表、register_feeder装饰器、create_from_config方法、环境变量替换_substitute_env_vars)
- [ ] T020 [US1] 在factory.py中实现配置文件加载逻辑（读取~/.ginkgo/data_sources.yml，YAML解析，错误处理）
- [ ] T021 [US1] 在factory.py中实现Feeder实例创建逻辑（根据配置动态创建，支持enabled标志）

**LiveDataFeeder基类（使用现有实现）**:
- [ ] T022 [P] [US1] 验证现有ginkgo/trading/feeders/live_feeder.py可用性（确认ILiveDataFeeder接口、WebSocket连接、set_event_publisher、subscribe_symbols方法）
- [ ] T023 [P] [US1] 创建EastMoneyFeeder适配器 in src/ginkgo/livecore/data_feeders/eastmoney_feeder.py (继承现有LiveDataFeeder，实现_connect、_subscribe、_unsubscribe，WebSocket连接wss://push2.eastmoney.com，Tick解析)
- [ ] T024 [US1] 使用@register_feeder装饰器注册EastMoneyFeeder到工厂

**DataManager核心实现**:
- [ ] T025 [US1] 创建DataManager类 in src/ginkgo/livecore/data_manager.py (继承threading.Thread，all_symbols集合，_lock锁，feeders字典，Kafka Consumer，Queue消费者列表)
- [ ] T026 [US1] 在DataManager中实现_initialize_data_sources方法（使用LiveDataFeederFactory.create_from_config创建Feeder实例）
- [ ] T027 [US1] 在DataManager中实现run方法（Kafka消费循环，订阅ginkgo.live.interest.updates，调用_handle_interest_update）
- [ ] T028 [US1] 在DataManager中实现_handle_interest_update方法（线程安全更新all_symbols，按市场分发订阅到Feeder）
- [ ] T029 [US1] 在DataManager中实现start方法（启动所有Feeder、启动Queue消费者、启动主线程）
- [ ] T030 [US1] 在DataManager中实现stop方法（停止Feeder、等待Queue消费完、关闭Kafka）

**Queue消费者实现**:
- [ ] T031 [US1] 创建TickConsumer类 in src/ginkgo/livecore/utils/tick_consumer.py (继承threading.Thread，队列处理，转换为PriceUpdateDTO，发布到Kafka，批量发布优化)
- [ ] T032 [US1] 在TickConsumer中实现非阻塞put逻辑（队列满时丢弃当前数据并记录warn日志）

**市场过滤和订阅管理**:
- [ ] T033 [US1] 在DataManager中实现MARKET_MAPPING常量（cn: [".SH", ".SZ"], hk: [".HK"], us: []）
- [ ] T034 [US1] 在DataManager中实现_filter_by_market方法（根据标的代码后缀过滤市场）

**装饰器和质量保证**:
- [ ] T035 [US1] 为DataManager关键方法添加@time_logger装饰器（start, stop, _handle_interest_update）
- [ ] T036 [US1] 为DataManager关键方法添加@retry装饰器（Kafka发布方法）
- [ ] T037 [US1] 为DataManager添加完整类型注解（all_symbols: Set[str], _lock: threading.Lock, feeders: Dict[str, LiveDataFeeder]）
- [ ] T038 [US1] 为DataManager添加三行头部注释（Upstream: Kafka/Feeder, Downstream: ExecutionNode, Role: 数据管理器）
- [ ] T039 [US1] 使用GLOG添加结构化日志（INFO级别启动停止、DEBUG级别数据流、ERROR级别异常）

**Checkpoint**: 此时User Story 1应完全功能且可独立测试 - 能够接收实时Tick数据并发布到Kafka

---

## Phase 4: User Story 2 - 定时数据快照获取 (Priority: P1)

**Goal**: 量化交易员能够定期获取市场数据快照（K线数据），策略进行技术分析和趋势判断

**Independent Test**: 配置定时任务（如每1分钟），验证DataManager能够按计划从数据源获取快照数据并发布到Kafka

### Tests for User Story 2 (TDD - 先写测试，确保失败) ⚠️

- [ ] T040 [P] [US2] 编写TaskTimer单元测试 in tests/unit/livecore/test_task_timer.py (测试初始化、APScheduler配置、定时任务添加、线程安全）
- [ ] T041 [P] [US2] 编写TaskTimer集成测试 in tests/integration/livecore/test_task_timer_integration.py (测试完整流程：APScheduler触发→BarService查询→BarDTO转换→Kafka发布)

### Implementation for User Story 2

**TaskTimer核心实现**:
- [ ] T042 [US2] 创建TaskTimer类 in src/ginkgo/livecore/task_timer.py (继承threading.Thread，all_symbols集合，_lock锁，Kafka Consumer，APScheduler BackgroundScheduler)
- [ ] T043 [US2] 在TaskTimer中实现run方法（启动APScheduler、添加定时任务、Kafka消费循环）
- [ ] T044 [US2] 在TaskTimer中实现stop方法（shutdown APScheduler、关闭Kafka）
- [ ] T045 [US2] 在TaskTimer中实现_handle_interest_update方法（线程安全更新all_symbols）

**APScheduler任务配置**:
- [ ] T046 [US2] 在TaskTimer中实现_add_jobs方法（添加Selector更新任务：每小时整点，添加数据更新任务：每天19:00，添加K线分析任务：每天21:00）
- [ ] T047 [US2] 使用CronTrigger配置定时任务（timezone='Asia/Shanghai', coalesce=True, max_instances=1, misfire_grace_time=300）

**数据快照任务实现**:
- [ ] T048 [US2] 实现_bar_analysis_job方法 in src/ginkgo/livecore/task_timer.py (21:00触发，使用services.data.cruds.bar()获取当日K线，转换为BarDTO，发布到Kafka ginkgo.live.market.data)
- [ ] T049 [US2] 实现_selector_update_job方法 in src/ginkgo/livecore/task_timer.py (每小时触发，发送控制命令到Kafka ginkgo.live.control.commands)
- [ ] T050 [US2] 实现_data_update_job方法 in src/ginkgo/livecore/task_timer.py (19:00触发，发送数据更新控制命令到Kafka)

**服务集成**:
- [ ] T051 [US2] 集成ServiceHub访问BarService（使用`from ginkgo import services`，services.data.cruds.bar()获取K线数据）

**装饰器和质量保证**:
- [ ] T052 [US2] 为TaskTimer任务方法添加@time_logger装饰器（_bar_analysis_job, _selector_update_job, _data_update_job）
- [ ] T053 [US2] 为TaskTimer任务方法添加@retry装饰器（Kafka发布、BarService查询）
- [ ] T054 [US2] 实现safe_job_wrapper装饰器 in src/ginkgo/livecore/utils/decorators.py（任务崩溃隔离，异常捕获，错误日志，告警通知）
- [ ] T055 [US2] 为TaskTimer添加完整类型注解
- [ ] T056 [US2] 为TaskTimer添加三行头部注释（Upstream: Kafka/BarService, Downstream: ExecutionNode, Role: 定时任务调度器）
- [ ] T057 [US2] 使用GLOG添加结构化日志

**Checkpoint**: 此时User Stories 1和2都应独立工作 - 能够接收实时数据和定时K线数据

---

## Phase 5: User Story 3 - 多数据源统一接入 (Priority: P2)

**Goal**: 量化交易员能够灵活切换或同时使用多个数据源（Tushare、东方财富、同花顺等）

**Independent Test**: 配置多个数据源实例，验证DataManager能够根据配置自动选择数据源或在主数据源故障时切换

### Tests for User Story 3 (TDD - 先写测试，确保失败) ⚠️

- [ ] T058 [P] [US3] 编写多数据源配置测试 in tests/unit/livecore/test_factory.py (测试配置文件解析、多Feeder创建、enabled标志、环境变量替换)
- [ ] T059 [P] [US3] 编写数据源切换测试 in tests/integration/livecore/test_data_source_failover.py (测试主数据源故障切换到备用数据源)

### Implementation for User Story 3

**多市场Feeder实现**:
- [ ] T060 [P] [US3] 创建FuShuFeeder适配器 in src/ginkgo/livecore/data_feeders/fushu_feeder.py (继承现有LiveDataFeeder，HTTP轮询模式，连接https://api.fushu.com/v1/tick，poll_interval=5秒)
- [ ] T061 [P] [US3] 创建AlpacaFeeder适配器 in src/ginkgo/livecore/data_feeders/alpaca_feeder.py (继承现有LiveDataFeeder，WebSocket模式，连接wss://stream.data.alpaca.markets/v2/iex)
- [ ] T062 [P] [US3] 使用@register_feeder装饰器注册FuShuFeeder和AlpacaFeeder到工厂

**配置文件完善**:
- [ ] T063 [US3] 更新~/.ginkgo/data_sources.yml.example添加完整配置示例（cn/hk/us市场配置，enabled标志，api_key环境变量）
- [ ] T064 [US3] 实现配置验证逻辑 in src/ginkgo/livecore/data_feeders/factory.py（使用Pydantic验证配置格式，Feeder类型检查）

**数据源优先级和健康检查**:
- [ ] T065 [US3] 在DataManager中实现数据源优先级配置（主数据源和备用数据源）
- [ ] T066 [US3] 在DataManager中实现数据源健康检查（定期检测数据源可用性，心跳检测）
- [ ] T067 [US3] 在DataManager中实现数据源自动切换逻辑（主数据源故障时切换到备用数据源，<5秒切换时间）

**装饰器和质量保证**:
- [ ] T068 [US3] 为新增Feeder添加@time_logger和@retry装饰器
- [ ] T069 [US3] 为新增Feeder添加完整类型注解和三行头部注释
- [ ] T070 [US3] 使用GLOG添加结构化日志

**Checkpoint**: 所有用户故事（1, 2, 3）现在都应独立功能

---

## Phase 6: User Story 4 - 数据质量监控与告警 (Priority: P3)

**Goal**: 系统运维人员能够实时监控数据质量（延迟、缺失、异常值），及时发现数据问题

**Independent Test**: 模拟各种数据质量问题（延迟、缺失、异常），验证监控模块能够检测并生成告警事件

### Tests for User Story 4 (TDD - 先写测试，确保失败) ⚠️

- [ ] T071 [P] [US4] 编写DataQualityMonitor单元测试 in tests/unit/livecore/test_data_quality_monitor.py (测试延迟检测、缺失检测、异常值过滤、时间戳校验)
- [ ] T072 [P] [US4] 编写监控告警集成测试 in tests/integration/livecore/test_monitoring_alerts.py (测试告警事件发布到Kafka）

### Implementation for User Story 4

**监控模块实现**:
- [ ] T073 [US4] 创建DataQualityMonitor类 in src/ginkgo/livecore/utils/data_quality_monitor.py (延迟监控、缺失检测、异常值过滤、去重、时间戳校验)
- [ ] T074 [US4] 实现check_latency方法（测量数据延迟，超过1秒阈值触发告警）
- [ ] T075 [US4] 实现check_missing方法（检测预期数据未到达）
- [ ] T076 [US4] 实现filter_abnormal方法（过滤价格≤0、成交量<0、涨跌幅>10%的异常数据）
- [ ] T077 [US4] 实现check_duplicates方法（使用(symbol_code, timestamp)作为唯一标识去重）
- [ ] T078 [US4] 实现validate_timestamp方法（检测时间倒流、时区错误）

**告警发布**:
- [ ] T079 [US4] 集成告警发布到Kafka（发布到ginkgo.notifications topic，包含level、message、timestamp）

**装饰器和质量保证**:
- [ ] T080 [US4] 为DataQualityMonitor添加@time_logger装饰器
- [ ] T081 [US4] 为DataQualityMonitor添加完整类型注解和三行头部注释
- [ ] T082 [US4] 使用GLOG添加结构化日志（WARNING级别告警、ERROR级别严重告警）

**Checkpoint**: 所有用户故事（1, 2, 3, 4）现在都应独立功能

---

## Phase 7: ExecutionNode扩展（实盘模式Selector触发机制）

**Purpose**: 扩展ExecutionNode的PortfolioProcessor，实现实盘模式下的Selector触发机制

**Why**: 回测模式通过Portfolio._on_time_advance()触发，实盘模式通过Kafka控制命令解耦触发

### Tests for ExecutionNode扩展 (TDD - 先写测试，确保失败) ⚠️

- [ ] T083 [P] 编写PortfolioProcessor扩展单元测试 in tests/unit/trading/processors/test_portfolio_processor_extension.py (测试_handle_control_command、_update_selectors、selector.pick调用、EventInterestUpdate发布)
- [ ] T084 [P] 编写控制命令集成测试 in tests/integration/trading/test_control_command_flow.py (测试TaskTimer发送命令→Kafka→ExecutionNode接收→selector.pick→EventInterestUpdate发布）

### Implementation for ExecutionNode扩展

**PortfolioProcessor扩展**:
- [ ] T085 在src/ginkgo/trading/processors/portfolio_processor.py中添加_handle_control_command方法（接收Kafka控制命令，解析command类型，路由到对应处理方法）
- [ ] T086 在src/ginkgo/trading/processors/portfolio_processor.py中添加_update_selectors方法（遍历portfolio._selectors，调用selector.pick(time)，创建EventInterestUpdate，发布到Kafka）
- [ ] T087 在src/ginkgo/trading/processors/portfolio_processor.py中添加Kafka Consumer订阅（订阅ginkgo.live.control.commands topic）

**控制命令DTO使用**:
- [ ] T088 在_handle_control_command中使用ControlCommandDTO解析Kafka消息

**装饰器和质量保证**:
- [ ] T089 为新增方法添加@time_logger装饰器
- [ ] T090 为新增方法添加完整类型注解
- [ ] T091 更新portfolio_processor.py的三行头部注释（添加ControlCommand消费说明）
- [ ] T092 使用GLOG添加结构化日志（INFO级别命令接收、DEBUG级别selector执行）

**Checkpoint**: 实盘模式Selector触发机制完整实现 - TaskTimer定时发送命令→ExecutionNode执行→EventInterestUpdate发布

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的改进和优化

### 性能优化任务

- [ ] T093 [P] 实现Kafka批量发布优化（批量大小100，提高吞吐量>10K messages/sec）
- [ ] T094 [P] 优化Queue大小控制（maxsize=10000，满时丢弃策略，保证<100ms延迟）
- [ ] T095 [P] 实现符号集定期清理（避免内存泄漏，清理无效符号）
- [ ] T096 [P] 优化Kafka发布失败重试（指数退避，max_retry=3，保证零丢失）

### 事件驱动集成

- [ ] T097 验证完整事件链路（LiveDataFeeder → DataManager → Kafka(EventPriceUpdate) → ExecutionNode → Portfolio → Strategy.cal → Signal）
- [ ] T098 验证定时事件链路（TaskTimer → Kafka(BarDTO) → ExecutionNode → Portfolio.on_bar_update → Strategy盘后分析）
- [ ] T099 验证控制事件链路（TaskTimer → Kafka(ControlCommandDTO) → ExecutionNode → selector.pick → Kafka(EventInterestUpdate) → DataManager）

### 代码质量检查

- [ ] T100 [P] TDD流程验证（运行pytest --markers=unit，确保所有测试通过）
- [ ] T101 [P] 代码质量检查（类型检查mypy，命名规范，装饰器使用）
- [ ] T102 [P] 安全合规检查（敏感信息检查，配置文件.gitignore，API Key环境变量）
- [ ] T103 [P] 性能基准测试（实时数据延迟<100ms，定时任务精度<1秒，数据源切换<5秒）

### 文档和维护任务

- [ ] T104 [P] 更新quickstart.md（添加LiveCore使用示例，DataManager启动，TaskTimer配置）
- [ ] T105 [P] 更新spec.md的架构设计部分（添加实盘模式Selector触发机制说明）
- [ ] T106 Code cleanup and refactoring（移除未使用代码，统一命名风格）
- [ ] T107 运行quickstart.md验证（启用debug模式，验证完整流程）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖Setup完成 - 阻塞所有用户故事
- **User Stories (Phase 3-7)**: 都依赖Foundational阶段完成
  - US1 (Phase 3) 和 US2 (Phase 4) 可并行实现（都是P1优先级）
  - US3 (Phase 5) 依赖US1完成（多数据源扩展实时数据功能）
  - US4 (Phase 6) 可与US1-US3并行（监控是独立关注点）
  - ExecutionNode扩展 (Phase 7) 依赖US2完成（定时触发机制）
- **Polish (Phase 8)**: 依赖所有期望的用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: Foundational完成后可开始 - 无其他故事依赖
- **User Story 2 (P1)**: Foundational完成后可开始 - 无其他故事依赖
- **User Story 3 (P2)**: 依赖US1完成（扩展实时数据多数据源）
- **User Story 4 (P3)**: Foundational完成后可开始 - 独立监控模块
- **ExecutionNode扩展**: 依赖US2完成（实盘模式定时触发）

### Within Each User Story

- TDD测试必须先写并确认失败
- Tests → Models → Services → Implementation
- 核心实现 → 集成 → 装饰器/质量保证
- 故事完成后独立测试验证

### Parallel Opportunities

- Setup阶段所有[P]任务可并行
- Foundational阶段所有DTO和测试可并行
- Foundational完成后，US1和US2可并行
- US1内所有[P]任务可并行
- US2内所有[P]任务可并行
- US3内所有[P]任务可并行
- US4内所有[P]任务可并行
- Polish阶段所有[P]任务可并行

---

## Parallel Example: User Story 1

```bash
# 启动User Story 1的所有测试（TDD）:
Task: "T016 [P] [US1] 编写DataManager单元测试"
Task: "T017 [P] [US1] 编写LiveDataFeederFactory单元测试"
Task: "T018 [P] [US1] 编写DataManager集成测试"

# 启动User Story 1的所有Feeder实现:
Task: "T023 [P] [US1] 创建EastMoneyFeeder适配器"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only - P1优先级)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (关键 - 阻塞所有故事)
3. 完成 Phase 3: User Story 1 (实时Tick数据)
4. 完成 Phase 4: User Story 2 (定时K线数据)
5. **STOP and VALIDATE**: 独立测试US1和US2
6. 部署/演示 MVP

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. User Story 1 → 独立测试 → 部署/演示 (实时数据MVP!)
3. User Story 2 → 独立测试 → 部署/演示 (定时数据MVP!)
4. User Story 3 → 独立测试 → 部署/演示 (多数据源)
5. User Story 4 → 独立测试 → 部署/演示 (监控告警)
6. ExecutionNode扩展 → 完整实盘架构
7. Polish → 生产就绪

### Parallel Team Strategy

多开发者场景：

1. 团队共同完成 Setup + Foundational
2. Foundational完成后：
   - Developer A: User Story 1 (实时数据)
   - Developer B: User Story 2 (定时数据)
3. US1完成后：
   - Developer A: User Story 3 (多数据源)
4. US2完成后：
   - Developer B: ExecutionNode扩展
5. 独立测试和集成

---

## 任务管理原则遵循

根据章程第6条任务管理原则，请确保：

- **任务数量控制**: 活跃任务列表不得超过5个任务，超出部分应归档或延期
- **定期清理**: 在每个开发阶段完成后，主动清理已完成和过期的任务
- **优先级明确**: 高优先级任务（P1: US1, US2）优先显示和执行
- **状态实时更新**: 任务状态必须及时更新，保持团队协作效率
- **用户体验优化**: 保持任务列表简洁，避免过长影响开发体验

---

## Summary

**Total Task Count**: 107 tasks

**Task Count per User Story**:
- Setup: 5 tasks
- Foundational: 10 tasks (4 DTOs + 4 DTO tests + 1 Kafka Topics + 1 validation)
- User Story 1 (实时数据): 24 tasks (3 tests + 14 implementations + 7 QA)
- User Story 2 (定时数据): 18 tasks (2 tests + 13 implementations + 3 QA)
- User Story 3 (多数据源): 13 tasks (2 tests + 10 implementations + 1 QA)
- User Story 4 (监控): 12 tasks (2 tests + 9 implementations + 1 QA)
- ExecutionNode扩展: 10 tasks (2 tests + 7 implementations + 1 QA)
- Polish: 15 tasks (4 performance + 3 integration + 4 quality + 4 docs)

**Parallel Opportunities Identified**:
- 37个任务标记为[P]可并行执行
- US1和US2可完全并行实现
- 所有DTO和测试可并行创建

**Independent Test Criteria for Each Story**:
- US1: 模拟Tick数据 → DataManager接收 → Kafka发布
- US2: 配置定时任务 → 验证K线数据获取和发布
- US3: 配置多数据源 → 验证自动切换
- US4: 模拟数据问题 → 验证告警生成

**Suggested MVP Scope**:
- Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (User Story 1) + Phase 4 (User Story 2)
- 总计: 57 tasks
- 交付: 实时Tick数据 + 定时K线数据
- 这是完整的最小可行产品，可独立演示和部署
