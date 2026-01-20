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

- [X] T001 添加APScheduler依赖到pyproject.toml (apscheduler>=3.10.0)
- [X] T002 创建LiveCore目录结构 src/ginkgo/livecore/ 及子目录 (data_feeders/, utils/)
- [X] T003 [P] 创建tests目录结构 tests/unit/livecore/, tests/integration/livecore/
- [X] T004 [P] 创建默认数据源配置文件模板 ~/.ginkgo/data_sources.yml.example
- [X] T005 [P] 更新CLAUDE.md添加LiveCore模块文档（新增数据层说明）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 所有用户故事依赖的核心基础设施，必须完成后才能开始任何用户故事实现

**⚠️ CRITICAL**: 此阶段完成前，无法开始任何用户故事工作

### DTO定义（所有用户故事依赖）

- [X] T006 [P] 创建PriceUpdateDTO in src/ginkgo/interfaces/dtos/price_update_dto.py (完整Tick字段：symbol, price, volume, amount, bid_price, ask_price, bid_volume, ask_volume, open_price, high_price, low_price, timestamp)
- [X] T007 [P] 创建BarDTO in src/ginkgo/interfaces/dtos/bar_dto.py (K线字段：symbol, period, open, high, low, close, volume, amount, turnover, change, change_pct, timestamp)
- [X] T008 [P] 创建InterestUpdateDTO in src/ginkgo/interfaces/dtos/interest_update_dto.py (订阅更新：portfolio_id, node_id, symbols, timestamp)
- [X] T009 [P] 创建ControlCommandDTO in src/ginkgo/interfaces/dtos/control_command_dto.py (控制命令：command, params, timestamp)
- [X] T010 更新src/ginkgo/interfaces/dtos/__init__.py导出所有DTO类

### DTO单元测试（TDD要求）

- [X] T011 [P] 编写PriceUpdateDTO单元测试 in tests/unit/interfaces/test_price_update_dto.py (测试字段验证、from_tick方法、JSON序列化)
- [X] T012 [P] 编写BarDTO单元测试 in tests/unit/interfaces/test_bar_dto.py (测试字段验证、from_bar方法、JSON序列化)
- [X] T013 [P] 编写InterestUpdateDTO单元测试 in tests/unit/interfaces/test_interest_update_dto.py (测试字段验证、JSON序列化)
- [X] T014 [P] 编写ControlCommandDTO单元测试 in tests/unit/interfaces/test_control_command_dto.py (测试字段验证、命令类型)

### Kafka Topics定义

- [X] T015 确保Kafka Topics定义在 src/ginkgo/interfaces/kafka_topics.py (包含MARKET_DATA, INTEREST_UPDATES, CONTROL_COMMANDS)

**Checkpoint**: 基础设施就绪 - 用户故事实现现在可以并行开始

**验收命令**:
```bash
# 1. 验证DTO文件存在
ls -la src/ginkgo/interfaces/dtos/*.py

# 2. 运行DTO单元测试
pytest tests/unit/interfaces/test_*_dto.py -v

# 3. 验证Kafka Topics定义
grep -E "MARKET_DATA|INTEREST_UPDATES|CONTROL_COMMANDS" src/ginkgo/interfaces/kafka_topics.py
```

---

## Phase 3: User Story 1 - 实时行情数据订阅与处理 (Priority: P1) 🎯 MVP

**Goal**: 量化交易员能够实时接收市场行情数据（Tick级别），策略基于最新价格做出交易决策

**Independent Test**: 模拟数据源发送实时Tick数据，验证DataManager能够接收、解析并发布EventPriceUpdate到Kafka

### Tests for User Story 1 (TDD - 先写测试，确保失败) ⚠️

- [X] T016 [P] [US1] 编写DataManager单元测试 in tests/unit/livecore/test_data_manager.py (测试初始化、订阅管理、Kafka消费、线程安全、K线推送)
- [X] T017 [P] [US1] 编写LiveDataFeeder单元测试 in tests/unit/livecore/test_feeders.py (测试多态挂载、secure.yml配置读取、连接管理)
- [X] T018 [P] [US1] 编写DataManager集成测试 in tests/integration/livecore/test_data_manager_integration.py (测试完整数据流：Kafka订阅→LiveDataFeeder→Kafka发布)

### Implementation for User Story 1

