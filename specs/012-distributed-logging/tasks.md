# Tasks: 容器化分布式日志系统 (Loki Only)

**Input**: Design documents from `/specs/012-distributed-logging/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/log-api-contract.md

**Tests**: TDD流程明确要求 (FR-LOG-015)，所有新功能先写测试再实现

**Organization**: 任务按用户故事分组，每个故事可独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事 (US1, US2, US3, US4)
- 包含精确文件路径

---

## Phase 1: Setup (项目初始化)

**Purpose**: 依赖安装和项目结构准备

- [ ] T001 添加 structlog>=24.0.0 到项目依赖 (pyproject.toml 或 setup.py)
- [ ] T002 创建 services/logging 目录结构: src/ginkgo/services/logging/{__init__.py,log_service.py,clients/loki_client.py}

---

## Phase 2: Foundational (核心基础设施)

**Purpose**: 所有用户故事依赖的核心组件，必须先完成

**⚠️ CRITICAL**: 任何用户故事工作开始前此阶段必须完成

### 日志工具函数（所有用户故事依赖）

- [ ] T003 [P] 创建容器检测函数 is_container_environment() 在 src/ginkgo/libs/utils/log_utils.py
  - 检测环境变量 (DOCKER_CONTAINER, KUBERNETES_SERVICE_HOST)
  - 检测 /proc/1/cgroup 文件
  - 检测 /.dockerenv 文件
- [ ] T004 [P] 创建容器元数据采集函数 get_container_metadata() 在 src/ginkgo/libs/utils/log_utils.py
  - 采集 container.id
  - 采集 kubernetes.pod.name, kubernetes.namespace
  - 采集 host.hostname, process.pid

### 日志配置扩展

- [ ] T005 扩展 GCONF 配置项在 src/ginkgo/config/logging_config.py
  - LOGGING_MODE (auto/container/local)
  - LOGGING_FORMAT (json/plain)
  - LOGGING_LEVEL_CONSOLE, LOGGING_LEVEL_FILE
  - LOGGING_CONTAINER_ENABLED, LOGGING_CONTAINER_JSON_OUTPUT
  - LOGGING_LOCAL_FILE_ENABLED, LOGGING_LOCAL_FILE_PATH
  - LOGGING_MASK_FIELDS

### 日志核心枚举类型

- [ ] T006 [P] 创建 LogMode 枚举在 src/ginkgo/libs/core/logger.py (container/local/auto)
- [ ] T007 [P] 创建 LogCategory 枚举在 src/ginkgo/libs/core/logger.py (system/backtest)
- [ ] T008 [P] 创建 LogLevel 枚举在 src/ginkgo/libs/core/logger.py (debug/info/warning/error/critical)

### structlog 配置和处理器

- [ ] T009 [P] 创建 ECS 字段映射处理器 ecs_processor() 在 src/ginkgo/libs/core/logger.py
  - 映射 @timestamp, log.level, log.logger, message
  - 映射 process.pid, host.hostname
- [ ] T010 [P] 创建 ginkgo 业务字段处理器 ginkgo_processor() 在 src/ginkgo/libs/core/logger.py
  - 添加 ginkgo.log_category
  - 添加 ginkgo.strategy_id, ginkgo.portfolio_id
- [ ] T011 [P] 创建容器元数据处理器 container_metadata_processor() 在 src/ginkgo/libs/core/logger.py
  - 注入 container.id, kubernetes.* 字段
- [ ] T012 [P] 创建敏感数据脱敏处理器 masking_processor() 在 src/ginkgo/libs/core/logger.py
  - 根据 GCONF.LOGGING_MASK_FIELDS 配置脱敏
- [ ] T013 配置 structlog 在 src/ginkgo/libs/core/logger.py
  - 设置 processors 链（contextvars, stdlib, ECS, ginkgo, container, masking, JSONRenderer）
  - 配置 wrapper_class=structlog.stdlib.BoundLogger
  - 配置 context_class=dict

**Checkpoint**: 基础设施就绪 - 用户故事实现现在可以并行开始

---

## Phase 3: User Story 1 - 容器环境日志聚合 (Priority: P1) 🎯 MVP

**Goal**: 容器环境下GLOG输出JSON格式日志到stdout/stderr，由Promtail采集到Loki

**Independent Test**: 在容器环境中运行Ginkgo，验证日志以JSON格式输出到stdout/stderr，可在Grafana中查询

### Tests for User Story 1 (TDD - 先写测试) ⚠️

> **NOTE: 先写这些测试，确保它们 FAIL 后再实现功能**

- [ ] T014 [P] [US1] 创建 GinkgoLogger 单元测试框架在 tests/unit/libs/test_core_logger.py
  - 测试 DEBUG/INFO/WARN/ERROR/CRITICAL 方法输出 JSON 格式
  - 测试包含 ECS 标准字段 (@timestamp, log.level, log.logger, message)
  - 使用 pytest.mark.tdd 标记
- [ ] T015 [P] [US1] 测试容器环境检测在 tests/unit/libs/test_log_utils.py
  - 测试 is_container_environment() 各种场景
  - Mock 环境变量和文件系统
  - 使用 pytest.mark.tdd 标记
- [ ] T016 [P] [US1] 测试容器元数据采集在 tests/unit/libs/test_log_utils.py
  - 测试 get_container_metadata() 返回正确字段
  - 使用 pytest.mark.tdd 标记

### Implementation for User Story 1

**GinkgoLogger 核心重写**:
- [ ] T017 [US1] 重写 GinkgoLogger.DEBUG/INFO/WARN/ERROR/CRITICAL 方法在 src/ginkgo/libs/core/logger.py
  - 保持现有 API 签名完全兼容
  - 内部调用 structlog 底层
  - 使用 contextvars 绑定的上下文
- [ ] T018 [US1] 实现 JSON 输出处理器在 src/ginkgo/libs/core/logger.py
  - 容器模式: structlog.processors.JSONRenderer()
  - 本地模式: Rich 控制台格式

**Ginkgo 级别控制**:
- [ ] T019 [US1] 实现 set_level() 方法在 src/ginkgo/libs/core/logger.py (保持兼容)
- [ ] T020 [US1] 实现 set_console_level() 方法在 src/ginkgo/libs/core/logger.py (保持兼容)
- [ ] T021 [US1] 实现 get_current_levels() 方法在 src/ginkgo/libs/core/logger.py (保持兼容)

**Ginkgo 错误统计迁移**:
- [ ] T022 [US1] 迁移 _should_log_error() 智能限流逻辑到 src/ginkgo/libs/core/logger.py
  - 保持现有错误流量控制功能 (FR-LOG-009)
  - 集成到 structlog processor

**Ginkgo 质量保证**:
- [ ] T023 [US1] 添加三行头部注释 (Upstream/Downstream/Role) 到 src/ginkgo/libs/core/logger.py
- [ ] T024 [US1] 添加类型注解到所有 GinkgoLogger 公共方法

**Checkpoint**: User Story 1 完成 - 容器环境日志聚合功能可用

---

## Phase 4: User Story 2 - 跨容器请求追踪 (Priority: P2)

**Goal**: 通过 trace_id 追踪跨服务请求链路，支持分布式问题排查

**Independent Test**: 模拟跨容器调用，验证日志中包含一致的 trace_id，可在 Loki 中关联所有相关日志

### Tests for User Story 2 (TDD - 先写测试) ⚠️

- [ ] T025 [P] [US2] 测试 trace_id 上下文管理在 tests/unit/libs/test_core_logger.py
  - 测试 set_trace_id() 返回 Token
  - 测试 get_trace_id() 获取当前值
  - 测试 clear_trace_id() 恢复上下文
  - 使用 pytest.mark.tdd 标记
- [ ] T026 [P] [US2] 测试 with_trace_id 上下文管理器在 tests/unit/libs/test_core_logger.py
  - 测试退出后 trace_id 自动清除
  - 使用 pytest.mark.tdd 标记
- [ ] T027 [P] [US2] 测试多线程 trace_id 隔离在 tests/unit/libs/test_core_logger.py
  - 测试 contextvars 线程隔离特性
  - 使用 pytest.mark.tdd 标记
- [ ] T028 [P] [US2] 测试异步上下文传播在 tests/unit/libs/test_core_logger.py
  - 测试 async/await 场景下 trace_id 自动传播
  - 使用 pytest.mark.tdd 标记

### Implementation for User Story 2

**Ginkgo 追踪上下文管理**:
- [ ] T029 [US2] 实现 contextvars.ContextVar _trace_id_ctx 在 src/ginkgo/libs/core/logger.py
  - 默认值 None
  - 线程隔离
- [ ] T030 [US2] 实现 set_trace_id() 方法在 src/ginkgo/libs/core/logger.py
  - 返回 contextvars.Token 用于恢复
  - 自动注入到日志 event dict 的 trace.id 字段
- [ ] T031 [US2] 实现 get_trace_id() 方法在 src/ginkgo/libs/core/logger.py
- [ ] T032 [US2] 实现 clear_trace_id() 方法在 src/ginkgo/libs/core/logger.py
  - 使用 Token 恢复之前的值
- [ ] T033 [US2] 实现 with_trace_id() 上下文管理器在 src/ginkgo/libs/core/logger.py
  - 使用 @contextlib.contextmanager
  - 自动清理 trace_id

**Ginkgo 质量保证**:
- [ ] T034 [US2] 添加类型注解到所有 trace_id 相关方法

**Checkpoint**: User Story 2 完成 - trace_id 追踪功能可用

---

## Phase 5: User Story 3 - 本地开发兼容模式 (Priority: P3)

**Goal**: 非容器环境保持本地文件日志和 Rich 控制台输出，保持现有开发体验

**Independent Test**: 在本地非Docker环境运行Ginkgo，验证日志输出到文件和控制台

### Tests for User Story 3 (TDD - 先写测试) ⚠️

- [ ] T035 [P] [US3] 测试本地模式文件日志在 tests/unit/libs/test_core_logger.py
  - 测试日志写入本地文件
  - 测试 Rich 控制台格式输出
  - 使用 pytest.mark.tdd 标记
- [ ] T036 [P] [US3] 测试自动环境检测在 tests/unit/libs/test_log_utils.py
  - 测试 mode=auto 时正确选择模式
  - 使用 pytest.mark.tdd 标记

### Implementation for User Story 3

**Ginkgo 本地模式输出**:
- [ ] T037 [US3] 实现本地模式文件输出处理器在 src/ginkgo/libs/core/logger.py
  - 使用 RichHandler 控制台输出
  - 使用 RotatingFileHandler 文件输出
- [ ] T038 [US3] 实现模式自动检测逻辑在 src/ginkgo/libs/core/logger.py
  - mode=auto 时调用 is_container_environment()
  - 自动切换容器/本地模式

**Ginkgo 质量保证**:
- [ ] T039 [US3] 验证向后兼容性 - 所有现有 GLOG 调用无需修改

**Checkpoint**: User Story 3 完成 - 本地开发模式兼容

---

## Phase 6: User Story 4 - 业务日志查询 (Priority: P2)

**Goal**: Service层提供LogService封装Loki查询API，供Web UI调用查询业务日志

**Independent Test**: 通过Service层LogService调用Loki API，验证能正确查询特定portfolio_id的日志

### Tests for User Story 4 (TDD - 先写测试) ⚠️

- [ ] T040 [P] [US4] 创建 LokiClient 单元测试在 tests/unit/services/logging/test_loki_client.py
  - 测试 query() 方法构建正确 HTTP 请求
  - Mock requests.get 返回
  - 测试响应解析
  - 使用 pytest.mark.tdd 标记
- [ ] T041 [P] [US4] 创建 LogService 单元测试在 tests/unit/services/logging/test_log_service.py
  - 测试 query_logs() 多条件过滤
  - 测试 query_by_portfolio()
  - 测试 query_by_trace_id()
  - 测试 query_errors()
  - 测试 Loki 不可用时的优雅降级
  - 使用 pytest.mark.tdd 标记

### Implementation for User Story 4

**Loki HTTP 客户端**:
- [ ] T042 [US4] 创建 LokiClient 类在 src/ginkgo/services/logging/clients/loki_client.py
  - __init__(base_url: str)
  - query(logql: str, limit: int = 100) -> List[Dict]
  - _parse_response(response) -> List[Dict]
  - 使用 requests 库调用 Loki HTTP API
- [ ] T043 [US4] 实现 LogQL 查询字符串构建在 src/ginkgo/services/logging/clients/loki_client.py
  - 支持标签过滤: {key="value"}
  - 支持内容搜索: |= "pattern"
  - 支持时间范围: [1h]

**LogService 封装**:
- [ ] T044 [US4] 创建 LogService 类在 src/ginkgo/services/logging/log_service.py
  - __init__(loki_client: LokiClient)
  - query_logs(portfolio_id, strategy_id, trace_id, level, start_time, end_time, limit, offset) -> List[Dict]
  - _build_logql(**filters) -> str: 构建 LogQL 查询
- [ ] T045 [US4] 实现 query_by_portfolio() 在 src/ginkgo/services/logging/log_service.py
- [ ] T046 [US4] 实现 query_by_trace_id() 在 src/ginkgo/services/logging/log_service.py
- [ ] T047 [US4] 实现 query_errors() 在 src/ginkgo/services/logging/log_service.py
- [ ] T048 [US4] 实现 get_log_count() 在 src/ginkgo/services/logging/log_service.py
- [ ] T049 [US4] 实现 Loki 不可用时的错误处理在 src/ginkgo/services/logging/log_service.py
  - 捕获 requests.exceptions.RequestException
  - 返回友好错误或空列表

**ServiceHub 注册**:
- [ ] T050 [US4] 注册 log_service 到 ServiceHub 在 src/ginkgo/services/logging/__init__.py
  - services.logging.log_service() 访问入口

**Ginkgo 质量保证**:
- [ ] T051 [US4] 添加三行头部注释到 services/logging/ 所有文件
- [ ] T052 [US4] 添加类型注解到所有 LogService 和 LokiClient 方法
- [ ] T053 [US4] 使用 Pydantic 验证 Loki 响应模型

**Checkpoint**: User Story 4 完成 - 业务日志查询功能可用

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的优化和质量保证

**Ginkgo 性能优化任务**:
- [ ] T054 [P] 日志序列化性能测试 (验证 < 0.1ms 目标)
- [ ] T055 [P] structlog 配置优化 (processors 顺序调优)

**Ginkgo 质量保证任务**:
- [ ] T056 [P] TDD 流程验证 (确保所有功能都有测试，覆盖率 > 85%)
- [ ] T057 [P] 代码质量检查 (类型注解、命名规范、装饰器使用)
- [ ] T058 [P] API 兼容性测试 (现有 GLOG 调用无需修改)
- [ ] T059 [P] 多线程安全测试 (contextvars 隔离验证)
- [ ] T060 [P] 异步兼容测试 (async/await 场景)

**文档和维护任务**:
- [ ] T061 [P] 更新 quickstart.md 验证 (确保所有示例可运行)
- [ ] T062 [P] API 文档更新 (包含 LogService 使用示例)
- [ ] T063 [P] 架构文档更新 (数据流图更新)
- [ ] T064 Code cleanup and refactoring
- [ ] T065 运行完整测试套件并确保覆盖率 > 85%

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - 阻塞所有用户故事
- **User Stories (Phase 3-6)**: 依赖 Foundational 完成
  - US1, US2, US3, US4 可以并行开发（如果有人力）
  - 或按优先级顺序开发 (P1 → P2 → P2 → P3)
- **Polish (Phase 7)**: 依赖所有用户故事完成

### User Story Dependencies

- **User Story 1 (P1)**: Foundational 完成后即可开始 - 无其他故事依赖
- **User Story 2 (P2)**: Foundational 完成后即可开始 - 独立于其他故事
- **User Story 3 (P3)**: Foundational 完成后即可开始 - 独立于其他故事
- **User Story 4 (P2)**: Foundational 完成后即可开始 - 独立于其他故事

### Within Each User Story

- 测试必须先写并 FAIL，然后实现功能
- 测试任务标记 [P] 可以并行运行
- 实现任务按序执行

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- T001, T002 可并行

**Foundational Phase (Phase 2)**:
- T003, T004, T006, T007, T008, T009, T010, T011, T012 可并行
- T005 依赖 T006-T008 枚举定义
- T013 依赖所有 processor 完成

**User Story 1 Tests**:
- T014, T015, T016 可并行

**User Story 2 Tests**:
- T025, T026, T027, T028 可并行

**User Story 3 Tests**:
- T035, T036 可并行

**User Story 4 Tests**:
- T040, T041 可并行

**User Story 4 Implementation**:
- T042, T043 (LokiClient) 和 T044-T049 (LogService) 有依赖关系

**Polish Phase**:
- 所有任务标记 [P] 可并行

---

## Parallel Example: User Story 1 Tests

```bash
# 并行启动 User Story 1 所有测试:
Task T014: "创建 GinkgoLogger 单元测试框架在 tests/unit/libs/test_core_logger.py"
Task T015: "测试容器环境检测在 tests/unit/libs/test_log_utils.py"
Task T016: "测试容器元数据采集在 tests/unit/libs/test_log_utils.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational (关键 - 阻塞所有故事)
3. 完成 Phase 3: User Story 1
4. **STOP and VALIDATE**: 独立测试 User Story 1
5. 如果准备就绪，部署/演示

