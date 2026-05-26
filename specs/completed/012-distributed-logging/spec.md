# Feature Specification: 容器化分布式日志系统

**Feature Branch**: `012-distributed-logging`
**Created**: 2026-02-26
**Status**: Draft
**Input**: User description: "重构日志模块，GLOG从本地的log文件写入调整为支持容器分布式日志"

## Clarifications

### Session 2026-02-26

- Q: 敏感数据脱敏策略？ → A: 配置驱动（通过GCONF配置字段名，灵活可选，默认关闭）
- Q: Trace ID 设置 API？ → A: 上下文变量模式（contextvars，异步安全，GLOG.set_trace_id()设置后自动传播）
- Q: JSON 日志字段规范？ → A: ECS 基础字段 + ginkgo.* 自定义扩展（支持回测特有字段如 strategy_id、portfolio_id）
- Q: 日志框架选型？ → A: 使用 structlog 作为底层，成熟的结构化日志方案，原生支持 JSON 和 context 绑定
- Q: 容器模式本地文件策略？ → A: 完全禁用，调试在宿主机进行（容器只用 stdout/stderr，本地模式保留文件日志）
- Q: 系统级 vs 业务级日志？ → A: 统一输出 + log_category 字段区分（system/backtest，在日志系统中筛选）
- Q: 日志存储架构？ → A: Loki Only（现阶段），通过 stdout/stderr → Promtail → Loki，未来可扩展 ClickHouse
- Q: 业务日志查询方式？ → A: Service层封装Loki查询API（LogService），供Web UI调用查询回测等业务日志

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 容器环境日志聚合 (Priority: P1)

在Kubernetes/Docker容器环境中运行Ginkgo交易系统时，运维人员需要能够从中央日志系统（Loki）查看所有容器的日志，并按时间、容器、服务实例进行筛选和分析。

**Why this priority**: 容器环境中本地文件日志无法持久化且难以集中管理，分布式日志是生产环境的基础设施需求。

**Independent Test**: 可通过部署多容器Ginkgo实例，验证日志是否正确输出到 stdout/stderr 并被 Promtail 采集到 Loki。

**Acceptance Scenarios**:

1. **Given** Ginkgo运行在Docker容器中，**When** 应用启动并产生日志，**Then** 日志以结构化格式（JSON）输出到stdout/stderr
2. **Given** 容器配置了 Promtail + Loki，**When** 日志输出，**Then** 日志包含容器元数据（container_id、pod_name、namespace）并可在 Grafana 中查询
3. **Given** 多个容器实例同时运行，**When** 在 Grafana 中查询，**Then** 可按容器ID/实例名区分不同来源的日志

---

### User Story 2 - 跨容器请求追踪 (Priority: P2)

当一个交易请求从LiveCore（数据层）流转到ExecutionNode（执行层）时，开发者需要能够通过trace_id追踪整个请求链路的日志，便于问题排查和性能分析。

**Why this priority**: 分布式系统中的请求追踪是诊断跨服务问题的关键能力，但非紧急需求。

**Independent Test**: 可通过模拟跨容器调用，验证日志中是否包含一致的trace_id且可在 Loki 中关联所有相关日志。

**Acceptance Scenarios**:

1. **Given** 一个请求进入系统，**When** 请求在多个服务间流转，**Then** 所有相关日志包含相同的trace_id
2. **Given** 日志被采集到 Loki，**When** 在 Grafana 中按 trace_id 筛选，**Then** 返回完整的请求链路日志
3. **Given** 请求处理失败，**When** 使用 trace_id 查询日志，**Then** 可定位到具体失败的服务和原因

---

### User Story 3 - 本地开发兼容模式 (Priority: P3)

开发者在本地非容器环境开发时，仍然可以使用本地文件日志和控制台输出，保持与现有开发体验一致。

**Why this priority**: 保持开发体验，避免强制要求容器环境才能运行，降低开发门槛。

**Independent Test**: 可在本地非Docker环境运行Ginkgo，验证日志是否正常输出到文件和控制台。

**Acceptance Scenarios**:

1. **Given** 非容器环境运行，**When** 产生日志，**Then** 日志写入本地文件（如果配置启用）
2. **Given** 本地运行，**When** 控制台日志开启，**Then** 日志以Rich格式输出到终端
3. **Given** 配置文件未指定日志模式，**When** 系统启动，**Then** 自动检测环境并选择合适的日志模式

