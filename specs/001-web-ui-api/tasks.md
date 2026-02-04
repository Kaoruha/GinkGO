# Tasks: Web UI and API Server

**Input**: Design documents from `/specs/001-web-ui-api/`
**Prerequisites**: plan.md (tech stack, structure), spec.md (user stories), research.md (decisions), data-model.md (entities), contracts/api-spec.yaml (endpoints)

**Tests**: 规范中未明确要求测试，遵循TDD原则，每个用户故事包含测试任务

**Organization**: 任务按用户故事分组，支持独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 所属用户故事（US1, US1.5, US2, US2.5, US3, US4, US5）

## Path Conventions

- **API Server**: `apiserver/` (独立项目)
- **Web UI**: `web-ui/` (独立项目，构建由用户手动执行)
- **Ginkgo Core**: `src/ginkgo/` (已存在)

---

## Phase 1: Setup (项目初始化)

**Purpose**: API Server和Web UI项目初始化和基础结构

### API Server项目初始化

- [ ] T001 创建API Server项目目录结构 `apiserver/`
- [ ] T001.1 [P] 创建 `apiserver/main.py` (FastAPI应用入口)
- [ ] T001.2 [P] 创建 `apiserver/api/` 目录（路由模块）
- [ ] T001.3 [P] 创建 `apiserver/models/` 目录（Pydantic DTOs）
- [ ] T001.4 [P] 创建 `apiserver/services/` 目录（业务逻辑层）
- [ ] T001.5 [P] 创建 `apiserver/middleware/` 目录（中间件）
- [ ] T001.6 [P] 创建 `apiserver/core/` 目录（核心配置）
- [ ] T001.7 [P] 创建 `apiserver/websocket/` 目录（WebSocket处理）
- [ ] T002 [P] 初始化API Server Python项目（requirements.txt，依赖FastAPI、uvicorn、Pydantic、kafka-python、websockets）
- [ ] T003 [P] 配置环境变量加载（`apiserver/core/config.py`，从.conf/.env读取）
- [ ] T004 [P] 添加 `.conf/Dockerfile.api-server` （API Server容器配置）
- [ ] T005 [P] 更新 `.conf/docker-compose.yml` （添加api-server服务）

### Web UI项目初始化

- [ ] T006 创建Web UI项目目录结构 `web-ui/` （用户手动执行构建）
- [ ] T006.1 [P] 初始化Vue 3 + Vite项目（`package.json`，依赖Vue 3、Vite、Pinia、TypeScript）
- [ ] T006.2 [P] 配置TailwindCSS（`tailwind.config.js`，原子化CSS配置）
- [ ] T006.3 [P] 集成Ant Design Vue（组件库配置）
- [ ] T006.4 [P] 创建 `web-ui/src/layouts/` 目录（布局组件）
- [ ] T006.5 [P] 创建 `web-ui/src/views/` 目录（页面组件）
- [ ] T006.6 [P] 创建 `web-ui/src/components/` 目录（通用组件）
- [ ] T006.7 [P] 创建 `web-ui/src/composables/` 目录（组合式函数）
- [ ] T006.8 [P] 创建 `web-ui/src/api/` 目录（API封装）
- [ ] T006.9 [P] 创建 `web-ui/src/stores/` 目录（Pinia状态管理）
- [ ] T007 [P] 配置路由（Vue Router，路由定义）

---

## Phase 2: Foundational (阻塞性前置条件)

**Purpose**: 核心基础设施，必须在任何用户故事实现前完成

**⚠️ CRITICAL**: 此阶段完成前，无法开始任何用户故事工作

### 认证授权系统

- [ ] T008 [P] 实现JWT认证中间件（`apiserver/middleware/auth.py`）
- [ ] T009 [P] 实现认证接口（`apiserver/api/auth.py`，POST /api/auth/login）
- [ ] T010 [P] 配置CORS中间件（`apiserver/middleware/cors.py`，允许Web UI跨域）
- [ ] T011 [P] 实现请求限流中间件（`apiserver/middleware/rate_limit.py`）

### 错误处理和日志