### Incremental Delivery

1. 完成 Setup + Foundational → 基础就绪
2. 添加 User Story 1 → 独立测试 → 部署/演示 (MVP!)
3. 添加 User Story 2 → 独立测试 → 部署/演示
4. 添加 User Story 4 → 独立测试 → 部署/演示
5. 添加 User Story 3 → 独立测试 → 部署/演示
6. 每个故事增加价值而不破坏已有功能

### Parallel Team Strategy

多人协作:

1. 团队共同完成 Setup + Foundational
2. Foundational 完成后:
   - Developer A: User Story 1 (P1)
   - Developer B: User Story 2 (P2)
   - Developer C: User Story 4 (P2)
   - Developer D: User Story 3 (P3)
3. 故事独立完成并集成

---

## 任务管理原则遵循

根据章程第6条任务管理原则:

- **任务数量控制**: 活跃任务列表不超过5个，超出归档或延期
- **定期清理**: 每个开发阶段完成后清理已完成和过期任务
- **优先级明确**: P1 → P2 → P3 顺序执行
- **状态实时更新**: 及时更新任务状态
- **用户体验优化**: 保持任务列表简洁

---

## Summary

**Total Tasks**: 65 tasks
- **Phase 1 (Setup)**: 2 tasks
- **Phase 2 (Foundational)**: 11 tasks
- **Phase 3 (US1 - P1)**: 10 tasks (3 tests + 7 implementation)
- **Phase 4 (US2 - P2)**: 10 tasks (4 tests + 6 implementation)
- **Phase 5 (US3 - P3)**: 5 tasks (2 tests + 3 implementation)
- **Phase 6 (US4 - P2)**: 14 tasks (2 tests + 12 implementation)
- **Phase 7 (Polish)**: 12 tasks

**Parallel Opportunities**: 35 tasks marked [P] 可并行执行

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 = 23 tasks (User Story 1 only)

**Independent Test Criteria**:
- US1: 容器环境运行，验证JSON日志输出到stdout/stderr
- US2: 模拟跨容器调用，验证trace_id一致性
- US3: 本地环境运行，验证文件和控制台日志
- US4: 调用LogService API，验证Loki查询正确

**Format Validation**: All tasks follow checklist format (checkbox, ID, labels, file paths) ✅