**多态实现（替代工厂模式）**:
- [X] T019 [P] [US1] 验证现有ILiveDataFeeder接口（确认ginkgo/trading/feeders/interfaces.py可用性）
- [X] T020 [US1] 创建EastMoneyFeeder in src/ginkgo/trading/feeders/eastmoney_feeder.py (继承ILiveDataFeeder，写死WebSocket URI，从secure.yml读取API密钥)
- [X] T021 [US1] 创建FuShuFeeder in src/ginkgo/trading/feeders/fushu_feeder.py (继承ILiveDataFeeder，HTTP轮询模式，从secure.yml读取凭证)

**LiveDataFeeder基类（使用现有实现）**:
- [X] T022 [P] [US1] 验证现有ginkgo/trading/feeders/live_feeder.py可用性（确认ILiveDataFeeder接口、WebSocket连接、set_event_publisher、subscribe_symbols方法）
- [X] T023 [P] [US1] 创建AlpacaFeeder in src/ginkgo/trading/feeders/alpaca_feeder.py (继承ILiveDataFeeder，美股WebSocket，从secure.yml读取凭证)
- [X] T024 [US1] 在各Feeder中实现GCONF读取逻辑（使用GCONF.get("data_sources.{feeder_name}.api_key")读取secure.yml配置）

**DataManager核心实现**:
- [X] T025 [US1] 创建DataManager类 in src/ginkgo/livecore/data_manager.py (继承threading.Thread，live_feeder多态实例，all_symbols集合，_lock锁，Kafka Producer/Consumer)
- [X] T026 [US1] 在DataManager中实现_create_feeder方法（多态创建：根据feeder_type参数返回EastMoneyFeeder()或FuShuFeeder()等实例）
- [X] T027 [US1] 在DataManager中实现run方法（双Kafka消费循环：订阅ginkgo.live.interest.updates和ginkgo.live.control.commands）
- [X] T028 [US1] 在DataManager中实现update_subscriptions方法（从InterestUpdateDTO更新all_symbols，线程安全，更新LiveDataFeeder订阅）
- [X] T029 [US1] 在DataManager中实现_handle_control_command方法（从Kafka接收ControlCommandDTO，处理bar_snapshot命令）
- [X] T030 [US1] 在DataManager中实现start方法（启动LiveDataFeeder、启动Kafka订阅、启动主线程）
- [X] T031 [US1] 在DataManager中实现stop方法（停止LiveDataFeeder、关闭Kafka、等待主线程结束）

**实时数据处理**:
- [X] T032 [US1] 在DataManager中实现_on_live_data_received方法（接收LiveDataFeeder的事件回调，转换为PriceUpdateDTO，发布到Kafka）
- [X] T033 [US1] 在DataManager中实现subscribe_live_data方法（设置LiveDataFeeder事件发布器，订阅symbols，启动订阅）

**盘后K线推送（新增）**:
- [X] T034 [US1] 在DataManager中实现_send_daily_bars方法（调用BarService获取当日K线，封装为PriceUpdateDTO，发布到Kafka）
- [X] T035 [US1] 在DataManager中添加from ginkgo import services导入（使用services.data.cruds.bar()获取K线数据）

**装饰器和质量保证**:
- [X] T036 [US1] 为DataManager关键方法添加@time_logger装饰器（start, stop, update_subscriptions, _on_live_data_received, _send_daily_bars）
- [X] T037 [US1] 为DataManager关键方法添加@retry装饰器（Kafka发布方法）
- [X] T038 [US1] 为DataManager添加完整类型注解（all_symbols: Set[str], _lock: threading.Lock, live_feeder: Optional[ILiveDataFeeder]）
- [X] T039 [US1] 为DataManager添加三行头部注释（Upstream: LiveDataFeeder/BarService, Downstream: ExecutionNode, Role: 实时数据管理器）
- [X] T040 [US1] 使用GLOG添加结构化日志（INFO级别启动停止、DEBUG级别数据流、ERROR级别异常）

**Checkpoint**: 此时User Story 1应完全功能且可独立测试 - 能够接收实时Tick数据并发布到Kafka

**验收命令**:
```bash
# 1. 运行DataManager单元测试
pytest tests/unit/livecore/test_data_manager.py -v

# 2. 运行集成测试
pytest tests/integration/livecore/test_data_manager_integration.py -v

# 3. 验证文件存在
ls -la src/ginkgo/livecore/data_manager.py
ls -la src/ginkgo/trading/feeders/eastmoney_feeder.py
```

---

