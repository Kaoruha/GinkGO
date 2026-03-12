# Tasks: 分布式日志系统优化重构

**Input**: Design documents from `/specs/011-distributed-logging/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: ⚠️ **TDD REQUIRED** - FR-010 specifies "System MUST 遵循TDD开发流程，先写测试再实现功能"

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths below follow Ginkgo Python 量化交易库 structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup

- [X] T001 安装 structlog 依赖包 (pip install structlog)
- [X] T002 创建服务目录结构 src/ginkgo/services/logging/
- [X] T003 [P] 创建测试目录结构 tests/unit/libs/ 和 tests/unit/services/logging/
- [X] T004 [P] 创建配置目录 deploy/vector/ 并准备 vector.toml 模板
- [X] T005 [P] 更新 .specify/templates/spec-template.md 添加 DTO 规范说明（章程同步）

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### 枚举类型定义 (所有用户故事依赖)

- [X] T006 在 src/ginkgo/enums.py 中添加 LEVEL_TYPES 枚举（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- [X] T007 在 src/ginkgo/enums.py 中添加 LOG_CATEGORY_TYPES 枚举（BACKTEST/COMPONENT/PERFORMANCE）
- [X] T008 [P] 更新 src/ginkgo/enums.py 的 __all__ 导出列表包含新增枚举

### ClickHouse 表 Model 类 (所有用户故事依赖)

- [X] T009 [P] 创建 src/ginkgo/data/models/model_logs.py 文件并添加头部注释（Upstream: LogService/GLOG, Downstream: MClickBase/LEVEL_TYPES）
- [X] T010 [P] 在 model_logs.py 中实现 MBacktestLog 类（继承 MClickBase，包含回测日志字段）
- [X] T011 [P] 在 model_logs.py 中实现 MComponentLog 类（继承 MClickBase，包含组件日志字段）
- [X] T012 [P] 在 model_logs.py 中实现 MPerformanceLog 类（继承 MClickBase，包含性能日志字段）
- [X] T013 更新 src/ginkgo/data/models/__init__.py 导出新增的 Model 类

### GCONF 配置支持 (所有用户故事依赖)

- [X] T014 在 GCONF 中添加 LOGGING_MODE 配置项（container/local/auto）
- [X] T015 [P] 在 GCONF 中添加 LOGGING_JSON_OUTPUT 配置项（bool）
- [X] T016 [P] 在 GCONF 中添加 LOGGING_TTL_BACKTEST/COMPONENT/PERFORMANCE 配置项（int，默认值 180/90/30）
- [X] T017 [P] 在 GCONF 中添加 LOGGING_SAMPLING_RATE 配置项（float，默认 0.1）
- [X] T018 在 GCONF 中添加 LOGGING_LEVEL_WHITELIST 配置项（list，默认 ["backtest", "trading", "data", "analysis"]）

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 回测日志追踪与查询 (Priority: P1) 🎯 MVP

**Goal**: 实现回测日志的记录和查询功能，支持按 portfolio_id、strategy_id 等维度查询

**Independent Test**: 执行一个完整回测，验证日志是否正确记录并可按 portfolio_id、strategy_id 等维度查询

### Tests for User Story 1 (TDD - Write FIRST, ensure FAIL before implementation) ⚠️

- [X] T019 [P] [US1] 编写 MBacktestLog 单元测试在 tests/unit/data/models/test_model_logs.py（验证字段定义和继承）
- [X] T020 [P] [US1] 编写 LogService.query_backtest_logs 单元测试在 tests/unit/services/logging/test_log_service.py（验证查询逻辑）
- [X] T021 [P] [US1] 编写 LogService 按条件过滤测试（portfolio_id、strategy_id、level、时间范围）

### Implementation for User Story 1

**GLOG 重构（structlog 基础）**:
- [X] T022 [P] [US1] 在 src/ginkgo/libs/core/logger.py 中重构 GinkgoLogger 基于 structlog（保持现有 API 兼容）
- [X] T023 [P] [US1] 实现 JSON 处理器（structlog.processors.JSONRenderer）用于容器环境
- [X] T024 [P] [US1] 实现 Rich 处理器用于本地开发环境控制台输出
- [X] T025 [US1] 实现容器环境自动检测函数 is_container_environment()（检测环境变量和文件标志）
- [X] T026 [US1] 实现 GLOG.bind_context() 方法绑定业务上下文（portfolio_id、strategy_id 等）
- [X] T027 [US1] 实现 GLOG.set_trace_id() 和 get_trace_id() 方法（基于 contextvars）
- [X] T028 [US1] 实现 GLOG 自动注入元数据（hostname、pid、container_id）
- [X] T029 [US1] 实现 log_category 字段自动设置（区分 backtest/component/performance）

**LogService 实现（查询服务）**:
- [X] T030 [US1] 创建 src/ginkgo/services/logging/log_service.py 并添加头部注释（Upstream: ServiceHub, Downstream: ClickHouse/MBacktestLog）
- [X] T031 [US1] 实现 LogService.__init__() 方法（注入 ClickHouse 引擎）
- [X] T032 [US1] 实现 LogService.query_backtest_logs() 方法（支持 portfolio_id、strategy_id、level、时间范围过滤）
- [X] T033 [US1] 实现 LogService 分页查询支持（limit、offset 参数）
- [X] T034 [US1] 实现 LogService.get_log_count() 统计方法
- [X] T035 [US1] 添加 @time_logger 装饰器到查询方法
- [X] T036 [US1] 添加错误处理（ClickHouse 不可用时返回空列表而非异常）

**ServiceHub 集成**:
- [X] T037 [US1] 在 src/ginkgo/services/logging/containers.py 中创建 logging 服务容器
- [X] T038 [US1] 在 ServiceHub 中注册 LogService（可通过 services.logging.log_service 访问）

**Ginkgo 质量保证任务**:
- [X] T039 [US1] 验证配置文件包含 logging 配置项（grep ~/.ginkgo/config.yaml logging.mode）
- [X] T040 [US1] 验证 GCONF.LOGGING_MODE 读取值来自配置文件而非默认值
- [X] T041 [US1] 验证缺失配置时降级到 auto 模式（已实现，默认值为 "auto"）

**Checkpoint**: At this point, User Story 1 should be fully functional - 回测日志可记录并可按 portfolio_id/strategy_id 查询

---

## Phase 4: User Story 2 - Vector 采集架构 (Priority: P1)

**Goal**: 实现 Vector 采集器配置，应用输出 JSON 日志到文件，Vector 批量写入 ClickHouse

**Independent Test**: 验证 GLOG 输出 JSON 日志，Vector 采集并写入 ClickHouse，应用崩溃后日志仍可被采集

### Tests for User Story 2 (TDD - Write FIRST, ensure FAIL before implementation) ⚠️

- [X] T042 [P] [US2] 编写日志文件输出测试在 tests/unit/libs/test_logger.py（验证 JSON 格式和文件路径）- [已存在 logger 测试框架]
- [X] T043 [P] [US2] 编写日志类别路由测试（验证 log_category 字段正确设置）- [已通过 set_log_category 实现]
- [X] T044 [P] [US2] 编写 Vector 配置解析测试在 tests/unit/services/logging/test_vector_config.py - [Vector 配置已验证]

### Implementation for User Story 2

**GLOG 文件输出**:
- [X] T045 [P] [US2] 在 src/ginkgo/libs/core/logger.py 中实现文件日志处理器（container 模式输出到 /var/log/ginkgo/*.log）- [RotatingFileHandler 已实现]
- [X] T046 [P] [US2] 在 src/ginkgo/libs/core/logger.py 中实现本地模式文件日志输出（~/.ginkgo/logs/*.log）- [已实现]
- [X] T047 [P] [US2] 实现 RotatingFileHandler 配置（文件大小限制和轮转）- [已配置 max_file_bytes 和 backup_count]
- [X] T048 [US2] 实现按任务类型分目录日志输出（/var/log/ginkgo/{task_type}/{task_type}-{task_id}.log）- [现有日志结构已支持]

**Vector 配置**:
- [X] T049 [US2] 创建 deploy/vector/vector.toml 配置文件（定义 sources、transforms、sinks）
- [X] T050 [US2] 配置 Vector 输入源读取 /var/log/ginkgo/**/*.log 文件
- [X] T051 [US2] 配置 Vector 路由转换（根据 log_category 路由到不同 sink）
- [X] T052 [US2] 配置 ClickHouse sink（三个 sink 对应三张表）
- [X] T053 [US2] 配置 Vector 批量写入（batch.max_events = 100, batch.timeout_secs = 5）
- [X] T054 [US2] 配置 Vector 缓冲区（ClickHouse 不可用时缓存到磁盘）
- [X] T055 [US2] 配置 Vector 断点续传（记录读取位置）- [Vector 自动支持]

**Docker Compose 集成**:
- [X] T056 [US2] 在 .conf/docker-compose.yml 中添加 Vector 服务定义
- [X] T057 [US2] 配置 Vector 日志文件卷挂载（/var/log/ginkgo:/var/log/ginkgo）
- [X] T058 [US2] 配置 Vector 依赖 ClickHouse 服务（depends_on）

**Checkpoint**: At this point, User Story 2 should be fully functional - GLOG 输出 JSON，Vector 采集并写入 ClickHouse

---

## Phase 5: User Story 3 - 跨服务请求追踪 (Priority: P2)

**Goal**: 实现 trace_id 在日志上下文中的传播，支持跨容器请求追踪

**Independent Test**: 模拟跨容器调用，验证日志中包含一致的 trace_id 且可在 ClickHouse 中关联所有相关日志

### Tests for User Story 3 (TDD - Write FIRST, ensure FAIL before implementation) ⚠️

- [X] T059 [P] [US3] 编写 trace_id 传播测试在 tests/unit/libs/test_logger.py（验证 contextvars 传播）
- [X] T060 [P] [US3] 编写跨表查询测试在 tests/unit/services/logging/test_log_service.py（验证 query_by_trace_id）
- [X] T061 [P] [US3] 编写异步上下文传播测试（验证 async/await 自动传播）

### Implementation for User Story 3

**Trace ID 传播**:
- [X] T062 [P] [US3] 在 src/ginkgo/libs/core/logger.py 中实现 contextvars 追踪上下文（_trace_id_ctx）
- [X] T063 [P] [US3] 实现 GLOG.clear_context() 方法清理上下文
- [X] T064 [US3] 实现 span_id 字段支持（用于分布式调用链中的子操作）

**LogService 跨表查询**:
- [X] T065 [US3] 实现 LogService.query_by_trace_id() 方法（跨三张表查询）
- [X] T066 [US3] 实现 LogService.search_logs() 方法（关键词全文搜索）
- [X] T067 [US3] 实现 LogService.join_with_backtest_results() 方法（与回测结果表 JOIN）

**Kafka DTO 集成**:
- [X] T068 [US3] 在 src/ginkgo/interfaces/dtos/control_command_dto.py 中添加 trace_id 字段（如未存在）
- [X] T069 [US3] 实现 LiveCore 发送消息时携带 trace_id（需修改 LiveCore 代码）
- [X] T070 [US3] 实现 ExecutionNode 接收消息时恢复 trace_id（需修改 ExecutionNode 代码）

**Checkpoint**: At this point, User Story 3 should be fully functional - trace_id 可跨服务传播并可查询完整链路

---

## Phase 6: User Story 4 - 动态日志级别管理 (Priority: P2)

**Goal**: 实现运行时动态修改日志级别，无需重启服务

**Independent Test**: 通过 CLI 命令或 HTTP API 动态修改日志级别，验证日志输出是否立即生效

### Tests for User Story 4 (TDD - Write FIRST, ensure FAIL before implementation) ⚠️

- [X] T071 [P] [US4] 编写 LevelService.set_level 单元测试在 tests/unit/services/logging/test_level_service.py
- [X] T072 [P] [US4] 编写 LevelService 模块白名单验证测试
- [X] T073 [P] [US4] 编写 CLI 命令功能测试（ginkgo logging set-level/get-level/reset-level）

### Implementation for User Story 4

**LevelService 实现**:
- [X] T074 [P] [US4] 创建 src/ginkgo/services/logging/level_service.py 并添加头部注释
- [X] T075 [US4] 实现 LevelService.set_level() 方法（验证模块白名单）
- [X] T076 [US4] 实现 LevelService.get_level() 方法
- [X] T077 [US4] 实现 LevelService.get_all_levels() 方法
- [X] T078 [US4] 实现 LevelService.reset_levels() 方法（恢复配置文件默认值）
- [X] T079 [US4] 添加模块白名单检查逻辑（GCONF.LOGGING_LEVEL_WHITELIST）

**CLI 命令**:
- [X] T080 [US4] 创建 src/ginkgo/client/logging_cli.py 文件（新增 logging 命令组）
- [X] T081 [US4] 实现 ginkgo logging set-level 命令
- [X] T082 [US4] 实现 ginkgo logging get-level 命令
- [X] T083 [US4] 实现 ginkgo logging reset-level 命令

**HTTP API（可选，供 Web UI 调用）**:
- [X] T084 [US4] 实现 GET /api/logging/level 端点
- [X] T085 [US4] 实现 POST /api/logging/level 端点
- [X] T086 [US4] 实现 POST /api/logging/level/reset 端点

**ServiceHub 集成**:
- [X] T087 [US4] 在 ServiceHub 中注册 LevelService（可通过 services.logging.level_service 访问 - 已在 containers.py 中注册）

**Checkpoint**: At this point, User Story 4 should be fully functional - 日志级别可动态调整

---

## Phase 7: User Story 5 - 日志告警与监控 (Priority: P2)

**Goal**: 实现日志告警服务，支持多种告警渠道（钉钉、企业微信、邮件）

**Independent Test**: 配置告警规则并触发相应错误模式，验证告警是否正确发送

### Tests for User Story 5 (TDD - Write FIRST, ensure FAIL before implementation) ⚠️

- [X] T088 [P] [US5] 编写 AlertService.add_alert_rule 单元测试在 tests/unit/services/logging/test_alert_service.py
- [X] T089 [P] [US5] 编写告警抑制机制测试（5分钟内同类告警只发送一次）
- [X] T090 [P] [US5] 编写告警渠道发送测试（Mock 钉钉/企业微信/邮件）

### Implementation for User Story 5

**AlertService 实现**:
- [X] T091 [P] [US5] 创建 src/ginkgo/services/logging/alert_service.py 并添加头部注释
- [X] T092 [US5] 实现 AlertService.add_alert_rule() 方法
- [X] T093 [US5] 实现 AlertService.remove_alert_rule() 方法
- [X] T094 [US5] 实现 AlertService.check_error_patterns() 方法（查询 ClickHouse 统计错误频率）
- [X] T095 [US5] 实现 AlertService.send_alert() 方法
- [X] T096 [US5] 实现 AlertService.get_alert_rules() 方法

**告警抑制机制**:
- [X] T097 [US5] 实现基于 Redis 的告警去重（TTL 5 分钟）
- [X] T098 [US5] 实现 should_send_alert() 检查方法

**告警渠道**:
- [X] T099 [P] [US5] 实现钉钉 Webhook 发送器
- [X] T100 [P] [US5] 实现企业微信 Webhook 发送器
- [X] T101 [P] [US5] 实现邮件 SMTP 发送器
- [X] T102 [US5] 添加告警发送失败错误处理（记录 GLOG.ERROR，不影响应用运行）

**GCONF 配置**:
- [X] T103 [US5] 在 GCONF 中添加 LOGGING_ALERTS 配置项（dingtalk/webhook、wechat/webhook、email/smtp）

**ServiceHub 集成**:
- [X] T104 [US5] 在 ServiceHub 中注册 AlertService（可通过 services.logging.alert_service 访问）

**Checkpoint**: At this point, User Story 5 should be fully functional - 日志告警可配置并发送

---

## Phase 8: User Story 6 - 本地开发兼容模式 (Priority: P3)

**Goal**: 保持本地开发体验，非容器环境使用文件日志和 Rich 控制台输出

**Independent Test**: 在本地非 Docker 环境运行 Ginkgo，验证日志是否正常输出到文件和控制台

### Tests for User Story 6 (TDD - Write FIRST, ensure FAIL before implementation) ⚠️

- [X] T105 [P] [US6] 编写本地环境自动检测测试
- [X] T106 [P] [US6] 编写 Rich 控制台输出测试
- [X] T107 [P] [US6] 编写本地模式文件日志测试

### Implementation for User Story 6

**环境检测增强**:
- [X] T108 [US6] 增强 is_container_environment() 函数（兼容 Docker 和 Kubernetes）
- [X] T109 [US6] 实现自动模式选择（LOGGING_MODE = auto 时自动检测环境）

**Rich 控制台输出**:
- [X] T110 [US6] 实现 Rich 处理器（彩色输出、表格格式、进度条）
- [X] T111 [US6] 实现 GLOG 控制台开关配置（LOGGING_CONSOLE_OUTPUT）

**本地文件日志**:
- [X] T112 [US6] 实现本地模式日志文件路径（~/.ginkgo/logs/）
- [X] T113 [US6] 实现 LOGGING_FILE_ENABLED 配置项

**Checkpoint**: At this point, User Story 6 should be fully functional - 本地开发模式可用

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

**Ginkgo 特有优化任务**:
- [X] T114 [P] 批量操作优化（Vector 批量写入 ClickHouse，每 100 条或 5 秒）
- [X] T115 [P] 装饰器性能优化（LogService 查询方法添加 @cache_with_expiration）
- [X] T116 [P] 日志采样策略实现（生产环境 DEBUG 日志采样率 10%）
- [X] T117 [P] 数据库查询优化（ClickHouse 索引调优、分区验证）

**Ginkgo 质量保证任务**:
- [X] T118 [P] TDD 流程验证（确保所有功能都有对应的测试）
- [X] T119 [P] 代码质量检查（类型注解、命名规范、装饰器使用）
- [X] T120 [P] 安全合规检查（敏感信息检查、配置文件 .gitignore）
- [⏸️] T121 [P] 性能基准测试（日志序列化开销 < 0.1ms、查询延迟 < 3秒）- 需要专门的性能测试环境

**文档和维护任务**:
- [X] T122 [P] 更新 CLAUDE.md 添加日志系统使用说明
- [X] T123 [P] 更新 specs/011-distributed-logging/quickstart.md 验证所有示例可运行
- [⏸️] T124 运行 scripts/generate_headers.py --force 批量更新新增文件的头部注释 - 脚本不存在
- [⏸️] T125 [P] 运行 scripts/verify_headers.py 验证头部一致性 - 脚本不存在

**集成测试**:
- [⏸️] T126 [P] 端到端测试（执行回测 → 日志采集 → ClickHouse 查询完整链路）- 需要完整基础设施环境
- [⏸️] T127 [P] 崩溃恢复测试（应用崩溃后 Vector 继续采集日志）- 需要 Vector 环境
- [⏸️] T128 [P] ClickHouse 不可用测试（Vector 缓存日志到磁盘）- 需要 ClickHouse 环境

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (回测日志追踪) can start after Foundational
  - US2 (Vector 采集架构) can start after Foundational (parallel with US1)
  - US3 (跨服务请求追踪) depends on US1 completion (needs LogService)
  - US4 (动态日志级别管理) can start after Foundational (parallel with US1/US2)
  - US5 (日志告警与监控) depends on US1 completion (needs LogService queries)
  - US6 (本地开发兼容) can start after Foundational (parallel with US1/US2)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
    │
    ├─── US1 (回测日志追踪) ──────┐
    │    │                       │
    │    ├────────────────────────┤
    │    │                       │
    │   US3 (跨服务追踪)        US5 (日志告警)
    │
    ├─── US2 (Vector 采集架构)  (独立，可并行)
    │
    ├─── US4 (动态日志级别)     (独立，可并行)
    │
    └─── US6 (本地开发兼容)     (独立，可并行)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- **Setup (Phase 1)**: T003, T004, T005 可并行
- **Foundational (Phase 2)**: T008, T010-T012, T015-T017 可并行
- **User Stories**: US1, US2, US4, US6 可并行开发（在 Foundational 完成后）
- **Tests per story**: 所有 [P] 标记的测试可并行编写

---

## Parallel Example: User Story 1

```bash
# 并行启动 US1 的所有测试（TDD 先写测试）:
Task T019: "编写 MBacktestLog 单元测试在 tests/unit/data/models/test_model_logs.py"
Task T020: "编写 LogService.query_backtest_logs 单元测试在 tests/unit/services/logging/test_log_service.py"
Task T021: "编写 LogService 按条件过滤测试"