- [ ] T012 [P] 实现全局错误处理中间件（`apiserver/middleware/error_handler.py`）
- [ ] T013 [P] 配置日志系统（GLOG集成，Rich格式化）
- [ ] T014 [P] 添加请求日志中间件（审计日志）

### WebSocket基础设施

- [ ] T015 [P] 实现WebSocket连接管理器（`apiserver/websocket/manager.py`）
- [ ] T016 [P] 配置心跳检测机制（30秒心跳）
- [ ] T017 [P] 实现断线重连机制（自动重连逻辑）

### 数据库模型扩展

- [ ] T018 为Portfolios表添加mode字段（BACKTEST/PAPER/LIVE）
- [ ] T019 为Portfolios表添加config_locked字段（boolean）
- [ ] T020 创建strategies表（Portfolio组件关系表）
- [ ] T021 创建api_sessions表（API会话管理）

### Ginkgo核心扩展

- [ ] T022 [P] 扩展MPortfolio模型添加mode和config_locked字段
- [ ] T023 [P] 在ServiceHub中注册API Server相关服务
- [ ] T024 [P] 实现Portfolio模式流转逻辑（Backtest → Paper → Live）

### Docker配置

- [ ] T025 [P] 更新 `.conf/Dockerfile.api-server` （FastAPI容器配置）
- [ ] T026 [P] 更新 `.conf/docker-compose.yml` （添加api-server和web-ui服务）

**Checkpoint**: 基础设施就绪 - 用户故事实现可以并行开始

---

## Phase 3: User Story 1 - 实时监控仪表盘 (Priority: P1) 🎯 MVP

**Goal**: 提供实时监控仪表盘，显示持仓、净值、盈亏、系统状态，支持多Portfolio分屏展示

**Independent Test**: 访问仪表盘页面，验证数据展示准确性和实时刷新

### Tests for User Story 1

- [ ] T027 [P] [US1] 编写仪表盘API契约测试（tests/contract/test_dashboard_api.py）
- [ ] T028 [P] [US1] 编写Portfolio状态集成测试（tests/integration/test_portfolio_state.py）
- [ ] T029 [P] [US1] 编写WebSocket连接测试（tests/integration/test_websocket.py）

### API Server实现

- [ ] T030 [P] [US1] 实现仪表盘统计接口（`apiserver/api/dashboard.py`，GET /api/dashboard/stats）
- [ ] T031 [US1] 实现Portfolio列表接口（`apiserver/api/portfolio.py`，GET /api/portfolio）
- [ ] T032 [US1] 实现Portfolio详情接口（`apiserver/api/portfolio.py`，GET /api/portfolio/{uuid}）
- [ ] T033 [US1] 实现Portfolio查询服务（`apiserver/services/portfolio_service.py`，通过ServiceHub访问）

### WebSocket实现

- [ ] T034 [P] [US1] 实现Portfolio数据推送处理器（`apiserver/websocket/handlers/portfolio_handler.py`）
- [ ] T035 [US1] 实现系统状态推送处理器（`apiserver/websocket/handlers/system_handler.py`）

### 前端实现

- [ ] T036 [P] [US1] 创建DashboardLayout布局组件（`web-ui/src/layouts/DashboardLayout.vue`）
- [ ] T037 [P] [US1] 创建首页视图（`web-ui/src/views/Dashboard/index.vue`）
- [ ] T038 [P] [US1] 实现ArenaRanking竞技场组件（`web-ui/src/components/arena/ArenaRanking.vue`）
- [ ] T039 [P] [US1] 实现SignalStream信号流组件（`web-ui/src/components/arena/SignalStream.vue`）
- [ ] T040 [P] [US1] 实现NewsFeed资讯组件（`web-ui/src/components/arena/NewsFeed.vue`）
- [ ] T041 [P] [US1] 实现MyStats指标组件（`web-ui/src/components/arena/MyStats.vue`）
- [ ] T042 [P] [US1] 实现NetValueChart净值曲线组件（`web-ui/src/components/charts/NetValueChart.vue`）
- [ ] T043 [P] [US1] 实现DataTable基础组件（`web-ui/src/components/base/DataTable.vue`）
- [ ] T044 [P] [US1] 实现Pinia stores（`web-ui/src/stores/portfolio.ts`，`web-ui/src/stores/dashboard.ts`）

