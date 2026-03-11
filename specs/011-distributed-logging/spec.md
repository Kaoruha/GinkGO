# Feature Specification: 分布式日志系统优化重构

**Feature Branch**: `011-distributed-logging`
**Created**: 2026-03-09
**Status**: Draft
**Input**: User description: "重构GLOG，按照分布式日志系统优化"

## Clarifications

### Session 2026-03-10

- **Q1: ClickHouse 日志表结构设计** → A: 分表方案（ginkgo_logs_backtest、ginkgo_logs_component、ginkgo_logs_performance）
- **Q2: 性能日志记录的内容** → B: 全选（duration_ms + memory_mb + cpu_percent + throughput + custom_metrics）
- **Q3: 组件日志覆盖范围** → A: 所有核心组件（Strategy、Analyzer、RiskManagement、Sizer、Portfolio、Engine、DataWorker、ExecutionNode）
- **Q4: 回测日志与组件日志的关联方式** → C: 通过 trace_id 关联（使用分布式追踪的 trace_id 关联所有日志）
- **Q5: 不同类型日志的保留策略** → 支持TTL配置清理策略（通过GCONF配置每张表的TTL值）

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 回测日志追踪与查询 (Priority: P1)

量化研究员在执行回测后，需要能够快速查询该回测的完整运行日志，包括策略信号生成、风控触发、订单执行等关键事件，以便分析回测结果和排查问题。

**Why this priority**: 回测日志追踪是量化研究的核心需求，直接影响研发效率和问题诊断能力。

**Independent Test**: 可通过执行一个完整回测，验证日志是否正确记录并可按portfolio_id、strategy_id等维度查询。

**Acceptance Scenarios**:

1. **Given** 一个回测任务已完成，**When** 用户通过LogService按portfolio_id查询日志，**Then** 返回该回测的所有相关日志（按时间排序）
2. **Given** 回测日志包含ERROR级别，**When** 用户筛选错误日志，**Then** 只显示该回测的ERROR和CRITICAL级别日志
3. **Given** 回测正在运行中，**When** 用户实时查询日志，**Then** 能够看到最新的日志输出（延迟<2秒）
4. **Given** 查询包含大量日志的回测，**When** 使用分页查询，**Then** 每页返回指定数量日志并提供总数统计

---

### User Story 2 - Vector 采集架构 (Priority: P1)

系统采用应用无感知的日志采集模式：应用只管输出JSON格式日志到stdout/stderr或日志文件，由Vector采集器负责采集、缓冲、批量写入ClickHouse，实现应用与存储的解耦。

**Why this priority**: Vector采集模式是架构解耦的关键，应用无需关心存储细节，日志采集独立于应用生命周期。

**Independent Test**: 可通过验证GLOG输出JSON日志，Vector采集并写入ClickHouse，应用崩溃后日志仍可被采集。

**Acceptance Scenarios**:

1. **Given** GLOG输出JSON格式日志，**When** Vector读取日志文件，**Then** 日志被正确解析并写入ClickHouse
2. **Given** 应用进程崩溃退出，**When** 已输出到文件的日志，**Then** Vector仍可继续采集并写入ClickHouse
3. **Given** ClickHouse短暂不可用，**When** Vector写入失败，**Then** Vector缓存日志并在ClickHouse恢复后重试，不丢失日志
4. **Given** 日志输出量大，**When** Vector批量写入，**Then** 每100条或5秒批量提交，减少ClickHouse写入压力

---

### User Story 3 - 跨服务请求追踪 (Priority: P2)

当一个交易请求从LiveCore（数据层）流转到ExecutionNode（执行层）时，开发者需要能够通过trace_id追踪整个请求链路的日志，便于问题排查和性能分析。

**Why this priority**: 分布式系统中的请求追踪是诊断跨服务问题的关键能力，提升可观测性。

**Independent Test**: 可通过模拟跨容器调用，验证日志中是否包含一致的trace_id且可在ClickHouse中关联所有相关日志。

**Acceptance Scenarios**:

1. **Given** 一个请求进入系统，**When** 请求在多个服务间流转，**Then** 所有相关日志包含相同的trace_id
2. **Given** 日志被采集到ClickHouse，**When** 按trace_id筛选查询，**Then** 返回完整的请求链路日志（按时间排序）
3. **Given** 请求处理失败，**When** 使用trace_id查询日志，**Then** 可定位到具体失败的服务和错误原因

---

### User Story 4 - 动态日志级别管理 (Priority: P2)

运维人员需要能够在不重启服务的情况下动态调整日志级别，以便在排查问题时临时开启DEBUG日志，问题解决后恢复INFO级别。

