# Implementation Plan: 分布式日志系统优化重构

**Branch**: `011-distributed-logging` | **Date**: 2026-03-10 | **Spec**: [spec.md](./spec.md)

## Summary

本功能对 GLOG（Ginkgo 日志系统）进行完整重构，实现基于 Vector + ClickHouse 的分布式日志系统。主要解决现有系统的功能缺失、可观测性不足和运维不便等问题。

**核心变更**:
1. 基于 structlog 重构日志输出，支持 JSON 格式和 contextvars 追踪
2. Vector 采集日志文件，批量写入 ClickHouse（应用无感知模式）
3. 三张日志表分离设计（backtest、component、performance），通过 trace_id 关联
4. 新增 SQLAlchemy Model 类（MBacktestLog、MComponentLog、MPerformanceLog）
5. 动态日志级别管理（CLI + HTTP API）
6. 日志告警服务（支持钉钉、企业微信、邮件）

---

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: structlog, clickhouse-sqlalchemy, Vector, ClickHouse, Rich, Pydantic
**Storage**: ClickHouse（三张日志表独立存储）
**Testing**: pytest with TDD workflow, unit/integration/database 标记分类
**Target Platform**: Linux 服务器（Docker 容器部署）
**Project Type**: single（Python 量化交易库）
**Performance Goals**:
- 日志序列化开销 < 0.1ms
- 日志写入不阻塞业务逻辑
- Vector 内存占用 < 200MB
- 日志从输出到 ClickHouse 可查询延迟 < 10 秒

**Constraints**:
- 必须启用 debug 模式进行数据库操作
- 遵循事件驱动架构
- 支持分布式 worker
- 保持现有 GLOG API 向后兼容

**Scale/Scope**:
- 支持多策略并行回测日志追踪
- 处理千万级日志数据查询
- 实时风控监控日志记录

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理（Vector 配置通过环境变量注入）
- [x] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构（日志不阻塞事件处理流程）
- [x] 使用 ServiceHub 统一访问服务（LogService、LevelService、AlertService 从容器获取）
- [x] 严格分离数据层（ClickHouse）、采集层（Vector）、输出层（GLOG）职责

### 代码质量原则 (Code Quality)
- [x] 使用 `@time_logger`、`@retry`、`@cache_with_expiration` 装饰器（LogService 查询方法）
- [x] 提供类型注解，支持静态类型检查（所有新增方法）
- [x] 禁止使用 hasattr 等反射机制回避类型错误
- [x] 遵循既定命名约定（Model 类继承 MClickBase，CRUD 操作使用 add_/get_ 前缀）

### 测试原则 (Testing Excellence)
- [x] 遵循 TDD 流程，先写测试再实现功能
- [x] 测试按 unit、integration、database 标记分类
- [x] 数据库测试使用测试数据库，避免影响生产数据

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法（Vector 批量写入 ClickHouse）
- [x] 合理使用多级缓存（LevelService 使用内存缓存日志级别）
- [x] 使用懒加载机制优化启动时间（structlog 延迟配置）

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多 5 个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确，高优先级任务优先显示
- [x] 任务状态实时更新，确保团队协作效率

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [x] 核心 API 提供详细使用示例和参数说明（contracts/ 目录）
- [x] 重要组件有清晰的架构说明和设计理念文档（research.md）

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新 Role 描述
- [x] 修改模块依赖关系时，更新 Upstream/Downstream 描述
- [x] 代码审查过程中检查头部信息的准确性
- [x] 定期运行 `scripts/verify_headers.py` 检查头部一致性
- [x] CI/CD 流程包含头部准确性检查
- [x] 使用 `scripts/generate_headers.py --force` 批量更新头部

### 验证完整性原则 (Verification Integrity)
- [x] 配置类功能验证包含配置文件检查（GCONF.LOGGING_* 配置项）
- [x] 验证配置文件包含对应配置项
- [x] 验证值从配置文件读取，而非代码默认值
- [x] 验证用户可通过修改配置文件改变行为
- [x] 验证缺失配置时降级到默认值
- [x] 外部依赖验证包含存在性、正确性、版本兼容性三维度检查
- [x] 禁止仅因默认值/Mock 使测试通过就认为验证完成

