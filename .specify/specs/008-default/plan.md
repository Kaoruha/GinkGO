# Implementation Plan: 实盘数据模块完善

**Branch**: `008-live-data-module` | **Date**: 2026-01-12 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/008-live-data-module/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

完善实盘数据模块，支持实时Tick数据触发和定时控制命令触发。DataManager管理实时数据源（LiveDataFeeder），通过Kafka与ExecutionNode解耦。TaskTimer定时发送控制命令（bar_snapshot）触发DataManager推送当日K线数据，Portfolio复用on_price_update()处理K线并输出信号。使用多态模式创建LiveDataFeeder实例，配置写死+secure.yml读取密钥。

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic, APScheduler, websockets, pyyaml
**Storage**: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存)
**Testing**: pytest with TDD workflow, unit/integration/database/network标记分类
**Target Platform**: Linux server (量化交易后端)
**Project Type**: single (Python量化交易库)
**Performance Goals**: 高频数据处理 (<100ms延迟), 批量数据操作 (>10K records/sec), 内存优化 (<2GB)
**Constraints**: 必须启用debug模式进行数据库操作, 遵循事件驱动架构, 支持分布式worker
**Scale/Scope**: 支持多策略并行回测, 处理千万级历史数据, 实时风控监控

**架构依赖**:
- 基于007-live-trading-architecture实盘架构
- 使用现有LiveDataFeeder实现 (`ginkgo/trading/feeders/live_feeder.py`)
- Kafka作为事件总线解耦LiveCore、TaskTimer和ExecutionNode
- ServiceHub/Service容器模式访问服务（BarService等）

**关键集成点**:
- LiveDataFeeder: 多态模式创建（EastMoneyFeeder/FuShuFeeder/AlpacaFeeder），配置写死+secure.yml读取密钥
- DataManager: 管理LiveDataFeeder，订阅2个Kafka Topic（interest.updates + control.commands），推送当日K线数据
- TaskTimer: 定时发送控制命令到Kafka（bar_snapshot → DataManager）
- DataManager._send_daily_bars: 从BarService获取当日K线，封装为PriceUpdateDTO发布到Kafka
- Portfolio: 复用现有on_price_update()处理K线数据，策略执行分析输出信号

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理（~/.ginkgo/data_sources.yml支持${VAR}格式）
- [x] 敏感配置文件已添加到.gitignore（secure.yml）

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (LiveDataFeeder → DataManager → Kafka → ExecutionNode)
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import services`访问服务组件（BarService等）
- [x] 严格分离数据层（DataManager、TaskTimer）、执行层（ExecutionNode、Portfolio）职责
- [x] 所有Service从ServiceContainer获取，不直接实例化
- [x] DataManager管理LiveDataFeeder（多态），推送当日K线数据到Kafka
- [x] TaskTimer与DataManager解耦，只发送控制命令（bar_snapshot）
- [x] Portfolio复用现有on_price_update()处理K线数据

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器（DataManager、TaskTimer、各Feeder等）
- [x] 提供类型注解，支持静态类型检查（所有新增类）
- [x] 禁止使用hasattr等反射机制回避类型错误
- [x] 遵循既定命名约定（DTO后缀、Feeder后缀等）

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能
- [x] 测试按unit、integration、database、network标记分类
- [x] 数据库测试使用测试数据库，避免影响生产数据
- [x] LiveDataFeeder通过多态创建，测试由实际使用验证
- [x] DataManager、TaskTimer、DTO等组件必须包含完整的TDD测试

### 性能原则 (Performance Excellence)
- [x] 实时数据处理延迟 < 100ms（FR-052）
- [x] 批量数据发布（FR-047）
- [x] 合理使用多级缓存（DTO转换、订阅管理）

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确，高优先级任务优先显示

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [x] 核心API提供详细使用示例和参数说明（quickstart.md）
- [x] 重要组件有清晰的架构说明和设计理念文档

### 代码注释同步原则 (Code Header Synchronization)
- [x] 所有新增代码文件包含三行头部注释（Upstream/Downstream/Role）
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述

### 验证完整性原则 (Verification Integrity)
- [x] 配置类功能验证包含配置文件检查（验证~/.ginkgo/data_sources.yml存在性和内容）
- [x] 验证配置文件包含对应配置项（如grep data_sources.yml cn.type）
- [x] 验证值从配置文件读取，而非代码默认值
- [x] 外部依赖验证包含Kafka连接、数据源API可达性检查

## Project Structure

### Documentation (this feature)

```text
specs/008-live-data-module/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# LiveCore 数据层实现
src/ginkgo/livecore/
├── __init__.py
├── data_manager.py              # DataManager主类（管理LiveDataFeeder，订阅2个Kafka Topic）
├── task_timer.py                # TaskTimer定时任务调度器（发送bar_snapshot命令）
└── utils/                       # 工具模块
    ├── __init__.py
    └── decorators.py            # 装饰器（safe_job_wrapper等）

# LiveDataFeeder实现（多态模式）
src/ginkgo/trading/feeders/
├── live_feeder.py               # 现有LiveDataFeeder基类（重用）
├── eastmoney_feeder.py          # EastMoneyFeeder（A股，WebSocket）
├── fushu_feeder.py              # FuShuFeeder（港股，HTTP轮询）
└── alpaca_feeder.py             # AlpacaFeeder（美股，WebSocket）

# DTO定义
src/ginkgo/interfaces/dtos/
├── __init__.py
├── price_update_dto.py          # PriceUpdateDTO
├── bar_dto.py                   # BarDTO
├── interest_update_dto.py       # InterestUpdateDTO
└── control_command_dto.py       # ControlCommandDTO