**Why this priority**: 动态日志管理显著提升运维效率，避免重启服务带来的业务中断。

**Independent Test**: 可通过CLI命令或HTTP API动态修改日志级别，验证日志输出是否立即生效。

**Acceptance Scenarios**:

1. **Given** 服务当前日志级别为INFO，**When** 执行CLI命令 `ginkgo logging set-level DEBUG --module backtest`，**Then** backtest模块日志立即变为DEBUG级别（无需重启）
2. **Given** 临时开启DEBUG日志，**When** 问题解决后执行 `ginkgo logging reset-level`，**Then** 日志级别恢复为配置文件中的默认值
3. **Given** 通过HTTP API修改日志级别，**When** 调用成功，**Then** 返回当前所有模块的日志级别状态
4. **Given** 设置了动态日志级别，**When** 服务重启，**Then** 日志级别恢复为配置文件中的默认值（动态设置不持久化）

---

### User Story 5 - 日志告警与监控 (Priority: P2)

运维人员需要能够对日志中的异常模式设置告警规则，当特定错误模式出现频率超过阈值时自动发送通知（钉钉、企业微信、邮件）。

**Why this priority**: 日志告警是实现主动运维的关键，能够及时发现系统异常。

**Independent Test**: 可通过配置告警规则并触发相应错误模式，验证告警是否正确发送。

**Acceptance Scenarios**:

1. **Given** 配置了ERROR日志告警规则（5分钟内超过10次），**When** 触发条件满足，**Then** 发送告警通知到配置的渠道（钉钉/企业微信/邮件）
2. **Given** 配置了关键词告警（如"数据库连接失败"），**When** 日志包含该关键词，**Then** 立即发送告警通知
3. **Given** 告警已发送，**When** 相同错误持续触发，**Then** 避免告警风暴（5分钟内同类告警只发送一次）
4. **Given** 告警渠道配置错误，**When** 发送告警失败，**Then** 记录发送失败日志，不影响应用正常运行

---

### User Story 6 - 本地开发兼容模式 (Priority: P3)

开发者在本地非容器环境开发时，仍然可以使用本地文件日志和控制台输出，保持与现有开发体验一致。

**Why this priority**: 保持开发体验，避免强制要求容器环境才能运行，降低开发门槛。

**Independent Test**: 可在本地非Docker环境运行Ginkgo，验证日志是否正常输出到文件和控制台。

**Acceptance Scenarios**:

1. **Given** 非容器环境运行，**When** 产生日志，**Then** 日志写入本地文件（如果配置启用）
2. **Given** 本地运行，**When** 控制台日志开启，**Then** 日志以Rich格式输出到终端
3. **Given** 配置文件未指定日志模式，**When** 系统启动，**Then** 自动检测环境并选择合适的日志模式

---

### Edge Cases

- **应用进程崩溃**: 日志已写入文件，Vector继续采集，不丢失日志
- **Vector进程异常**: 应用继续输出日志到文件，Vector重启后从上次位置继续采集
- **ClickHouse不可用**: Vector缓存日志到磁盘，ClickHouse恢复后重试
- **日志量过大导致OOM**: Vector使用有界缓冲区（最大10000条），超过时丢弃最旧日志并告警
- **多线程上下文隔离**: contextvars是线程隔离的，每个线程有独立上下文；但需在任务结束后调用clear_context()清理上下文
- **异步上下文传播**: contextvars支持async/await，追踪上下文会自动传播到所有await的子函数
- **日志服务查询超时**: LogService查询设置超时限制（5秒），超时返回部分结果或友好错误
- **动态日志级别权限**: 通过GCONF配置允许动态调整的模块白名单，防止误操作影响核心模块
- **告警风暴抑制**: 相同错误模式5分钟内只发送一次告警，避免告警通道被淹没
- **JSON解析失败**: Vector遇到非JSON日志时保留原始消息，记录警告并继续处理

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- **FR-002**: System MUST 使用ServiceHub模式，通过`from ginkgo import services`访问服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、分析层和服务层职责
- **FR-004**: System MUST 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器进行优化
- **FR-005**: System MUST 提供类型注解，支持静态类型检查

**量化交易特有需求**:
- **FR-006**: System MUST 支持多数据源接入 (ClickHouse/MySQL/MongoDB/Redis)
- **FR-007**: System MUST 支持批量数据操作 (如add_bars而非单条插入)
- **FR-008**: System MUST 集成风险管理系统 (PositionRatioRisk, LossLimitRisk等)
- **FR-009**: System MUST 支持多策略并行回测和实时风控
- **FR-010**: System MUST 遵循TDD开发流程，先写测试再实现功能

