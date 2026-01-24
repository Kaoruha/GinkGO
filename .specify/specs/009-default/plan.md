# Implementation Plan: Data Worker容器化部署

**Branch**: `009-data-worker` | **Date**: 2025-01-23 | **Spec**: [spec.md](/home/kaoru/Ginkgo/specs/009-data-worker/spec.md)
**Input**: Feature specification from `/specs/009-data-worker/spec.md`

## Summary

构建容器化数据采集Worker，替代现有GTM多进程模式。Data Worker作为Kafka消费者订阅控制命令，从外部数据源获取市场数据并写入ClickHouse。采用"容器即进程"模式，默认4个容器实例通过Kafka consumer group实现负载均衡。

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: ClickHouse, MySQL, MongoDB, Redis, Kafka, Typer, Rich, Pydantic, APScheduler
**Storage**: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存/心跳)
**Testing**: pytest with TDD workflow, unit/integration/database/network标记分类
**Target Platform**: Linux server (量化交易后端), Docker容器部署
**Project Type**: single (Python量化交易库)
**Performance Goals**: 批量数据操作 >10K records/sec, 单次采集 <60秒, 容器启动 <30秒
**Constraints**: 必须启用debug模式进行数据库操作, 遵循事件驱动架构, Kafka消息驱动
**Scale/Scope**: 默认4个容器实例, 支持处理千万级历史数据

**Key Integration Points**:
- **Kafka Topic**: `ginkgo.live.control.commands` (接收控制命令)
- **Kafka Consumer Group**: `data_worker_group` (多实例负载均衡)
- **Redis Key**: `heartbeat:data_worker:{instance_id}` (TTL=30s)
- **Data Sources**: 已集成在BarCRUD.get_bars()内，通过GCONF配置
- **Target Database**: ClickHouse (K线数据写入)

**Migration Context**:
- **Current**: GTM多进程模式 (`GinkgoThreadManager.start_multi_worker()`)
- **Target**: 容器化微服务模式 (Docker Compose, Kafka事件驱动)
- **Compatibility**: 保持与现有TaskTimer、NotificationWorker模式一致

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [ ] 所有代码提交前已进行敏感文件检查
- [ ] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理
- [ ] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (Kafka消息驱动，无需本地调度)
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import services`访问服务组件
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [x] 提供类型注解，支持静态类型检查
- [ ] 禁止使用hasattr等反射机制回避类型错误
- [ ] 遵循既定命名约定 (CRUD前缀、模型继承等)

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能
- [ ] 测试按unit、integration、database、network标记分类
- [ ] 数据库测试使用测试数据库，避免影响生产数据

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法 (如add_bars) 而非单条操作
- [ ] 合理使用多级缓存 (Redis + Memory + Method级别)
- [x] 使用懒加载机制优化启动时间

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确，高优先级任务优先显示
- [x] 任务状态实时更新，确保团队协作效率

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [ ] 核心API提供详细使用示例和参数说明
- [ ] 重要组件有清晰的架构说明和设计理念文档

### 代码注释同步原则 (Code Header Synchronization)
- [ ] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [ ] 修改模块依赖关系时，更新Upstream/Downstream描述
- [ ] 代码审查过程中检查头部信息的准确性
- [ ] 定期运行`scripts/verify_headers.py`检查头部一致性
- [ ] CI/CD流程包含头部准确性检查
- [ ] 使用`scripts/generate_headers.py --force`批量更新头部

### 验证完整性原则 (Verification Integrity)
- [ ] 配置类功能验证包含配置文件检查（不仅检查返回值）
- [ ] 验证配置文件包含对应配置项（如 grep config.yml notifications.timeout）
- [ ] 验证值从配置文件读取，而非代码默认值（打印原始配置内容）
- [ ] 验证用户可通过修改配置文件改变行为（修改配置后重新运行）
- [ ] 验证缺失配置时降级到默认值（删除配置项后验证）
- [ ] 外部依赖验证包含存在性、正确性、版本兼容性检查
- [ ] 禁止仅因默认值/Mock使测试通过就认为验证完成

## Project Structure

### Documentation (this feature)

```text
specs/009-data-worker/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (TO BE CREATED)
├── data-model.md        # Phase 1 output (TO BE CREATED)
├── quickstart.md        # Phase 1 output (TO BE CREATED)
├── contracts/           # Phase 1 output (TO BE CREATED)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/ginkgo/
├── workers/
│   └── data_worker/                    # NEW: Data Worker模块
│       ├── __init__.py
│       ├── worker.py                   # DataWorker主类 (Kafka consumer)
│       ├── config.py                   # 数据源配置加载
│       ├── collector.py                # 数据采集器
│       ├── validator.py                # 数据验证器
│       └── quality.py                  # 数据质量报告
│
├── interfaces/
│   └── dtos/
│       └── data_command_dto.py         # NEW: Kafka控制命令DTO
│
├── client/
│   └── data_worker_cli.py              # NEW: CLI命令 (ginkgo data-worker ...)
│
└── livecore/
    └── data_worker.py                  # NEW: 容器入口点