### 集成

- [ ] T045 [US1] 前端API封装（`web-ui/src/api/modules/portfolio.ts`，`web-ui/src/api/request.ts`）
- [ ] T046 [US1] WebSocket客户端集成（`web-ui/src/composables/useWebSocket.ts`）
- [ ] T047 [US1] 路由配置（仪表盘路由，分屏路由）

**Checkpoint**: 用户故事1完成 - 仪表盘可独立使用和测试

---

## Phase 4: User Story 1.5 - Paper模拟盘模式 (Priority: P1)

**Goal**: 支持回测完成后启动Paper模式（模拟盘），配置锁死，验证后转为Live模式

**Independent Test**: 完成回测后启动Paper模式，验证配置锁死和模式流转

### Tests for User Story 1.5

- [ ] T048 [P] [US1.5] 编写Paper模式转换API契约测试（tests/contract/test_paper_mode.py）
- [ ] T049 [P] [US1.5] 编写配置锁断验证测试（tests/integration/test_config_locked.py）

### API Server实现

- [ ] T050 [P] [US1.5] 实现回测转Paper接口（`apiserver/api/backtest.py`，POST /api/backtest/{uuid}/paper）
- [ ] T051 [US1.5] 实现Paper转Live接口（`apiserver/api/portfolio.py`，POST /api/portfolio/{uuid}/to_live）
- [ ] T052 [US1.5] 实现配置锁死验证逻辑（`apiserver/services/portfolio_service.py`）

### 前端实现

- [ ] T053 [P] [US1.5] 创建BacktestLayout布局（`web-ui/src/layouts/BacktestLayout.vue`）
- [ ] T054 [P] [US1.5] 实现回测详情页（`web-ui/src/views/Backtest/Detail.vue`）
- [ ] T055 [US1.5] 实现模式流转UI组件（启动Paper、转为Live按钮，配置锁死提示）

**Checkpoint**: 用户故事1.5完成 - Paper模式流转功能可用

---

## Phase 5: User Story 2 - 策略回测管理 (Priority: P1)

**Goal**: 提供回测任务配置、启动、状态查询、结果查看功能

**Independent Test**: 创建回测任务、执行回测、查看结果报告

### Tests for User Story 2

- [ ] T056 [P] [US2] 编写回测API契约测试（tests/contract/test_backtest_api.py）
- [ ] T057 [P] [US2] 编写回测执行集成测试（tests/integration/test_backtest_execution.py）

### API Server实现

- [ ] T058 [P] [US2] 实现回测任务创建接口（`apiserver/api/backtest.py`，POST /api/backtest）
- [ ] T059 [P] [US2] 实现回测任务列表接口（`apiserver/api/backtest.py`，GET /api/backtest）
- [ ] T060 [P] [US2] 实现回测任务状态接口（`apiserver/api/backtest.py`，GET /api/backtest/{uuid}）
- [ ] T061 [P] [US2] 实现回测启动/停止接口（`apiserver/api/backtest.py`，POST /api/backtest/{uuid}/start）
- [ ] T062 [US2] 实现回测结果接口（`apiserver/api/backtest.py`，GET /api/backtest/{uuid}/result）
- [ ] T063 [US2] 实现回测业务服务（`apiserver/services/backtest_service.py`）

### 前端实现

- [ ] T064 [P] [US2] 实现回测配置页（`web-ui/src/views/Backtest/Config.vue`）
- [ ] T065 [P] [US2] 实现回测列表页（`web-ui/src/views/Backtest/List.vue`）
- [ ] T066 [P] [US2] 实现回测结果详情页（`web-ui/src/views/Backtest/Result.vue`）
- [ ] T067 [P] [US2] 实现回测表单组件（策略选择、参数配置）

**Checkpoint**: 用户故事2完成 - 回测管理功能可用

---

## Phase 6: User Story 2.5 - 回测组件管理 (Priority: P1)