**分布式日志核心需求**:

*结构化日志基础*:
- **FR-LOG-001**: System MUST 支持JSON结构化日志输出，包含timestamp、level、message、logger_name、trace_id等ECS标准字段
- **FR-LOG-002**: System MUST 自动检测容器环境（检测环境变量和文件标志）
- **FR-LOG-003**: System MUST 在容器环境下输出JSON到stdout/stderr或指定日志文件，本地模式保留文件日志
- **FR-LOG-004**: System MUST 支持trace_id在日志上下文中传播（基于contextvars，异步安全）
- **FR-LOG-005**: System MUST 保持现有GLOG API兼容性（INFO、ERROR等方法签名不变）
- **FR-LOG-006**: System MUST 支持配置驱动的日志模式切换（container/local/auto）
- **FR-LOG-007**: System MUST 实现日志元数据自动注入（hostname、pid、container_id、pod_name等）
- **FR-LOG-008**: System MUST 支持敏感数据脱敏（通过GCONF配置字段名模式，默认关闭）
- **FR-LOG-009**: System MUST 基于structlog框架实现，利用其原生JSON处理器和context绑定功能

*Vector 采集架构*:
- **FR-LOG-010**: System MUST 输出JSON格式日志到stdout/stderr或指定日志文件，供Vector采集
- **FR-LOG-011**: System MUST 在ClickHouse中创建三张日志表：ginkgo_logs_backtest（回测日志）、ginkgo_logs_component（组件日志）、ginkgo_logs_performance（性能日志）
- **FR-LOG-012**: System MUST 支持按日志类型路由到不同的表（通过log_category字段或component_name字段区分）
- **FR-LOG-013**: Vector MUST 支持批量写入ClickHouse（每100条或5秒批量提交），减少写入开销
- **FR-LOG-014**: Vector MUST 在ClickHouse不可用时缓存日志到磁盘，恢复后重试
- **FR-LOG-015**: Vector MUST 支持从文件上次读取位置继续采集（断点续传）
- **FR-LOG-016**: System MUST 支持通过GCONF配置每张表的TTL值（LOGGING_TTL_BACKTEST、LOGGING_TTL_COMPONENT、LOGGING_TTL_PERFORMANCE）

*日志查询服务（LogService）*:
- **FR-LOG-016**: System MUST 在Service层提供LogService，封装ClickHouse SQL查询API
- **FR-LOG-017**: LogService MUST 支持按portfolio_id、strategy_id、trace_id等字段查询日志
- **FR-LOG-018**: LogService MUST 支持分页查询（limit、offset参数）和日志级别过滤
- **FR-LOG-019**: LogService MUST 优雅处理ClickHouse不可用情况，返回友好错误而非异常
- **FR-LOG-020**: LogService MUST 支持时间范围查询（start_time、end_time参数）
- **FR-LOG-021**: LogService MUST 支持关键词全文搜索（message字段LIKE查询）
- **FR-LOG-022**: LogService MUST 支持与回测结果表JOIN查询，实现日志与结果关联分析

*动态日志管理*:
- **FR-LOG-023**: System MUST 支持运行时动态修改日志级别（无需重启服务）
- **FR-LOG-024**: System MUST 提供CLI命令 `ginkgo logging set-level` 和 `ginkgo logging reset-level`
- **FR-LOG-025**: System MUST 支持按模块设置不同日志级别（如backtest模块DEBUG，其他模块INFO）
- **FR-LOG-026**: System MUST 提供HTTP API获取和设置日志级别（供Web UI调用）
- **FR-LOG-027**: 动态日志级别设置 MUST 不持久化，服务重启后恢复配置文件默认值
- **FR-LOG-028**: System MUST 通过GCONF配置允许动态调整的模块白名单，防止误操作

*日志告警与监控*:
- **FR-LOG-029**: System MUST 支持基于ClickHouse查询的告警规则配置（频率阈值、时间窗口）
- **FR-LOG-030**: System MUST 支持关键词告警（如"数据库连接失败"立即告警）
- **FR-LOG-031**: System MUST 支持多种告警渠道（钉钉、企业微信、邮件）
- **FR-LOG-032**: System MUST 实现告警抑制机制（相同错误5分钟内只告警一次）
- **FR-LOG-033**: System MUST 在告警发送失败时记录错误日志，不影响应用运行