## Phase 4: User Story 2 - 定时控制命令发送 (Priority: P1)

**Goal**: TaskTimer能够定时发送控制命令，触发Portfolio获取市场数据快照并执行策略分析

**Independent Test**: 配置定时任务（如每1分钟），验证TaskTimer能够按计划发送控制命令到Kafka（ginkgo.live.control.commands）

### Tests for User Story 2 (TDD - 先写测试，确保失败) ⚠️

- [X] T041 [P] [US2] 编写TaskTimer单元测试 in tests/unit/livecore/test_task_timer.py (测试初始化、APScheduler配置、多cron规则配置、线程安全)
- [X] T042 [P] [US2] 编写TaskTimer集成测试 in tests/integration/livecore/test_task_timer_integration.py (测试多个cron规则场景：每分钟、每小时、每天；测试控制命令发布到Kafka)

### Implementation for User Story 2

**TaskTimer核心实现**:
- [X] T043 [US2] 创建TaskTimer类 in src/ginkgo/livecore/task_timer.py (APScheduler BackgroundScheduler，Kafka Producer，配置管理)
- [X] T044 [US2] 在TaskTimer中实现start方法（启动APScheduler、添加定时任务）
- [X] T045 [US2] 在TaskTimer中实现stop方法（shutdown APScheduler、关闭Kafka Producer）
- [X] T046 [US2] 在TaskTimer中实现配置验证逻辑（验证task_timer.yml格式、cron表达式合法性、命令类型有效性）

**APScheduler任务配置**:
- [X] T047 [US2] 在TaskTimer中实现配置文件加载逻辑（读取~/.ginkgo/task_timer.yml，解析scheduled_tasks列表，验证cron表达式）
- [X] T048 [US2] 在TaskTimer中实现_add_jobs方法（遍历配置文件中的scheduled_tasks，使用CronTrigger为每个任务添加APScheduler job，支持enabled标志）
- [X] T049 [US2] 使用CronTrigger配置定时任务（timezone='Asia/Shanghai', coalesce=True, max_instances=1, misfire_grace_time=300，支持多个cron表达式）

**控制命令任务实现**:
- [X] T050 [US2] 实现_bar_snapshot_job方法 in src/ginkgo/livecore/task_timer.py (21:00触发，发送"bar_snapshot"控制命令到Kafka ginkgo.live.control.commands)
- [X] T051 [US2] 实现_selector_update_job方法 in src/ginkgo/livecore/task_timer.py (每小时触发，发送"update_selector"控制命令到Kafka ginkgo.live.control.commands)
- [X] T052 [US2] 实现_data_update_job方法 in src/ginkgo/livecore/task_timer.py (19:00触发，发送"update_data"控制命令到Kafka ginkgo.live.control.commands)

**装饰器和质量保证**:
- [X] T053 [US2] 为TaskTimer任务方法添加@time_logger装饰器（_bar_snapshot_job, _selector_update_job, _data_update_job）
- [X] T054 [US2] 为TaskTimer任务方法添加@retry装饰器（Kafka发布方法）
- [X] T055 [US2] 实现safe_job_wrapper装饰器 in src/ginkgo/livecore/utils/decorators.py（任务崩溃隔离，异常捕获，错误日志，告警通知）
- [X] T056 [US2] 为TaskTimer添加完整类型注解
- [X] T057 [US2] 为TaskTimer添加三行头部注释（Upstream: None, Downstream: ExecutionNode, Role: 定时任务调度器）
- [X] T058 [US2] 使用GLOG添加结构化日志

**Checkpoint**: 此时User Stories 1和2都应独立工作 - 能够接收实时数据和发送定时控制命令

**验收命令**:
```bash
# 1. 运行TaskTimer单元测试
pytest tests/unit/livecore/test_task_timer.py -v

# 2. 运行TaskTimer集成测试
pytest tests/integration/livecore/test_task_timer_integration.py -v

# 3. 验证配置文件
cat ~/.ginkgo/task_timer.yml

# 4. 验证文件存在
ls -la src/ginkgo/livecore/task_timer.py
```

---

## Phase 5: User Story 3 - 多数据源扩展 (Priority: P3)

**Goal**: 支持多个数据源（通过多态扩展）

**说明**: 采用多态模式，按需添加新Feeder类，无需工厂模式

### Implementation for User Story 3（按需实施）