**Goal**: 提供组件CRUD操作、在线代码编辑、语法验证功能

**Independent Test**: 创建自定义组件、编辑代码、在回测中使用

### Tests for User Story 2.5

- [ ] T068 [P] [US2.5] 编写组件API契约测试（tests/contract/test_components_api.py）
- [ ] T069 [P] [US2.5] 编写组件语法验证测试（tests/integration/test_component_validation.py）

### API Server实现

- [ ] T070 [P] [US2.5] 实现组件列表接口（`apiserver/api/components.py`，GET /api/components）
- [ ] T071 [P] [US2.5] 实现组件创建接口（`apiserver/api/components.py`，POST /api/components）
- [ ] T072 [P] [US2.5] 实现组件详情接口（`apiserver/api/components.py`，GET /api/components/{uuid}）
- [ ] T073 [P] [US2.5] 实现组件更新接口（`apiserver/api/components.py`，PUT /api/components/{uuid}）
- [ ] T074 [P] [US2.5] 实现组件删除接口（`apiserver/api/components.py`，DELETE /api/components/{uuid}）
- [ ] T075 [US2.5] 实现组件代码验证（`apiserver/services/component_service.py`，Python语法检查）
- [ ] T076 [P] [US2.5] 实现组件版本历史（`apiserver/services/component_service.py`）

### 前端实现

- [ ] T077 [P] [US2.5] 创建ComponentLayout布局（`web-ui/src/layouts/ComponentLayout.vue`）
- [ ] T078 [P] [US2.5] 实现组件列表页（`web-ui/src/views/Components/List.vue`）
- [ ] T079 [P] [US2.5] 实现组件编辑器（`web-ui/src/components/editors/MonacoEditor.vue`）
- [ ] T080 [P] [US2.5] 实现组件创建/编辑表单（类型选择、代码输入）

**Checkpoint**: 用户故事2.5完成 - 组件管理功能可用

---

## Phase 7: User Story 3 - 数据管理界面 (Priority: P1)

**Goal**: 提供股票信息、K线数据、Tick数据查询、更新和质量检查功能

**Independent Test**: 查询股票K线数据、触发数据更新、验证数据质量

### Tests for User Story 3

- [ ] T081 [P] [US3] 编写数据API契约测试（tests/contract/test_data_api.py）
- [ ] T082 [P] [US3] 编写数据更新集成测试（tests/integration/test_data_update.py）

### API Server实现

- [ ] T083 [P] [US3] 实现股票信息查询接口（`apiserver/api/data.py`，GET /api/data/stockinfo）
- [ ] T084 [P] [US3] 实现股票信息更新接口（`apiserver/api/data.py`，POST /api/data/stockinfo/sync）
- [ ] T085 [P] [US3] 实现K线数据查询接口（`apiserver/api/data.py`，GET /api/data/bars）
- [ ] T086 [P] [US3] 实现K线数据更新接口（`apiserver/api/data.py`，POST /api/data/bars/sync）
- [ ] T087 [P] [US3] 实现Tick数据查询接口（`apiserver/api/data.py`，GET /api/data/ticks）
- [ ] T088 [US3] 实现数据质量报告接口（`apiserver/api/data.py`，GET /api/data/quality）

### 前端实现

- [ ] T089 [P] [US3] 创建SettingsLayout布局（`web-ui/src/layouts/SettingsLayout.vue`）
- [ ] T090 [P] [US3] 实现股票信息页（`web-ui/src/views/Data/StockInfo.vue`）
- [ ] T091 [P] [US3] 实现K线数据页（`web-ui/src/views/Data/Bars.vue`）
- [ ] T092 [P] [US3] 实现K线图表组件（`web-ui/src/components/charts/KLineChart.vue`，Lightweight Charts）

**Checkpoint**: 用户故事3完成 - 数据管理功能可用

---

## Phase 8: User Story 4 - API服务接口 (Priority: P1)

**Goal**: 提供RESTful API和WebSocket接口，支持外部系统集成

**Independent Test**: API客户端测试各接口请求响应和数据格式