*性能优化*:
- **FR-LOG-034**: 日志序列化开销 MUST < 0.1ms（JSON格式化）
- **FR-LOG-035**: 日志写入不阻塞业务逻辑（仅写入文件/stdout，由Vector处理存储）
- **FR-LOG-036**: Vector缓冲区大小 MUST 有界（最大10000条），超过时丢弃最旧日志并告警
- **FR-LOG-037**: System MUST 保持现有的错误流量控制功能（_should_log_error智能限流）
- **FR-LOG-038**: System MUST 支持日志采样（生产环境DEBUG日志采样率10%，减少日志量）

*日志字段扩展*:
- **FR-LOG-039**: System MUST 支持日志类别区分（log_category: backtest/component/performance）
- **FR-LOG-040**: System MUST 支持业务上下文绑定（strategy_id、portfolio_id、event_type、symbol等）
- **FR-LOG-041**: System MUST 提供上下文管理API（bind_context、unbind_context、clear_context）
- **FR-LOG-042**: System MUST 支持span_id用于追踪分布式调用链中的子操作

*性能日志记录*:
- **FR-LOG-043**: System MUST 支持记录方法执行耗时（duration_ms字段）
- **FR-LOG-044**: System MUST 支持记录内存使用情况（memory_mb字段）
- **FR-LOG-045**: System MUST 支持记录CPU使用率（cpu_percent字段）
- **FR-LOG-046**: System MUST 支持记录吞吐量指标（throughput字段）
- **FR-LOG-047**: System MUST 支持自定义性能指标（custom_metrics JSON字段）

*组件日志覆盖*:
- **FR-LOG-048**: System MUST 支持所有核心组件的日志记录（Strategy、Analyzer、RiskManagement、Sizer、Portfolio、Engine、DataWorker、ExecutionNode）
- **FR-LOG-049**: System MUST 在组件日志中包含component_name和component_version字段
- **FR-LOG-050**: System MUST 支持按组件名查询和过滤日志

**日志表 Model 类定义**:
- **FR-LOG-051**: System MUST 为三张日志表定义 SQLAlchemy Model 类（MBacktestLog、MComponentLog、MPerformanceLog），继承自 MClickBase
- **FR-LOG-052**: Model 类 MUST 包含所有列定义（mapped_column），支持类型提示和表结构文档化
- **FR-LOG-053**: Model 类 MUST 支持 CREATE TABLE 语句生成，用于数据库表初始化
- **FR-LOG-054**: GLOG 输出的日志字段 MUST 与对应 Model 类的字段结构匹配，确保 Vector 写入成功
- **FR-LOG-055**: Model 类文件位置: `src/ginkgo/data/models/model_logs.py` (集中管理所有日志模型)
- **FR-LOG-056**: Model 类 MUST 支持通过枚举类型映射处理 level、log_category、event_type 等字段

**代码维护与文档需求**:
- **FR-014**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-015**: File updates MUST synchronize header descriptions with actual code functionality
- **FR-016**: Header updates MUST be verified during code review process
- **FR-017**: CI/CD pipeline MUST include header accuracy verification

**配置验证需求**:
- **FR-018**: 配置类功能验证 MUST 包含配置文件存在性检查（不仅检查返回值）
- **FR-019**: 配置类验证 MUST 确认值从配置文件读取，而非代码默认值
- **FR-020**: 配置类验证 MUST 确认用户可通过修改配置文件改变行为
- **FR-021**: 配置类验证 MUST 确认缺失配置时降级到默认值
- **FR-022**: 外部依赖验证 MUST 包含存在性、正确性、版本兼容性三维度检查
- **FR-023**: 禁止仅因默认值/Mock使测试通过就认为验证完成（假阳性预防）

### Key Entities

**日志输出层（libs/core/logger.py）**:
- **GinkgoLogger**: 基于structlog的日志记录器，保持现有API兼容
  - 输出JSON格式到stdout/stderr或日志文件
  - 现有方法：DEBUG、INFO、WARN、ERROR、CRITICAL
  - 新增方法：bind_context、unbind_context、clear_context、set_trace_id、get_trace_id
  - 新增方法：log_performance(duration_ms, function_name, **metrics)
- **LogMode**: 日志模式枚举（container/local/auto）
- **LogCategory**: 日志类别枚举（backtest/component/performance）
- **LogLevel**: 日志级别枚举（DEBUG/INFO/WARNING/ERROR/CRITICAL）