### DTO消息队列原则 (DTO Message Pattern)
- [x] 所有 Kafka 消息发送使用 DTO 包装（trace_id 通过 ControlCommandDTO 传播）
- [x] 发送端使用 DTO.model_dump_json() 序列化
- [x] 接收端使用 DTO(**data) 反序列化
- [x] 使用 DTO.Commands 常量类定义命令/事件类型
- [x] 使用 DTO.is_xxx() 方法进行类型判断
- [x] 禁止直接发送字典或裸 JSON 字符串到 Kafka
- [x] DTO 使用 Pydantic BaseModel 实现类型验证

**Status**: ✅ PASSED（所有原则检查通过）

---

## Project Structure

### Documentation (this feature)

```text
specs/011-distributed-logging/
├── plan.md              # This file
├── research.md          # Phase 0 output（技术调研）
├── data-model.md        # Phase 1 output（数据模型）
├── quickstart.md        # Phase 1 output（快速入门）
├── contracts/           # Phase 1 output（API 契约）
│   ├── log_service_api.md
│   ├── level_service_api.md
│   └── alert_service_api.md
└── tasks.md             # Phase 2 output（/speckit.tasks 命令生成）
```

### Source Code (repository root)

```text
# 新增文件
src/ginkgo/
├── data/models/
│   └── model_logs.py                 # 日志表 Model 类（MBacktestLog、MComponentLog、MPerformanceLog）
├── enums.py                          # 新增 LEVEL_TYPES、LOG_CATEGORY_TYPES 枚举
├── libs/core/
│   └── logger.py                     # 重构 GLOG，基于 structlog
├── services/logging/
│   ├── __init__.py
│   ├── log_service.py                # 日志查询服务（重构现有 LokiLogService）
│   ├── level_service.py              # 日志级别管理服务（新增）
│   └── alert_service.py              # 日志告警服务（新增）
└── interfaces/dtos/
    └── logging_dto.py                # 日志相关 DTO（如需要）

# 修改文件
src/ginkgo/
├── data/models/__init__.py           # 导出新增的 Model 类
└── enums.py                          # 新增日志相关枚举

# 配置文件
~/.ginkgo/
└── config.yaml                       # 新增 logging.* 配置项

# Vector 配置
deploy/
├── vector/
│   └── vector.toml                   # Vector 采集配置
└── docker-compose.yml                # 新增 Vector 服务

# 测试文件
tests/unit/libs/
└── test_logger.py                    # GLOG 单元测试
tests/unit/services/logging/
├── test_log_service.py               # LogService 单元测试
├── test_level_service.py             # LevelService 单元测试
└── test_alert_service.py             # AlertService 单元测试

# CLI 命令
src/ginkgo/cli/
└── logging_cli.py                    # 新增 logging 命令组（ginkgo logging）

# 脚本
scripts/
└── init_logging_tables.py             # 日志表初始化脚本
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 三表分离设计 | 不同类型日志的查询模式、TTL 需求、字段差异大 | 单表方案会导致索引效率低、TTL 配置复杂、存储浪费 |
| Vector 独立部署 | 应用无感知采集模式，应用崩溃不影响日志采集 | 应用直写 ClickHouse 会导致应用与存储强耦合，ClickHouse 不可用影响业务 |
| contextvars 追踪 | Python 标准库原生支持异步上下文传播 | 手动传递 trace_id 容易遗漏，不支持自动异步传播 |

---

## Research Summary (Phase 0)

**Research 文件**: [research.md](./research.md)

### 关键技术决策

1. **日志框架**: structlog（JSON 输出、contextvars 支持）
2. **采集架构**: Vector + ClickHouse（应用解耦、高性能）
3. **存储设计**: 三表分离（backtest、component、performance）
4. **Model 类**: SQLAlchemy Model 类（MBacktestLog、MComponentLog、MPerformanceLog）
5. **枚举类型**: LEVEL_TYPES、LOG_CATEGORY_TYPES
6. **追踪机制**: contextvars + trace_id
7. **部署模式**: Docker Compose 单实例 Vector

---

## Data Model Summary (Phase 1)

**Data Model 文件**: [data-model.md](./data-model.md)

### 枚举类型

- `LEVEL_TYPES`: DEBUG、INFO、WARNING、ERROR、CRITICAL
- `LOG_CATEGORY_TYPES`: BACKTEST、COMPONENT、PERFORMANCE

### ClickHouse 表

| 表名 | 用途 | TTL | 分区策略 |
|------|------|-----|----------|
| ginkgo_logs_backtest | 回测业务日志 | 180 天 | (toDate(timestamp), portfolio_id) |
| ginkgo_logs_component | 组件运行日志 | 90 天 | (toDate(timestamp), component_name) |
| ginkgo_logs_performance | 性能监控日志 | 30 天 | (toDate(timestamp), level) |

### SQLAlchemy Model 类

- `MBacktestLog`: 回测日志 Model（包含 portfolio_id、strategy_id、event_type 等业务字段）
- `MComponentLog`: 组件日志 Model（包含 component_name、module_name 等组件字段）
- `MPerformanceLog`: 性能日志 Model（包含 duration_ms、memory_mb、cpu_percent 等性能字段）

---

## API Contracts Summary (Phase 1)

**Contracts 目录**: [contracts/](./contracts/)

### LogService

日志查询服务，封装 ClickHouse SQL 查询 API：
- `query_backtest_logs()`: 查询回测日志
- `query_component_logs()`: 查询组件日志
- `query_performance_logs()`: 查询性能日志
- `query_by_trace_id()`: 跨表查询（完整链路）
- `search_logs()`: 关键词全文搜索
- `join_with_backtest_results()`: 与回测结果表 JOIN
- `get_log_count()`: 日志数量统计

### LevelService

日志级别管理服务，支持动态调整：
- `set_level()`: 设置模块日志级别
- `get_level()`: 获取模块日志级别
- `get_all_levels()`: 获取所有模块日志级别
- `reset_levels()`: 重置为配置文件默认值

**CLI 命令**:
- `ginkgo logging set-level`: 设置日志级别
- `ginkgo logging get-level`: 获取日志级别
- `ginkgo logging reset-level`: 重置日志级别

### AlertService

日志告警服务，支持多种告警渠道：
- `add_alert_rule()`: 添加告警规则
- `remove_alert_rule()`: 移除告警规则
- `check_error_patterns()`: 检查告警规则
- `send_alert()`: 发送告警通知
- `get_alert_rules()`: 获取告警规则

**告警渠道**: 钉钉、企业微信、邮件

---

## Quickstart Summary (Phase 1)

**Quickstart 文件**: [quickstart.md](./quickstart.md)

### 基本使用

```python
from ginkgo.libs import GLOG