---

### User Story 4 - 业务日志查询 (Priority: P2)

在Web UI中查看回测结果时，用户需要能够查看该回测的运行日志，以便了解回测过程中的关键事件和潜在问题。

**Why this priority**: 业务日志查询是用户体验的重要组成部分，但可以通过直接跳转Grafana作为备选方案。

**Independent Test**: 可通过Service层LogService调用Loki API，验证是否能正确查询特定portfolio_id的日志。

**Acceptance Scenarios**:

1. **Given** 一个回测已完成，**When** 用户在Web UI点击"查看日志"，**Then** 显示该回测的所有日志（按portfolio_id过滤）
2. **Given** 日志包含错误信息，**When** 用户筛选错误级别，**Then** 只显示该回测的ERROR级别日志
3. **Given** Loki服务不可用，**When** 用户尝试查询日志，**Then** 返回友好的错误提示而非崩溃

---

### Edge Cases

- 容器重启后日志丢失（容器日志无持久化）：日志由 Loki 持久化存储，保证历史可查
- 日志输出阻塞影响交易性能：stdout/stderr 写入是非阻塞的，结构化序列化开销 < 0.1ms
- Loki 不可用：日志继续输出到 stdout/stderr，由容器平台缓存，不影响应用运行
- 多进程竞争写本地日志：容器环境下完全禁用本地文件日志，宿主机本地模式保留文件支持
- 日志量过大导致OOM：实现日志采样和限流机制（复用现有错误流量控制）
- **多线程上下文隔离**: contextvars 是线程隔离的，每个线程有独立的上下文，不会串；但需要注意在任务结束后调用 clear_context() 清理上下文，避免上下文泄漏
- **异步上下文传播**: contextvars 支持 async/await，追踪上下文会自动传播到所有 await 的子函数；需要在异步函数入口处设置 trace_id

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- **FR-002**: System MUST 使用ServiceHub模式，通过`from ginkgo import services`访问服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、分析层和服务层职责
- **FR-004**: System MUST 使用`@time_logger`、`@retry`、`cache_with_expiration`装饰器进行优化
- **FR-005**: System MUST 提供类型注解，支持静态类型检查

**量化交易特有需求**:
- **FR-006**: System MUST 支持多数据源接入 (ClickHouse/MySQL/MongoDB/Redis)
- **FR-007**: System MUST 支持批量数据操作 (如add_bars而非单条插入)
- **FR-008**: System MUST 集成风险管理系统 (PositionRatioRisk, LossLimitRisk等)
- **FR-009**: System MUST 支持多策略并行回测和实时风控
- **FR-010**: System MUST 遵循TDD开发流程，先写测试再实现功能

**分布式日志核心需求**:
- **FR-LOG-001**: System MUST 支持JSON结构化日志输出，包含timestamp、level、message、logger_name、container_id、trace_id等字段
- **FR-LOG-002**: System MUST 自动检测容器环境（检测DOCKER_CONTAINER、KUBERNETES_SERVICE_HOST等环境变量）
- **FR-LOG-003**: System MUST 在容器环境下仅输出到stdout/stderr，完全禁用本地文件写入（避免多进程竞争，调试使用宿主机本地模式）
- **FR-LOG-004**: System MUST 支持trace_id在日志上下文中传播，实现跨服务请求追踪
- **FR-LOG-005**: System MUST 保持现有GLOG API兼容性（INFO、ERROR等方法签名不变）
- **FR-LOG-006**: System MUST 支持配置驱动的日志模式切换（container/local/auto）
- **FR-LOG-007**: System MUST 在非容器环境下保持本地文件和控制台日志功能
- **FR-LOG-008**: System MUST 实现日志元数据自动注入（hostname、pid、container_id、pod_name等）
- **FR-LOG-009**: System MUST 保持现有的错误流量控制功能（_should_log_error智能限流）
- **FR-LOG-010**: System MUST 支持配置驱动的敏感数据脱敏（通过GCONF指定字段名模式，默认关闭）
- **FR-LOG-011**: System MUST 提供上下文变量模式的trace_id管理（GLOG.set_trace_id()/get_trace_id()，使用contextvars支持异步）
- **FR-LOG-012**: System MUST 基于 structlog 框架实现，利用其原生 JSON 处理器和 context 绑定功能
- **FR-LOG-013**: System MUST 保持现有 GLOG API 兼容性，将调用转发到 structlog 底层
- **FR-LOG-014**: System MUST 支持日志类别区分（log_category: system/backtest），通过统一 logger 输出，在 Loki 中通过标签筛选
- **FR-LOG-015**: System MUST 遵循 TDD 驱动开发流程，先编写测试再实现功能
- **FR-LOG-016**: System MUST 在Service层提供LogService，封装Loki LogQL查询API，支持按portfolio_id、strategy_id、trace_id等字段查询业务日志
- **FR-LOG-017**: LogService MUST 支持分页查询和日志级别过滤，避免返回过大数据集
- **FR-LOG-018**: LogService MUST 优雅处理Loki不可用的情况，返回空结果或友好错误而非异常