**日志采集层（Vector）**:
- **Vector**: 开源日志采集和转换工具（Rust编写）
  - 读取日志文件（/var/log/ginkgo/*.log）
  - 解析JSON格式
  - 批量写入ClickHouse
  - 支持断点续传（记录读取位置）
  - ClickHouse不可用时缓存到磁盘

**日志查询服务（services/logging/log_service.py）**:
- **LogService**: 日志查询服务，封装ClickHouse SQL查询，支持分表查询
  - 回测日志查询: `query_backtest_logs(portfolio_id, strategy_id, level, limit, offset)`
  - 组件日志查询: `query_component_logs(component_name, level, limit, offset)`
  - 性能日志查询: `query_performance_logs(function_name, min_duration, limit)`
  - 跨表查询: `query_by_trace_id(trace_id)` - 跨所有表通过trace_id查询
  - 关键词搜索: `search_logs(keyword, level, time_range, tables)`
  - 关联查询: `join_with_backtest_results(portfolio_id)` - 与回测结果表JOIN

**日志告警服务（services/logging/alert_service.py）**:
- **AlertService**: 日志告警服务
  - `check_error_patterns()`: 检查错误模式是否触发告警（查询ClickHouse）
  - `send_alert(alert_message)`: 发送告警通知
  - `add_alert_rule(pattern, threshold, time_window)`: 添加告警规则
  - 支持多种告警渠道：钉钉、企业微信、邮件

**动态日志管理（services/logging/level_service.py）**:
- **LevelService**: 日志级别管理服务
  - `set_level(module, level)`: 设置指定模块的日志级别
  - `get_levels()`: 获取所有模块的当前日志级别
  - `reset_levels()`: 重置为配置文件默认值
  - 提供HTTP API接口

**ClickHouse日志表（分表设计）**:

*回测日志表（ginkgo_logs_backtest）*:
- **用途**: 记录回测任务的业务日志（策略信号、风控触发、订单执行等）
- **字段**:
  - 基础字段: timestamp、level、message、logger_name
  - 追踪字段: trace_id、span_id
  - 业务字段: portfolio_id、strategy_id、event_type、symbol、direction、volume、price
  - 元数据字段: hostname、pid、container_id、task_id、ingested_at
- **索引**: timestamp、trace_id、portfolio_id、strategy_id、level
- **分区**: (toDate(timestamp), portfolio_id) 按日期和组合ID复合分区
- **TTL**: 通过GCONF配置（默认180天，可调整）
- **引擎**: MergeTree()
- **排序键**: (timestamp, portfolio_id, trace_id)

*组件日志表（ginkgo_logs_component）*:
- **用途**: 记录各核心组件的运行日志（Strategy、Analyzer、RiskManagement、Sizer、Portfolio、Engine、DataWorker、ExecutionNode）
- **字段**:
  - 基础字段: timestamp、level、message、logger_name
  - 追踪字段: trace_id、span_id
  - 组件字段: component_name、component_version、component_instance、module_name
  - 元数据字段: hostname、pid、container_id、task_id、ingested_at
- **索引**: timestamp、trace_id、component_name、level、hostname
- **分区**: (toDate(timestamp), component_name) 按日期和组件名复合分区
- **TTL**: 通过GCONF配置（默认90天，可调整）
- **引擎**: MergeTree()
- **排序键**: (timestamp, component_name, trace_id)

*性能日志表（ginkgo_logs_performance）*:
- **用途**: 记录性能监控数据（方法执行耗时、资源使用、吞吐量等）
- **字段**:
  - 基础字段: timestamp、level、message、logger_name
  - 追踪字段: trace_id、span_id
  - 性能字段: duration_ms、memory_mb、cpu_percent、throughput、custom_metrics（JSON）
  - 上下文字段: function_name、module_name、call_site
  - 元数据字段: hostname、pid、container_id、task_id、ingested_at
- **索引**: timestamp、trace_id、function_name、duration_ms、level
- **分区**: (toDate(timestamp), level) 按日期和日志级别复合分区
- **TTL**: 通过GCONF配置（默认30天，可调整）
- **引擎**: MergeTree()
- **排序键**: (timestamp, trace_id, function_name)

*TTL配置说明*:
- 通过GCONF配置每张表的TTL值:
  - `GCONF.LOGGING_TTL_BACKTEST = 180`（天）
  - `GCONF.LOGGING_TTL_COMPONENT = 90`（天）
  - `GCONF.LOGGING_TTL_PERFORMANCE = 30`（天）
- 支持运行时动态修改TTL，ClickHouse会自动清理过期数据

**Vector配置（vector.toml）**:
- **输入源**: 读取日志文件 /var/log/ginkgo/**/*.log
- **路由转换**: 根据 log_category 字段路由到不同 sink
- **输出**: 三个 sink 分别对应三张日志表
- **批量配置**: batch.max_events = 100, batch.timeout_secs = 5