**多市场Feeder扩展**:
- [ ] T059 [P] [US3] 创建FuShuFeeder in src/ginkgo/trading/feeders/fushu_feeder.py (继承ILiveDataFeeder，港股HTTP轮询)
- [ ] T060 [P] [US3] 创建AlpacaFeeder in src/ginkgo/trading/feeders/alpaca_feeder.py (继承ILiveDataFeeder，美股WebSocket)
- [ ] T061 [US3] 在DataManager._create_feeder中添加新的Feeder类型支持

**Checkpoint**: 多数据源扩展完成

**验收命令**:
```bash
# 1. 验证多Feeder文件存在
ls -la src/ginkgo/trading/feeders/{eastmoney,fushu,alpaca}_feeder.py

# 2. 验证DataManager._create_feeder支持多类型
grep -A 20 "_create_feeder" src/ginkgo/livecore/data_manager.py
```

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

**验收命令**:
```bash
# 1. 运行数据质量监控单元测试
pytest tests/unit/livecore/test_data_quality_monitor.py -v

# 2. 验证监控模块存在
ls -la src/ginkgo/livecore/data_quality_monitor.py
```

---

## Phase 7: ExecutionNode扩展（实盘模式Selector触发机制）

**Purpose**: 扩展ExecutionNode的PortfolioProcessor，实现实盘模式下的Selector触发机制

**Why**: 回测模式通过Portfolio._on_time_advance()触发，实盘模式通过Kafka控制命令解耦触发

### Tests for ExecutionNode扩展 (TDD - 先写测试，确保失败) ⚠️

- [X] T083 [P] 编写PortfolioProcessor扩展单元测试框架 in tests/unit/trading/processors/test_portfolio_processor_extension.py (测试类初始化、Mock setup)

**_handle_control_command方法测试**:
- [X] T083a [P] 测试_handle_control_command处理有效"update_selector"命令（验证解析成功，调用_update_selectors）
- [X] T083a-1 [P] 测试DataManager的_handle_control_command处理"bar_snapshot"命令（验证调用_send_daily_bars）
- [X] T083b [P] 测试_handle_control_command忽略未知命令类型（验证日志记录，不抛异常）
- [X] T083c [P] 测试_handle_control_command处理无效JSON（验证错误处理，返回错误响应）
- [X] T083d [P] 测试_handle_control_command处理空消息（验证边界条件处理）

**_update_selectors方法测试**:
- [X] T083e [P] 测试_update_selectors调用所有selectors（验证遍历portfolio._selectors，每个selector.pick被调用）
- [X] T083f [P] 测试_update_selectors创建EventInterestUpdate（验证事件包含正确portfolio_id、codes、timestamp）
- [X] T083g [P] 测试_update_selectors发布EventInterestUpdate到Kafka（验证engine_put被调用）
- [X] T083h [P] 测试_update_selectors处理空selector列表（验证不崩溃，返回空codes）
- [X] T083i [P] 测试_update_selectors处理selector.pick抛异常（验证异常捕获，日志记录，继续处理其他selector）

**集成测试**:
- [X] T084 [P] 编写控制命令集成测试 in tests/integration/trading/test_control_command_flow.py (测试TaskTimer发送命令→Kafka→ExecutionNode接收→selector.pick→EventInterestUpdate发布)

### Implementation for ExecutionNode扩展

**PortfolioProcessor扩展**:
- [X] T085 在src/ginkgo/workers/execution_node/portfolio_processor.py中添加_handle_control_command方法（接收Kafka控制命令，解析command类型，路由到对应处理方法）
- [X] T086 在src/ginkgo/workers/execution_node/portfolio_processor.py中添加_update_selectors方法（遍历portfolio._selectors，调用selector.pick(time)，创建EventInterestUpdate，发布到Kafka）
- [X] T087 在src/ginkgo/workers/execution_node/portfolio_processor.py中添加Kafka Consumer订阅（订阅ginkgo.live.control.commands topic）

**注意**: Portfolio无需修改 - 复用现有on_price_update()处理K线数据（DataManager推送当日K线到Kafka）
**注意**: 实际文件路径为 src/ginkgo/workers/execution_node/portfolio_processor.py（非src/ginkgo/trading/processors/）

**控制命令DTO使用**:
- [X] T089 在_handle_control_command中使用ControlCommandDTO解析Kafka消息