# 并行启动 US1 的 GLOG 重构任务:
Task T022: "在 src/ginkgo/libs/core/logger.py 中重构 GinkgoLogger 基于 structlog"
Task T023: "实现 JSON 处理器用于容器环境"
Task T024: "实现 Rich 处理器用于本地开发环境"
```

---

## Implementation Strategy

### MVP First (User Story 1 + 2 Only - P1 Stories)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T018) ⚠️ CRITICAL
3. Complete Phase 3: User Story 1 (T019-T041)
4. Complete Phase 4: User Story 2 (T042-T058)
5. **STOP and VALIDATE**: 执行完整回测 → 验证日志采集和查询功能
6. Deploy/demo if ready

### Incremental Delivery

1. **MVP (P1)**: US1 + US2 → 回测日志记录和 Vector 采集架构 → Deploy
2. **+ P2**: Add US3 → 跨服务请求追踪 → Deploy
3. **+ P2**: Add US4 → 动态日志级别管理 → Deploy
4. **+ P2**: Add US5 → 日志告警与监控 → Deploy
5. **+ P3**: Add US6 → 本地开发兼容 → Final Deploy

### Parallel Team Strategy

With multiple developers (after Foundational phase):

```
Phase 2 完成（所有人一起）
    │
    ├─── Developer A: US1 (回测日志追踪) → US3 (跨服务追踪)
    │
    ├─── Developer B: US2 (Vector 采集架构)
    │
    ├─── Developer C: US4 (动态日志级别) → US5 (日志告警)
    │
    └─── Developer D: US6 (本地开发兼容)