**日志表 SQLAlchemy Model 类**:
- **文件位置**: `src/ginkgo/data/models/model_logs.py`
- **MBacktestLog**: 回测日志表 Model 类
  - 继承 MClickBase，使用 mapped_column 定义所有字段
  - 字段包括：timestamp, level, message, logger_name, trace_id, span_id, portfolio_id, strategy_id, event_type, symbol, direction, volume, price, hostname, pid, container_id, task_id, ingested_at
  - 支持通过枚举类型映射处理 level 字段
- **MComponentLog**: 组件日志表 Model 类
  - 继承 MClickBase，使用 mapped_column 定义所有字段
  - 字段包括：timestamp, level, message, logger_name, trace_id, span_id, component_name, component_version, component_instance, module_name, hostname, pid, container_id, task_id, ingested_at
- **MPerformanceLog**: 性能日志表 Model 类
  - 继承 MClickBase，使用 mapped_column 定义所有字段
  - 字段包括：timestamp, level, message, logger_name, trace_id, span_id, duration_ms, memory_mb, cpu_percent, throughput, custom_metrics(JSON), function_name, module_name, hostname, pid, container_id, task_id, ingested_at
- **表创建**: Model 类 MUST 支持 `create_all()` 方法生成 CREATE TABLE 语句
- **类型校验**: GLOG 输出日志前通过 Model 类进行字段校验，确保结构匹配

## Success Criteria *(mandatory)*

### Measurable Outcomes

**性能与响应指标**:
- **SC-LOG-001**: 日志序列化开销 < 0.1ms（JSON格式化）
- **SC-LOG-002**: 日志写入不阻塞业务逻辑（仅写入文件/stdout）
- **SC-LOG-003**: Vector内存占用 < 200MB（有界缓冲区）

**分布式日志功能指标**:
- **SC-LOG-004**: 100%的日志包含ECS标准字段
- **SC-LOG-005**: 95%的请求日志可通过trace_id关联（跨服务场景）
- **SC-LOG-006**: 容器环境自动检测准确率 > 99%
- **SC-LOG-007**: 日志格式符合结构化日志规范（JSON Lines）

**Vector采集架构指标**:
- **SC-LOG-008**: 日志从输出到ClickHouse可查询延迟 < 10秒
- **SC-LOG-009**: ClickHouse写入成功率 > 99.9%
- **SC-LOG-010**: Vector断点续传准确率 100%（不丢失、不重复）
- **SC-LOG-011**: ClickHouse不可用时Vector缓存到磁盘，恢复后重试成功率 > 95%
- **SC-LOG-012**: Vector批量写入吞吐量 > 10000条/秒

**日志查询功能指标**:
- **SC-LOG-013**: 按portfolio_id查询日志返回时间 < 3秒
- **SC-LOG-014**: 关键词全文搜索响应时间 < 5秒
- **SC-LOG-015**: 分页查询支持百万级日志数据集
- **SC-LOG-016**: 与回测结果表JOIN查询响应时间 < 5秒

**动态日志管理指标**:
- **SC-LOG-017**: 动态修改日志级别生效时间 < 1秒（无需重启）
- **SC-LOG-018**: 日志级别CLI命令响应时间 < 500ms
- **SC-LOG-019**: HTTP API获取日志级别响应时间 < 200ms

**日志告警指标**:
- **SC-LOG-020**: 告警规则触发后通知发送延迟 < 10秒
- **SC-LOG-021**: 告警抑制准确率 100%（5分钟内同类告警只发送一次）
- **SC-LOG-022**: 告警发送失败不影响应用运行

**系统兼容性指标**:
- **SC-LOG-023**: 现有GLOG API调用代码无需修改即可运行（向后兼容）
- **SC-LOG-024**: 本地开发环境功能无回归（文件日志、Rich控制台）
- **SC-LOG-025**: 现有错误流量控制功能正常工作

**TDD开发指标**:
- **SC-LOG-026**: 日志模块测试覆盖率 > 85%（GLOG核心功能测试）
- **SC-LOG-027**: 所有新功能先写测试再实现，测试失败作为Red阶段验收标准

**业务与用户体验指标**:
- **SC-LOG-028**: 用户可在3秒内查询到指定回测的完整日志
- **SC-LOG-029**: 运维人员可通过trace_id在5秒内定位完整请求链路
- **SC-LOG-030**: 日志格式化对交易系统性能影响 < 1%

## Assumptions