**未来扩展性（ClickHouse）**:
- **FR-LOG-FUTURE-001**: 系统架构应预留扩展点，未来可添加 ClickHouse 存储用于复杂业务查询
- **FR-LOG-FUTURE-002**: 日志字段设计应兼容 ClickHouse 表结构，便于后续迁移

**代码维护与文档需求**:
- **FR-014**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-015**: File updates MUST synchronize header descriptions with actual code functionality
- **FR-016**: Header updates MUST be verified during code review process
- **FR-017**: CI/CD pipeline MUST include header accuracy verification

### Key Entities

**日志输出层（libs/core/logger.py）**:
- **GinkgoLogger**: 基于 structlog 的日志记录器，保持现有 API 兼容
- **LogMode**: 日志模式枚举（container/local/auto），决定日志输出方式
- **LogCategory**: 日志类别枚举（system/backtest），用于区分系统级日志和业务级日志
- **TraceContext**: 追踪上下文管理，基于 contextvars 实现

**日志字段结构（structlog event dict）**:
- **ECS 标准字段**: @timestamp, log.level, log.logger, message, process.pid, host.hostname
- **容器元数据**: container.id, kubernetes.pod.name, kubernetes.namespace
- **追踪上下文**: trace.id, span.id
- **Ginkgo 业务字段**: ginkgo.log_category, ginkgo.strategy_id, ginkgo.portfolio_id, ginkgo.event_type, ginkgo.symbol

**日志聚合系统（外部组件）**:
- **Promtail**: 日志采集器，读取容器 stdout/stderr，发送到 Loki
- **Loki**: 日志数据库，存储和索引日志，提供 LogQL 查询 API
- **Grafana**: 可视化界面，通过 LogQL 查询 Loki

**日志查询服务（Service层）**:
- **LogService**: 封装 Loki LogQL 查询 API 的服务层，提供业务日志查询功能
  - `query_logs(portfolio_id, level, limit, offset)`: 按组合ID查询日志
  - `query_by_trace_id(trace_id)`: 按追踪ID查询日志
  - `query_by_strategy_id(strategy_id, limit, offset)`: 按策略ID查询日志
  - 优雅处理 Loki 不可用情况

## Success Criteria *(mandatory)*

### Measurable Outcomes

**性能与响应指标**:
- **SC-LOG-001**: 日志序列化开销 < 0.1ms（JSON 格式化）
- **SC-LOG-002**: stdout/stderr 写入不阻塞业务逻辑（非阻塞 I/O）
- **SC-LOG-003**: 支持 JSON 格式输出，符合 Loki 采集要求

**分布式日志特有指标**:
- **SC-LOG-004**: 100%的日志包含容器元数据（容器环境下）
- **SC-LOG-005**: 95%的请求日志可通过trace_id关联（跨服务场景）
- **SC-LOG-006**: 容器环境自动检测准确率 > 99%
- **SC-LOG-007**: 日志格式符合结构化日志规范（JSON Lines）

**系统兼容性指标**:
- **SC-LOG-008**: 现有GLOG API调用代码无需修改即可运行（向后兼容）
- **SC-LOG-009**: 本地开发环境功能无回归（文件日志、Rich控制台）
- **SC-LOG-010**: 与 Loki 日志系统兼容（Grafana 查询正常）
- **SC-LOG-011**: 现有错误流量控制功能正常工作