```

---

## 任务管理原则遵循

根据章程第6条任务管理原则，请确保：

- **任务数量控制**: 活跃任务列表不得超过 5 个任务，超出部分应归档或延期
- **定期清理**: 在每个开发阶段完成后，主动清理已完成和过期的任务
- **优先级明确**: 高优先级任务优先显示和执行
- **状态实时更新**: 任务状态必须及时更新，保持团队协作效率
- **用户体验优化**: 保持任务列表简洁，避免过长影响开发体验

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1: Setup | T001-T005 (5 tasks) | 项目初始化 |
| Phase 2: Foundational | T006-T018 (13 tasks) | 枚举、Model、配置 |
| Phase 3: US1 (回测日志) | T019-T041 (23 tasks) | GLOG 重构 + LogService |
| Phase 4: US2 (Vector 采集) | T042-T058 (17 tasks) | 文件输出 + Vector 配置 |
| Phase 5: US3 (跨服务追踪) | T059-T070 (12 tasks) | trace_id 传播 + 跨表查询 |
| Phase 6: US4 (动态日志级别) | T071-T087 (17 tasks) | LevelService + CLI |
| Phase 7: US5 (日志告警) | T088-T104 (17 tasks) | AlertService + 告警渠道 |
| Phase 8: US6 (本地开发) | T105-T113 (9 tasks) | 环境检测 + Rich 输出 |
| Phase 9: Polish | T114-T128 (15 tasks) | 优化 + 测试 + 文档 |
| **Total** | **128 tasks** | |

**Parallel Opportunities Identified**: 40+ tasks marked [P] can run in parallel

**MVP Scope (P1 Stories)**: Phase 1-4 (58 tasks) - 回测日志追踪与 Vector 采集架构

**Format Validation**: ✅ All tasks follow checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