# ExecutionNode（无需修改，复用现有方法）
src/ginkgo/trading/
├── processors/
│   └── portfolio_processor.py    # 现有实现（无需修改）
└── portfolios/
    └── portfolio_live.py          # 现有on_price_update()处理K线（复用）

# 测试
tests/unit/livecore/
├── test_data_manager.py          # DataManager单元测试
├── test_task_timer.py            # TaskTimer单元测试
└── test_feeders.py               # LiveDataFeeder单元测试

tests/integration/livecore/
├── test_data_manager_integration.py  # DataManager集成测试
└── test_kafka_flow.py                # Kafka数据流集成测试
```

**Structure Decision**: 采用分层架构，LiveCore（数据层）独立于ExecutionNode（执行层），通过Kafka解耦。使用多态模式创建数据源实例，配置写死+secure.yml读取密钥。Portfolio复用现有on_price_update()处理K线数据。

---

## Phase 0: Research & Discovery

*Objective: Resolve all technical unknowns and validate architectural decisions.*

### 研究结果总结

**APScheduler集成**:
- ✅ BackgroundScheduler在多线程环境中安全
- ✅ 与Kafka Consumer兼容（Consumer在主线程，Scheduler任务在ThreadPoolExecutor）
- ✅ 支持Cron表达式和时区处理
- 添加依赖: `apscheduler>=3.10.0`

**WebSocket客户端选型**:
- ✅ 使用现有`websockets==15.0.1`（异步）
- ✅ 使用`asyncio.run_coroutine_threadsafe`与多线程环境集成
- ✅ 内置心跳机制（ping_interval=30, ping_timeout=60）
- ✅ 实现指数退避重连

**Kafka Consumer多线程模式**:
- ✅ 不同group_id → 广播模式（每个Consumer接收全部消息）
- ✅ 每个组件独立Consumer + 独立线程
- ✅ 保持使用kafka-python-ng（无需切换到confluent-kafka）

**关键决策**:
| 组件 | 选择 | 版本 | 理由 |
|------|------|------|------|
| 定时任务调度 | APScheduler | >=3.10.0 | 线程安全，Cron表达式丰富 |
| WebSocket客户端 | websockets | 15.0.1 | 异步高性能，现有代码已使用 |
| Kafka客户端 | kafka-python-ng | 2.2.3 | 满足多线程需求，稳定可用 |

**详细研究文档**: `specs/008-live-data-module/research.md`

---

## Phase 1: Design & Contracts

*Objective: Define data models, API contracts, and implementation blueprint.*

### 数据模型设计

**DataManager核心数据结构**:
- `all_symbols: Set[str]` - 所有订阅标的（线程安全）
- `feeders: Dict[str, LiveDataFeeder]` - 按市场划分的Feeder实例
- `consumer: GinkgoConsumer` - Kafka消费者（独立group_id）
- `queues: Dict[str, Queue]` - 每个Feeder对应的Queue

**LiveDataFeeder状态机**:
```
DISCONNECTED → CONNECTING → CONNECTED
     ↑              ↓              ↓
     └─────────────┴──────────────┘
           (连接失败/断开)
```

**DTO定义**:
- `InterestUpdateDTO` - 订阅更新消息
- `PriceUpdateDTO` - 实时Tick数据
- `BarDTO` - K线数据
- `ControlCommandDTO` - 控制命令

**Queue数据流模型**:
```
LiveDataFeeder → Queue(maxsize=10000) → TickConsumer → PriceUpdateDTO → Kafka
```

**详细数据模型**: `specs/008-live-data-module/data-model.md`

### API契约

**DataManager接口契约**: `specs/008-live-data-module/contracts/data_manager_interface.md`
**LiveDataFeeder接口契约**: `specs/008-live-data-module/contracts/live_data_feeder_interface.md`
**DTO契约**: `specs/008-live-data-module/contracts/dtos.md`

### 快速入门

**快速开始指南**: `specs/008-live-data-module/quickstart.md`

---

## Phase 1 Constitution Re-check

*Re-evaluating constitutional compliance after design completion.*

### 架构设计再确认
- [x] DataManager使用ServiceHub访问BarService（不直接实例化）
- [x] LiveDataFeeder通过多态创建（直接实例化，配置写死+secure.yml）
- [x] 所有Service从ServiceContainer获取
- [x] Portfolio复用现有on_price_update()处理K线数据

### 代码质量再确认
- [x] 所有新增类使用`@time_logger`、`@retry`装饰器
- [x] 所有类提供完整类型注解
- [x] 遵循命名约定（DTO后缀、Feeder后缀等）

### 验证完整性再确认
- [x] 配置文件验证（~/.ginkgo/task_timer.yml、secure.yml）
- [x] 外部依赖验证（Kafka连接、数据源API）

**结论**: ✅ 所有设计符合章程要求，可以进入实施阶段

---

## Phase 2: Implementation Roadmap

*Objective: Break down the implementation into actionable tasks.*

**Note**: This section will be populated by the `/speckit.tasks` command, not by `/speckit.plan`.

---

## Summary

### 已完成工作

1. **Phase 0: Research & Discovery** ✅
   - 技术选型研究（APScheduler、WebSocket、Kafka）
   - 多线程兼容性验证
   - 风险评估和缓解方案

2. **Phase 1: Design & Contracts** ✅
   - 数据模型设计（DataManager、LiveDataFeeder、DTO）
   - API契约定义
   - 快速入门文档

### 下一步

运行 `/speckit.tasks` 生成详细实施任务清单