### Tests for User Story 4

- [ ] T093 [P] [US4] 编写OpenAPI规范验证（tests/contract/test_openapi_spec.py）
- [ ] T094 [P] [US4] 编写WebSocket连接测试（tests/integration/test_websocket_connection.py）

### API Server实现

- [ ] T095 [P] [US4] 自动生成OpenAPI文档（FastAPI内置，`/docs`端点）
- [ ] T096 [P] [US4] 配置WebSocket端点（`ws://{host}/ws/portfolio`，`ws://{host}/ws/signals`）
- [ ] T097 [P] [US4] 实现API健康检查接口（`GET /health`）

### 前端实现

- [ ] T098 [P] [US4] 前端API封装层完善（统一错误处理、Token刷新）

**Checkpoint**: 用户故事4完成 - API接口就绪

---

## Phase 9: User Story 5 - 警报中心与历史 (Priority: P1)

**Goal**: 提供实时警报查看、历史记录查询、处理状态标记功能

**Independent Test**: 触发风控警报、查看实时警报、查询历史记录

### Tests for User Story 5

- [ ] T099 [P] [US5] 编写警报API契约测试（tests/contract/test_alerts_api.py）
- [ ] T100 [P] [US5] 编写警报处理集成测试（tests/integration/test_alert_handling.py）

### API Server实现

- [ ] T101 [P] [US5] 实现实时警报接口（`apiserver/api/notifications.py`，GET /api/alerts/realtime）
- [ ] T102 [P] [US5] 实现历史警报接口（`apiserver/api/notifications.py`，GET /api/alerts/history）
- [ ] T103 [P] [US5] 实现警报标记处理接口（`apiserver/api/notifications.py`，POST /api/alerts/{uuid}/handle）
- [ ] T104 [US5] 实现警报业务服务（`apiserver/services/alert_service.py`）

### 前端实现

- [ ] T105 [P] [US5] 实现警报中心页（`web-ui/src/views/Alerts/Center.vue`）
- [ ] T106 [P] [US5] 实现实时警报Tab组件
- [ ] T107 [P] [US5] 实现历史警报Tab组件
- [ ] T108 [P] [US5] 实现警报详情弹窗

**Checkpoint**: 用户故事5完成 - 警报中心功能可用

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: 跨故事改进和优化

### 性能优化

- [ ] T109 [P] API响应时间优化（目标<500ms 95th percentile）
- [ ] T110 [P] WebSocket消息延迟优化（目标<100ms）
- [ ] T111 [P] 数据库查询优化（批量操作、索引优化）
- [ ] T112 [P] Redis缓存配置优化（热点数据缓存）

### 文档和部署

- [ ] T113 [P] 生成API文档（OpenAPI规范）
- [ ] T114 [P] 编写用户手册（`/home/kaoru/Ginkgo/specs/001-web-ui-api/quickstart.md`）
- [ ] T115 [P] 配置Nginx反向代理（SSL终止、WebSocket代理、静态文件服务）
- [ ] T116 [P] Docker部署测试（`docker-compose up`验证）

### 代码质量

- [ ] T117 [P] 代码质量检查（类型注解、命名规范、装饰器使用）
- [ ] T118 [P] 安全合规检查（敏感信息检查、配置文件.gitignore）
- [ ] T119 [P] 性能基准测试（批量操作、延迟、内存使用）
- [ ] T120 [P] TDD流程验证（确保所有功能都有对应的测试）

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖Setup完成 - 阻塞所有用户故事
- **User Stories (Phase 3-9)**: 依赖Foundational完成 - 可并行或按优先级执行
- **Polish (Phase 10)**: 依赖所有期望的用户故事完成

### User Story Dependencies

- **US1 (仪表盘)**: 可在Foundational完成后开始 - 无其他故事依赖
- **US1.5 (Paper模式)**: 可在Foundational完成后开始 - 依赖US1的Portfolio功能
- **US2 (回测管理)**: 可在Foundational完成后开始 - 无其他故事依赖
- **US2.5 (组件管理)**: 可在Foundational完成后开始 - 依赖US2的回测功能
- **US3 (数据管理)**: 可在Foundational完成后开始 - 无其他故事依赖
- **US4 (API接口)**: 基础设施完成后自然完成（其他API实现的同时）
- **US5 (警报中心)**: 可在Foundational完成后开始 - 依赖US1的Portfolio功能