.conf/
├── Dockerfile.dataworker               # NEW: Data Worker容器镜像
├── data_worker.yml                     # NEW: Data Worker配置文件
└── docker-compose.yml                  # UPDATE: 添加data-worker服务

tests/
├── unit/workers/data_worker/           # NEW: 单元测试
├── integration/workers/data_worker/    # NEW: 集成测试
└── network/workers/data_worker/        # NEW: 网络测试 (真实数据源)
```

**Structure Decision**: 复用现有TaskTimer/NotificationWorker容器化模式，在`src/ginkgo/workers/`下新建`data_worker/`模块，保持与现有Worker一致的结构。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

---

## Phase 0: Research & Architecture Decisions

**Status**: ✅ COMPLETED

### Research Tasks

1. ✅ **现有Worker模式研究** - 分析TaskTimer和NotificationWorker的实现模式
2. ✅ **Kafka Consumer Group最佳实践** - 研究多实例负载均衡配置
3. ✅ **数据源集成模式** - 研究Tushare/EastMoney API集成方式
4. ✅ **ClickHouse批量写入优化** - 研究高性能数据写入模式
5. ✅ **容器健康检查策略** - 研究Kafka消费者健康检查实现

### Artifacts Created

- ✅ `research.md` - 所有技术决策的依据和选择理由

---

## Phase 1: Design & Contracts

**Status**: ✅ COMPLETED

### Design Tasks

1. ✅ **数据模型设计** - 定义DataQualityReport, WorkerStatus (DataSourceConfig已移除，数据源集成在CRUD方法内)
2. ✅ **Kafka消息契约** - 定义控制命令的DTO格式
3. ✅ **容器配置设计** - Dockerfile和docker-compose.yml配置
4. ✅ **CLI接口设计** - ginkgo data-worker命令结构

### Artifacts Created

- ✅ `data-model.md` - 实体关系图和字段定义
- ✅ `contracts/kafka-messages.md` - Kafka消息格式契约
- ✅ `quickstart.md` - 快速开始指南

---

## Phase 2: Implementation Tasks

**Status**: NOT STARTED (use `/speckit.tasks` to generate)

---

## Dependencies

### External Dependencies (已存在)
- Kafka cluster with topic `ginkgo.live.control.commands`
- Redis cluster for heartbeat storage
- ClickHouse cluster with tables initialized
- Data source APIs (Tushare, EastMoney, etc.)

### Internal Dependencies (Ginkgo)
- `ginkgo.interfaces.kafka_topics` - Kafka主题常量
- `ginkgo.interfaces.dtos.control_command_dto` - 控制命令DTO
- `ginkgo.libs.core.logging` - GLOG日志工具
- `ginkgo.libs.core.config` - GCONF配置管理
- `ginkgo.data.cruds.bar` - Bar数据CRUD
- `ginkgo.data.services.stockinfo_service` - 股票信息服务

### New Dependencies (需添加)
- `ginkgo.workers.data_worker` - Data Worker模块
- `ginkgo.client.data_worker_cli` - CLI命令

---

## Migration Notes

### 从GTM迁移的变更

| 方面 | GTM (当前) | Data Worker (目标) |
|------|-----------|-------------------|
| 进程管理 | `subprocess.Popen` + nohup | Docker容器 |
| 状态追踪 | Redis PID集合 | Redis heartbeat (TTL) |
| 任务调度 | 本地APScheduler | Kafka消息 (TaskTimer发送) |
| 扩展方式 | `start_multi_worker(count=N)` | `docker-compose scale data-worker=N` |
| 故障检测 | 手动PID检查 | Redis TTL自动检测 |

### 兼容性考虑

- 保持Kafka topic `ginkgo.live.control.commands` 兼容
- 保持控制命令格式兼容 (bar_snapshot, update_selector, update_data, heartbeat_test)
- Redis心跳键格式统一为 `heartbeat:{service_type}:{instance_id}`