**TDD 开发指标**:
- **SC-LOG-012**: 日志模块测试覆盖率 > 85%（GLOG 核心功能测试）
- **SC-LOG-013**: 所有新功能先写测试再实现，测试失败作为 Red 阶段验收标准

**业务与用户体验指标**:
- **SC-LOG-014**: 运维人员可通过 Grafana 在5秒内定位 trace_id 的完整请求链路
- **SC-LOG-015**: 日志查询响应时间 < 2秒（在 Loki 中）
- **SC-LOG-016**: 日志格式化对交易系统性能影响 < 1%
- **SC-LOG-017**: Web UI用户可通过LogService在3秒内获取回测日志（按portfolio_id查询）
- **SC-LOG-018**: LogService在Loki不可用时优雅降级，返回友好错误提示

## Assumptions

1. **日志框架**: 使用 structlog 作为底层实现，其原生支持 JSON 输出和 contextvars 绑定
2. **容器检测标准**: 检测环境变量（DOCKER_CONTAINER、KUBERNETES_SERVICE_HOST、CONTAINER_ID）和文件（/.dockerenv、/proc/1/cgroup）来判断容器环境
3. **日志聚合系统**: 使用 Promtail + Loki 收集 stdout/stderr，应用层输出 JSON 格式，Grafana 提供查询界面
4. **日志存储**: Loki 作为主要日志存储，支持标签索引和 LogQL 查询；未来可扩展 ClickHouse 用于复杂业务查询
5. **Trace ID传播**: 使用 structlog 的 context 绑定功能（基于 contextvars），兼容 W3C Trace Context 格式
6. **配置文件**: 使用GCONF的现有配置系统，新增LOGGING_MODE、LOGGING_FORMAT、LOGGING_MASK_FIELDS等配置项
7. **向后兼容**: 现有代码通过`from ginkgo.libs import GLOG`导入的实例继续工作，内部调用转发到 structlog
8. **新依赖**: 需要添加 `structlog` 到项目依赖（通过 pyproject.toml 或 setup.py）
9. **TDD 流程**: 遵循项目 TDD 规范（Red → Green → Refactor），测试文件位于 `test/unit/libs/test_*`
10. **架构简化**: 当前实现采用 Loki Only 架构，不实现 ClickHouse 写入路径，未来有需求时再扩展
11. **多线程安全**: contextvars 是线程隔离的，每个线程有自己独立的上下文存储，多线程环境下不会串（但多进程各自独立）
12. **异步支持**: contextvars 原生支持 async/await，追踪上下文会自动传播到子协程

## Architecture Overview

### 当前架构（Loki Only）

```
┌─────────────────────────────────────────────────────────────┐
│                    应用代码                                  │
│                  GLOG.INFO("...")                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                structlog 处理层                              │
│  ECS 标准字段 + 容器元数据 + ginkgo.* 业务字段              │
│  输出: JSON Lines to stdout/stderr                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  容器标准输出流                               │
│              stdout/stderr (JSON)                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                             ▼
┌───────────────────┐        ┌─────────────────┐
│   宿主机本地模式   │        │    容器模式      │
│   (开发调试)       │        │    (生产环境)     │
├───────────────────┤        ├─────────────────┤
│ • 文件日志         │        │ • Docker 捕获    │
│ • Rich 控制台      │        │ • Promtail 采集  │
└───────────────────┘        └────────┬────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │        Loki           │
                          │  • 日志存储           │
                          │  • 标签索引           │
                          │  • LogQL 查询 API     │
                          └──────────┬───────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    ▼                                 ▼
        ┌──────────────────────┐          ┌──────────────────────┐
        │       Grafana         │          │     LogService       │
        │  • 运维日志查询        │          │  • 业务日志查询API   │
        │  • Dashboard          │          │  • 供Web UI调用       │
        │  • 可视化             │          │  • 封装LogQL查询     │
        └──────────────────────┘          └──────────────────────┘
```

### 未来扩展（ClickHouse）

```
                                (未来扩展)
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │    ClickHouse        │
                        │  • 复杂业务查询       │
                        │  • 统计分析           │
                        │  • 数据 JOIN         │
                        └──────────────────────┘
```