### Within Each User Story

1. 测试先行（TDD）：编写失败的测试
2. API实现：后端接口和业务逻辑
3. WebSocket实现：实时推送功能
4. 前端实现：页面和组件
5. 集成：前后端联调

### Parallel Opportunities

**Setup阶段（Phase 1）**:
```bash
# 可并行执行
T001.1 创建main.py
T001.2 创建api/目录
T001.3 创建models/目录
...
T006.1 初始化Vue项目
T006.2 配置TailwindCSS
T006.3 集成Ant Design Vue
...
```

**Foundational阶段（Phase 2）**:
```bash
# 可并行执行
T008 JWT认证中间件
T009 认证接口
T010 CORS中间件
T012 错误处理中间件
...
```

**User Story 1（Phase 3）**:
```bash
# 测试并行
T027 仪表盘API契约测试
T028 Portfolio状态集成测试
T029 WebSocket连接测试

# API实现并行
T030 仪表盘统计接口
T031 Portfolio列表接口
T032 Portfolio详情接口
...

# WebSocket实现并行
T034 Portfolio数据推送处理器
T035 系统状态推送处理器

# 前端实现并行
T036 DashboardLayout组件
T037 首页视图
T038 ArenaRanking组件
...
```

**跨Story并行**:
- 不同用户故事可由不同开发者并行工作（US1、US2、US3等）
- 每个故事完成后独立测试和部署

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational
3. 完成 Phase 3: User Story 1（仪表盘）
4. **STOP and VALIDATE**: 独立测试仪表盘功能
5. 部署/演示MVP

### Incremental Delivery

1. Setup + Foundational → 基础就绪
2. US1（仪表盘）→ 测试独立 → 部署MVP 🎯
3. US1.5（Paper模式）→ 测试独立 → 部署
4. US2（回测管理）→ 测试独立 → 部署
5. US2.5（组件管理）→ 测试独立 → 部署
6. US3（数据管理）→ 测试独立 → 部署
7. US4（API接口）→ 基础设施完成后自然完成
8. US5（警报中心）→ 测试独立 → 部署
9. Polish → 最终优化

### Parallel Team Strategy

多开发者协作策略：

1. 团队共同完成 Phase 1 + Phase 2
2. Foundational完成后：
   - 开发者 A: US1（仪表盘）
   - 开发者 B: US2 + US2.5（回测管理）
   - 开发者 C: US3（数据管理）
   - 开发者 D: US5（警报中心）
3. 每个故事独立完成和集成
4. 最后共同完成Polish阶段

---

## 任务管理原则遵循

根据章程第6条任务管理原则，请确保：

- **任务数量控制**: 活跃任务列表不得超过5个，超出部分应归档或延期
- **定期清理**: 在每个开发阶段完成后，主动清理已完成和过期的任务
- **优先级明确**: 高优先级任务优先显示和执行
- **状态实时更新**: 任务状态必须及时更新，保持团队协作效率
- **用户体验优化**: 保持任务列表简洁，避免过长影响开发体验

---

## Notes

- **Web UI构建**: Web前端项目的构建步骤（`pnpm install`、`pnpm build`等）由用户手动执行，不在自动化任务中包含
- **TDD流程**: 每个用户故事遵循测试先行原则，先编写失败的测试，再实现功能
- **配置锁死**: Paper和Live模式配置锁死，需回到策略研发阶段重新回测验证
- **ServiceHub**: API Server必须通过ServiceHub访问Ginkgo核心服务，禁止直接访问数据库
- **DTO模式**: Kafka消息必须使用DTO包装，禁止直接发送字典
- **任务标记**: [P] = 可并行，[Story] = 所属用户故事
- 文件路径必须明确（如 `apiserver/api/auth.py`）
- 每个Checkpoint后验证独立功能可用性