**装饰器和质量保证**:
- [X] T090 为新增方法添加@time_logger装饰器（使用GLOG代替print）
- [X] T091 为新增方法添加完整类型注解（Optional, List等）
- [X] T092 更新portfolio_processor.py的三行头部注释（添加ControlCommand消费说明）
- [X] T093 使用GLOG添加结构化日志（INFO级别命令接收、DEBUG级别selector执行）

**Checkpoint**: 实盘模式Selector触发机制完整实现 - TaskTimer定时发送命令→ExecutionNode执行→EventInterestUpdate发布

**验收命令**:
```bash
# 1. 运行ExecutionNode扩展单元测试
pytest tests/unit/trading/processors/test_portfolio_processor_extension.py -v

# 2. 运行控制命令集成测试
pytest tests/integration/trading/test_control_command_flow.py -v

# 3. 验证PortfolioProcessor有_handle_control_command方法
grep -A 10 "_handle_control_command" src/ginkgo/workers/execution_node/portfolio_processor.py

# 4. 验证Kafka控制命令消费
grep "control.commands" src/ginkgo/workers/execution_node/portfolio_processor.py
```

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的改进和优化

### 性能优化任务

- [ ] T094 [P] 实现Kafka批量发布优化（批量大小100，提高吞吐量>10K messages/sec）
- [ ] T095 [P] 优化实时数据处理延迟（保证<100ms延迟，移除不必要的Queue）
- [ ] T096 [P] 实现符号集定期清理（避免内存泄漏，清理无效符号）
- [X] T097 [P] 优化Kafka发布失败重试（指数退避，max_retry=3，保证零丢失）

### 事件驱动集成

- [ ] T098 验证完整事件链路（LiveDataFeeder → DataManager → Kafka(EventPriceUpdate) → ExecutionNode → Portfolio → Strategy.cal → Signal）
- [ ] T099 验证定时事件链路（TaskTimer → Kafka(ControlCommandDTO: bar_snapshot) → DataManager → BarService → Kafka(PriceUpdateDTO: 当日K线) → ExecutionNode → Portfolio.on_price_update → Strategy盘后分析）
- [ ] T100 验证控制事件链路（TaskTimer → Kafka(ControlCommandDTO: update_selector) → ExecutionNode → selector.pick → Kafka(EventInterestUpdate) → DataManager）

### 代码质量检查

- [ ] T101 [P] TDD流程验证（运行pytest --markers=unit，确保所有测试通过）
- [ ] T102 [P] 代码质量检查（类型检查mypy，命名规范，装饰器使用）
- [ ] T103 [P] 安全合规检查（敏感信息检查，配置文件.gitignore，API Key环境变量）
- [ ] T104 [P] 性能基准测试（实时数据延迟<100ms，定时任务精度<1秒，数据源切换<5秒）

### 文档和维护任务

- [X] T105 [P] 更新quickstart.md（添加LiveCore使用示例，DataManager启动，TaskTimer配置）
- [ ] T106 [P] 更新spec.md的架构设计部分（添加实盘模式Selector触发机制说明）
- [X] T107 Code cleanup and refactoring（移除未使用代码，统一命名风格）
- [ ] T108 运行quickstart.md验证（启用debug模式，验证完整流程）

**Checkpoint**: 完整实盘数据模块实现完成 - 所有功能通过测试，文档完整，性能达标

**验收命令**:
```bash
# 1. 运行所有单元测试
pytest tests/unit/livecore/ -v

# 2. 运行所有集成测试
pytest tests/integration/livecore/ tests/integration/trading/ -v

# 3. 验证完整事件链路
pytest -k "event_chain" -v

# 4. 性能基准测试
pytest tests/performance/ -v

# 5. 代码质量检查
mypy src/ginkgo/livecore/
flake8 src/ginkgo/livecore/

# 6. 文档验证
cat specs/008-live-data-module/quickstart.md
```

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
Task: "T017 [P] [US1] 编写LiveDataFeeder单元测试"
Task: "T018 [P] [US1] 编写DataManager集成测试"

# 启动User Story 1的所有Feeder实现:
Task: "T020 [P] [US1] 创建EastMoneyFeeder适配器"
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

**Total Task Count**: 108 tasks

**Task Count per User Story**:
- Setup: 5 tasks
- Foundational: 10 tasks (4 DTOs + 4 DTO tests + 1 Kafka Topics + 1 validation)
- User Story 1 (实时数据): 24 tasks (3 tests + 14 implementations + 7 QA)
- User Story 2 (定时数据): 19 tasks (2 tests + 14 implementations + 3 QA)
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