# 基础日志输出
GLOG.info("这是一条信息日志")

# 绑定业务上下文
GLOG.bind_context(portfolio_id="portfolio-001", strategy_id="strategy-ma")
GLOG.info("信号生成成功")

# 设置追踪 ID
GLOG.set_trace_id("trace-abc-123")
GLOG.info("处理订单")

# 记录性能日志
GLOG.log_performance(duration_ms=123.45, function_name="calculate_signals")
```

---

## Next Steps

1. **Phase 2 (Task Generation)**: 运行 `/speckit.tasks` 生成 tasks.md
2. **Phase 3 (Implementation)**: 运行 `/speckit.implement` 执行实现

---

## Constitution Check Re-evaluation (Post-Design)

*Phase 1 设计后的章程重新评估*

### 评估结果

所有 10 项章程原则在设计阶段得到充分遵守：

1. **安全与合规**: 敏感信息通过环境变量和配置文件管理
2. **架构设计**: 遵循事件驱动架构，使用 ServiceHub 统一访问服务
3. **代码质量**: 所有新增代码提供类型注解，使用装饰器优化
4. **测试原则**: 遵循 TDD 流程，测试分类标记
5. **性能原则**: 批量写入、多级缓存、懒加载
6. **任务管理**: 后续 tasks.md 将保持 5 个活跃任务
7. **文档原则**: 完整的中文文档和 API 契约
8. **代码注释同步**: 新文件头部包含 Upstream/Downstream/Role
9. **验证完整性**: 配置验证包含配置文件检查
10. **DTO 消息队列**: trace_id 通过 DTO 跨容器传播

**Status**: ✅ PASSED（设计阶段章程检查通过）