1. **日志框架**: 使用structlog作为底层实现，原生支持JSON输出和contextvars绑定
2. **容器检测标准**: 检测环境变量（DOCKER_CONTAINER、KUBERNETES_SERVICE_HOST）和文件（/.dockerenv、/proc/1/cgroup）
3. **日志采集系统**: 使用Vector作为日志采集器，采集stdout/stderr或日志文件，写入ClickHouse
4. **Trace ID传播**: 使用structlog的context绑定功能（基于contextvars），兼容W3C Trace Context格式，作为跨表关联的主要方式
5. **配置文件**: 使用GCONF现有配置系统，新增LOGGING_MODE、LOGGING_JSON_OUTPUT、LOGGING_TTL_*等配置项
6. **向后兼容**: 现有代码通过`from ginkgo.libs import GLOG`导入的实例继续工作，内部调用转发到structlog
7. **新依赖**: 需要添加Vector作为独立服务（Docker容器或二进制部署）
8. **TDD流程**: 遵循项目TDD规范（Red → Green → Refactor），测试文件位于`tests/unit/libs/test_*`
9. **多线程安全**: contextvars是线程隔离的，每个线程有独立上下文
10. **异步支持**: contextvars原生支持async/await，追踪上下文会自动传播到子协程
11. **告警渠道配置**: 通过GCONF配置钉钉webhook、企业微信webhook、SMTP服务器等信息
12. **日志采样策略**: 生产环境DEBUG日志采样率10%，ERROR和CRITICAL日志100%记录
13. **分表设计**: ClickHouse使用三张表分别存储回测日志、组件日志、性能日志，通过trace_id关联
14. **TTL配置**: 通过GCONF配置每张表的TTL值（LOGGING_TTL_BACKTEST默认180天、LOGGING_TTL_COMPONENT默认90天、LOGGING_TTL_PERFORMANCE默认30天）
15. **Vector部署**: Vector作为独立容器部署，通过Docker Compose或Kubernetes配置
16. **模块白名单**: 允许动态调整日志级别的模块：backtest、trading、data、analysis；核心模块（libs、services）不允许动态调整
17. **日志文件路径**: 容器环境输出到/var/log/ginkgo/{task_type}/*.log（按任务类型分目录），本地环境输出到~/.ginkgo/logs/
18. **Vector高可用**: 单个Vector实例足够（采集多个日志文件），支持断点续传，无需主备架构
19. **组件覆盖**: 组件日志覆盖所有核心组件（Strategy、Analyzer、RiskManagement、Sizer、Portfolio、Engine、DataWorker、ExecutionNode）
20. **性能指标**: 性能日志包含完整指标（duration_ms、memory_mb、cpu_percent、throughput、custom_metrics）

## Architecture Overview

### Vector 采集架构（分表设计）

```
┌─────────────────────────────────────────────────────────────┐
│                    应用代码                                  │
│                  GLOG.INFO("...")                            │
│                  GLOG.log_performance(duration_ms=100, ...)    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                structlog 处理层                              │
│  ECS 标准字段 + 容器元数据 + ginkgo.* 业务字段              │
│  输出: JSON Lines (包含 log_category 字段用于路由)          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              日志文件 / stdout                               │
│  /var/log/ginkgo/backtest/*.log                            │
│  /var/log/ginkgo/component/*.log                           │
│  /var/log/ginkgo/performance/*.log                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vector                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 输入源: 读取日志文件（支持通配符）                    │   │
│  │ - 文件监控 (inotify)                                  │   │
│  │ - 断点续传 (记录读取位置)                              │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 路由转换: 根据 log_category 路由到不同表             │   │
│  │ - backtest → ginkgo_logs_backtest                    │   │
│  │ - component → ginkgo_logs_component                  │   │
│  │ - performance → ginkgo_logs_performance             │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 缓冲: 内存缓冲 (最大10000条)                          │   │
│  │ - ClickHouse不可用时缓存到磁盘                       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 输出: 批量写入 ClickHouse                             │   │
│  │ - 每100条或5秒批量提交                               │   │
│  │ - 三个sink对应三张表                                │   │
│  │ - 重试机制（指数退避）                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  ClickHouse（分表架构）                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ginkgo_logs_backtest (TTL: 180天)                    │   │
│  │ - 分区: (toDate(timestamp), portfolio_id)            │   │
│  │ - 用途: 回测业务日志                                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ ginkgo_logs_component (TTL: 90天)                    │   │
│  │ - 分区: (toDate(timestamp), component_name)          │   │
│  │ - 用途: 组件运行日志                                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ ginkgo_logs_performance (TTL: 30天)                  │   │
│  │ - 分区: (toDate(timestamp), level)                   │   │
│  │ - 用途: 性能监控数据                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                          │
│  通过 trace_id 关联所有表的日志                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 LogService                                  │
│  • query_by_trace_id(trace_id) - 跨所有表查询             │
│  • query_backtest_logs(portfolio_id) - 回测日志查询        │
│  • query_component_logs(component_name) - 组件日志查询     │
│  • query_performance_logs(min_duration) - 性能日志查询     │
│  • 关联查询: 与回测结果表JOIN                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Web UI                                     │
│  • 回测日志查询                                              │
│  • 组件日志查询                                              │
│  • 性能监控面板                                              │
│  • 日志搜索                                                  │
│  • 错误日志筛选                                              │
└─────────────────────────────────────────────────────────────┘
```
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  ClickHouse                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ginkgo_logs 表                                        │   │
│  │ - 字段: timestamp, level, message, trace_id,         │   │
│  │         portfolio_id, strategy_id, ...               │   │
│  │ - 索引: timestamp, trace_id, portfolio_id, level     │   │
│  │ - 分区: toDate(timestamp)                            │   │
│  │ - TTL: 90天                                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 LogService                                  │
│  • 封装ClickHouse SQL查询                                    │
│  • 按portfolio_id、trace_id、strategy_id查询                │
│  • 分页、时间范围、关键词搜索                                │
│  • 与回测结果表JOIN                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Web UI                                     │
│  • 回测日志查询                                              │
│  • 日志搜索                                                  │
│  • 错误日志筛选                                              │
└─────────────────────────────────────────────────────────────┘
```

### 动态日志管理架构

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI命令                                  │
│  ginkgo logging set-level DEBUG --module backtest          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                LevelService                                 │
│  • 解析命令参数                                              │
│  • 验证模块白名单                                            │
│  • 调用GLOG.set_level()                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                GinkgoLogger                                 │
│  • 动态修改handler级别                                       │
│  • 无需重启服务                                              │
└─────────────────────────────────────────────────────────────┘

                      (HTTP API 并行路径)
┌─────────────────────────────────────────────────────────────┐
│              Web UI → FastAPI → LevelService                │
└─────────────────────────────────────────────────────────────┘
```

### 日志告警架构

```
┌─────────────────────────────────────────────────────────────┐
│            AlertService (后台任务)                          │
│  • 定期查询ClickHouse错误日志                                │
│  • 匹配告警规则（频率阈值、关键词）                           │
│  • 检查告警抑制（5分钟内是否已发送）                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              告警发送器                                      │
│  • 钉钉 Webhook                                             │
│  • 企业微信 Webhook                                          │
│  • SMTP Email                                               │
└─────────────────────────────────────────────────────────────┘
```

### Trace ID 传播架构

```
┌─────────────────────────────────────────────────────────────┐
│          LiveCore (数据层)                                   │
│  GLOG.set_trace_id("trace-123")                             │
│  GLOG.INFO("Price update received")  ← 包含 trace-123       │
│         ↓ (JSON日志输出到文件)                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ {"timestamp": "...", "level": "info",                 │   │
│  │  "trace_id": "trace-123", "message": "..."}          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                      │ (Kafka消息携带trace_id)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│          ExecutionNode (执行层)                              │
│  GLOG.set_trace_id(kafka_message.trace_id)  ← 恢复上下文    │
│  GLOG.INFO("Processing order")  ← 包含相同的 trace-123      │
└─────────────────────────────────────────────────────────────┘

查询时: LogService.query_by_trace_id("trace-123")
  → ClickHouse SQL: WHERE trace_id = 'trace-123' ORDER BY timestamp
  → 返回完整链路日志（按时间排序）
```

### Vector 配置示例

```toml
# vector.toml

# 输入源：读取Ginkgo日志文件
[sources.ginkgo_logs]
type = "file"
include = ["/var/log/ginkgo/*.log"]
read_from = "beginning"
  # 断点续传：Vector会记录读取位置

# 转换：确保JSON格式并添加采集时间
[transforms.parse_json]
inputs = ["ginkgo_logs"]
type = "remap"
source = """
  # 如果消息不是JSON对象，尝试解析
  if exists(.message) && is_string(.message) {
    . = parse_json!(.message)
  }
  # 添加Vector采集时间戳
  .ingested_at = now()
"""

# 输出：写入ClickHouse
[sinks.clickhouse]
inputs = ["parse_json"]
type = "clickhouse"
database = "ginkgo"
table = "ginkgo_logs"
endpoint = "http://clickhouse-server:8123"

# 批量配置
batch.max_events = 100          # 每100条批量提交
batch.timeout_secs = 5          # 或5秒超时

# 重试配置
retry_max_attempts = 5          # 最多重试5次
retry_secs = 1                  # 初始重试间隔1秒

# 缓冲区配置（ClickHouse不可用时）
buffer.type = "disk"            # 缓存到磁盘
buffer.max_size = 10485760      # 最大10MB

# 健康检查
healthcheck.enabled = true
```
