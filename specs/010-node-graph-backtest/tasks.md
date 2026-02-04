# Tasks: 节点图拖拉拽配置回测功能

**Input**: Design documents from `/specs/010-node-graph-backtest/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - not explicitly requested in feature specification (FR-010 mentions TDD but not as hard requirement for all tasks)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **后端**: `apiserver/` (Python FastAPI)
- **前端**: `web-ui/src/` (Vue 3 + TypeScript)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency installation

- [ ] T001 安装前端依赖 @vue-flow/core 及插件在 web-ui/ (npm install @vue-flow/core @vue-flow/background @vue-flow/controls @vue-flow/minimap)
- [ ] T002 创建数据库表 node_graphs 和 node_graph_templates 在 apiserver/migrations/create_node_graphs.sql
- [ ] T003 [P] 配置认证中间件跳过 /api/node-graphs 路径在 apiserver/middleware/auth.py (添加到 SKIP_AUTH_PREFIXES)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### 后端数据模型和 Schema

- [ ] T004 [P] 创建 NodeGraph Pydantic schema 在 apiserver/schemas/node_graph.py (NodeGraphSummary, NodeGraph, NodeGraphCreate, NodeGraphUpdate)
- [ ] T005 [P] 创建 GraphData 相关 schema 在 apiserver/schemas/node_graph.py (GraphData, GraphNode, GraphEdge)
- [ ] T006 [P] 创建 NodeTemplate Pydantic schema 在 apiserver/schemas/node_graph.py
- [ ] T007 [P] 创建 ValidationResult schema 在 apiserver/schemas/node_graph.py

### 前端类型定义

- [ ] T008 [P] 创建节点类型枚举和端口定义 在 web-ui/src/components/node-graph/types.ts (NodeType, NODE_TYPE_LABELS, NodePort, NODE_PORTS)
- [ ] T009 [P] 创建节点数据结构类型 在 web-ui/src/components/node-graph/types.ts (NodeData, NodeConfig, GraphNode, GraphEdge)
- [ ] T010 [P] 创建节点图配置类型 在 web-ui/src/components/node-graph/types.ts (GraphData, NodeGraph, NodeGraphSummary, NodeTemplate)
- [ ] T011 [P] 创建验证和编译相关类型 在 web-ui/src/components/node-graph/types.ts (ValidationResult, CompileResult, BacktestTaskCreate)
- [ ] T012 [P] 创建连接规则和工具函数 在 web-ui/src/components/node-graph/types.ts (CONNECTION_RULES, canConnect, getInputPorts, getOutputPorts)

### 前端状态管理

- [ ] T013 创建节点图 Pinia store 在 web-ui/src/stores/nodeGraph.ts (管理 nodes, edges, viewport, selectedNodes, selectedEdges 状态)
- [ ] T014 创建节点图操作 composable 在 web-ui/src/composables/useNodeGraph.ts (addNode, removeNode, addEdge, removeEdge 等操作)

### 前端 API 模块

- [ ] T015 创建节点图 API 模块 在 web-ui/src/api/modules/nodeGraph.ts (list, get, create, update, delete, compile, validate, getTemplates)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - 节点画布基础操作 (Priority: P1) 🎯 MVP

**Goal**: 用户通过可视化画布创建和管理回测配置节点，支持添加、连接、删除节点

**Independent Test**: 用户可以独立测试节点添加、连线、删除操作，无需依赖后端编译和执行功能。画布操作完全在前端实现，不涉及服务器交互。

### 前端组件实现

- [ ] T016 [P] [US1] 创建节点图编辑器核心组件 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (集成 VueFlow，处理节点和边的 v-model)
- [ ] T017 [P] [US1] 创建画布组件 在 web-ui/src/components/node-graph/NodeGraphCanvas.vue (包含 Background, Controls, MiniMap 插件)
- [ ] T018 [P] [US1] 创建节点组件 在 web-ui/src/components/node-graph/NodeComponent.vue (自定义节点渲染，支持拖拽)
- [ ] T019 [P] [US1] 创建连接线组件 在 web-ui/src/components/node-graph/ConnectionLine.vue (自定义边样式和路径)
- [ ] T020 [P] [US1] 创建节点选择面板 在 web-ui/src/components/node-graph/NodePalette.vue (显示9种节点类型，支持拖拽到画布)
- [ ] T021 [US1] 实现节点拖拽添加逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (onDrop 事件处理，添加节点到 nodes 数组)
- [ ] T022 [US1] 实现节点连接逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (onConnect 事件处理，验证连接规则，添加到 edges 数组)
- [ ] T023 [US1] 实现节点删除逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (选中节点后按 Delete 键删除，同时删除相关连接)
- [ ] T024 [US1] 实现连接线删除逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (选中边后点击删除按钮)
- [ ] T025 [US1] 实现画布缩放和平移 在 web-ui/src/components/node-graph/NodeGraphCanvas.vue (使用 VueFlow 的 zoom 和 pan 功能)
- [ ] T026 [US1] 实现撤销/重做功能 在 web-ui/src/composables/useNodeGraph.ts (使用命令模式，支持至少20步历史)

### 主页面和路由

- [ ] T027 [US1] 创建节点图编辑器主页面 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (集成所有组件，包含工具栏和操作按钮)
- [ ] T028 [US1] 添加节点图路由 在 web-ui/src/router/index.ts (路径 /backtest/graph-editor)

**Checkpoint**: At this point, User Story 1 should be fully functional - 用户可以在画布上添加、连接、删除节点，支持缩放平移和撤销重做

---

## Phase 4: User Story 2 - 节点参数配置 (Priority: P1)

**Goal**: 用户点击节点可打开参数面板，配置节点特定参数

**Independent Test**: 用户可以为单个节点配置参数并保存（前端状态），验证参数持久化和表单验证逻辑。参数配置在前端完成，保存功能依赖 US4。

### 前端参数配置组件

- [ ] T029 [P] [US2] 创建节点属性编辑面板 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (右侧面板，显示选中节点的参数)
- [ ] T030 [P] [US2] 创建 Engine 节点参数表单 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (start_date, end_date 日期选择器)
- [ ] T031 [P] [US2] 创建 Broker 节点参数表单 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (broker_type 下拉框，initial_cash, commission_rate, slippage_rate, broker_attitude 输入)
- [ ] T032 [P] [US2] 创建 Portfolio 节点参数表单 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (portfolio_uuid 选择器，调用 /api/portfolio)
- [ ] T033 [P] [US2] 创建 Strategy 节点参数表单 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (component_uuid 选择器，调用 /api/components)
- [ ] T034 [P] [US2] 创建 Selector/Sizer/Risk/Analyzer 节点参数表单 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (component_uuid 选择器)
- [ ] T035 [US2] 实现参数表单验证 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (日期格式、数值范围、必填字段验证)
- [ ] T036 [US2] 实现参数保存到节点数据 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (更新 node.data.config，节点显示摘要信息)
- [ ] T037 [US2] 实现节点摘要显示 在 web-ui/src/components/node-graph/NodeComponent.vue (在节点上显示配置的关键信息，如策略名称、时间范围)
- [ ] T038 [US2] 实现动态参数表单 在 web-ui/src/components/node-graph/NodePropertyPanel.vue (根据 Broker 类型显示不同的配置项，如 OKX 类型显示 API Key 字段)

**Checkpoint**: At this point, User Story 2 should be fully functional - 用户可以点击节点打开右侧面板，配置各类型节点的参数，验证表单正确显示错误提示

---

## Phase 5: User Story 3 - 节点图验证与错误提示 (Priority: P2)

**Goal**: 系统实时验证节点图的有效性，检测并提示配置错误

**Independent Test**: 用户可以故意创建错误配置（如循环依赖、缺失参数），验证错误提示的准确性和位置指示。验证逻辑在前端实现，无需后端支持。

### 前端验证逻辑

- [ ] T039 [P] [US3] 创建验证结果展示组件 在 web-ui/src/components/node-graph/GraphValidator.vue (显示错误列表、警告信息、验证状态)
- [ ] T040 [US3] 实现节点图结构验证 在 web-ui/src/composables/useNodeGraph.ts (验证必须有且只有一个 ENGINE 节点，至少一个 PORTFOLIO 节点)
- [ ] T041 [US3] 实现连接规则验证 在 web-ui/src/composables/useNodeGraph.ts (使用 CONNECTION_RULES 验证连接是否合规)
- [ ] T042 [US3] 实现循环依赖检测 在 web-ui/src/composables/useNodeGraph.ts (使用 DFS 算法检测图中的环)
- [ ] T043 [US3] 实现节点参数验证 在 web-ui/src/composables/useNodeGraph.ts (验证必需参数是否配置，如 Engine 的 start_date)
- [ ] T044 [US3] 实现端口类型匹配验证 在 web-ui/src/composables/useNodeGraph.ts (验证 sourceHandle 和 targetHandle 的数据类型兼容)
- [ ] T045 [US3] 实现实时验证触发 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (nodes 或 edges 变化时自动触发验证)
- [ ] T046 [US3] 实现错误视觉反馈 在 web-ui/src/components/node-graph/NodeComponent.vue (有错误的节点显示红色边框)
- [ ] T047 [US3] 实现错误连接线视觉反馈 在 web-ui/src/components/node-graph/ConnectionLine.vue (违规连接显示红色虚线)
- [ ] T048 [US3] 集成验证组件到主页面 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (显示验证结果，根据 is_valid 启用/禁用保存按钮)
- [ ] T049 [US3] 实现手动验证按钮 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (触发验证，显示"配置有效"提示)

**Checkpoint**: At this point, User Story 3 should be fully functional - 用户可以看到实时验证结果，错误节点和连接高亮显示，只有有效配置才能保存

---

## Phase 6: User Story 4 - 节点图保存与加载 (Priority: P2)

**Goal**: 用户可以保存当前节点图配置，并从保存的配置列表中加载历史配置

**Independent Test**: 用户可以保存节点图并重新加载，验证配置完整性和节点/参数还原正确性。需要后端 API 支持。

### 后端 API 实现

- [ ] T050 [P] [US4] 创建节点图数据库操作函数 在 apiserver/api/node_graphs.py (实现 get_db, create_backtest_task 类似的数据库操作)
- [ ] T051 [P] [US4] 实现获取节点图列表 API 在 apiserver/api/node_graphs.py (GET /api/node-graphs，分页、筛选)
- [ ] T052 [P] [US4] 实现创建节点图 API 在 apiserver/api/node_graphs.py (POST /api/node-graphs，生成 UUID，写入 MySQL)
- [ ] T053 [P] [US4] 实现获取节点图详情 API 在 apiserver/api/node_graphs.py (GET /api/node-graphs/{uuid})
- [ ] T054 [P] [US4] 实现更新节点图 API 在 apiserver/api/node_graphs.py (PUT /api/node-graphs/{uuid})
- [ ] T055 [P] [US4] 实现删除节点图 API 在 apiserver/api/node_graphs.py (DELETE /api/node-graphs/{uuid})
- [ ] T056 [US4] 注册节点图路由 在 apiserver/main.py (router.include_router 到 /api/node-graphs)

### 前端保存加载功能

- [ ] T057 [US4] 实现保存节点图功能 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (调用 nodeGraphApi.create，显示保存对话框输入名称)
- [ ] T058 [US4] 实现加载节点图功能 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (调用 nodeGraphApi.list 显示配置列表，选择后加载到画布)
- [ ] T059 [US4] 实现配置列表弹窗 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (显示已保存的配置，支持搜索和筛选)
- [ ] T060 [US4] 实现覆盖保存逻辑 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (修改已保存配置时提示"覆盖保存"或"另存为新配置")
- [ ] T061 [US4] 实现删除配置功能 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (确认后调用 nodeGraphApi.delete)
- [ ] T062 [US4] 实现配置还原逻辑 在 web-ui/src/composables/useNodeGraph.ts (从 API 加载的 JSON 还原 nodes 和 edges 状态)

**Checkpoint**: At this point, User Story 4 should be fully functional - 用户可以保存、加载、删除节点图配置，配置持久化到 MySQL

---

## Phase 7: User Story 5 - 节点图编译与回测任务创建 (Priority: P2)

**Goal**: 系统将节点图编译为回测任务配置，发送到后端 API 创建回测任务

**Independent Test**: 用户可以编译节点图并查看生成的配置 JSON，验证编译逻辑正确性，无需实际运行回测。

### 后端编译服务

- [ ] T063 [P] [US5] 创建节点图编译服务 在 apiserver/services/graph_compiler.py (实现 GraphCompiler 类，compile 方法)
- [ ] T064 [P] [US5] 实现节点查找逻辑 在 apiserver/services/graph_compiler.py (_find_node_by_type, _find_nodes_by_type)
- [ ] T065 [P] [US5] 实现 Engine 配置映射 在 apiserver/services/graph_compiler.py (ENGINE 节点 → engine_config.start_date, end_date)
- [ ] T066 [P] [US5] 实现 Broker 配置映射 在 apiserver/services/graph_compiler.py (BROKER 节点 → engine_config.broker_*)
- [ ] T067 [P] [US5] 实现 Portfolio 配置映射 在 apiserver/services/graph_compiler.py (PORTFOLIO 节点 → portfolio_uuids)
- [ ] T068 [P] [US5] 实现 Component 配置映射 在 apiserver/services/graph_compiler.py (STRATEGY/RISK 等组件 → component_config)
- [ ] T069 [P] [US5] 实现编译 API 在 apiserver/api/node_graphs.py (POST /api/node-graphs/{uuid}/compile)
- [ ] T070 [US5] 实现验证 API 在 apiserver/api/node_graphs.py (POST /api/node-graphs/{uuid}/validate，调用前端相同的验证逻辑)

### 前端编译功能

- [ ] T071 [US5] 实现编译功能 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (调用 nodeGraphApi.compile，显示生成的 JSON)
- [ ] T072 [US5] 实现编译预览弹窗 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (显示 backtest_config JSON，支持复制)
- [ ] T073 [US5] 实现创建回测任务功能 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (编译成功后点击按钮调用 /api/backtest 创建任务)
- [ ] T074 [US5] 实现编译错误处理 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (显示编译失败错误，阻止任务创建)
- [ ] T075 [US5] 实现任务创建后跳转 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (成功后跳转到回测详情页 /backtest/{uuid})

**Checkpoint**: At this point, User Story 5 should be fully functional - 用户可以编译节点图为回测配置，预览 JSON，创建回测任务

---

## Phase 8: User Story 6 - 节点图模板与预设 (Priority: P3)

**Goal**: 系统提供常用回测配置的节点图模板，用户可基于模板快速创建配置

**Independent Test**: 用户可以选择模板并加载到画布，验证模板节点和参数预填充正确性。

### 后端模板功能

- [ ] T076 [P] [US6] 创建模板数据 在 apiserver/migrations/create_node_graphs.sql (INSERT 5个预设模板到 node_graph_templates 表)
- [ ] T077 [P] [US6] 实现获取模板列表 API 在 apiserver/api/node_graphs.py (GET /api/node-graphs/templates，支持 category 筛选)
- [ ] T078 [P] [US6] 实现获取模板详情 API 在 apiserver/api/node_graphs.py (GET /api/node-graphs/templates/{uuid})

### 前端模板功能

- [ ] T079 [US6] 实现模板列表组件 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (显示5个预设模板：双均线策略、多因子策略、网格交易、动量策略、均值回归)
- [ ] T080 [US6] 实现从模板创建功能 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (选择模板后加载 graph_data 到画布)
- [ ] T081 [US6] 实现模板加载后保存逻辑 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (修改模板参数后保存为新配置，不覆盖模板)
- [ ] T082 [US6] 实现模板分类筛选 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (按 category 分组显示模板)

**Checkpoint**: All user stories should now be independently functional - 用户可以从模板快速创建节点图配置

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

### Ginkgo 后端优化任务

- [ ] T083 [P] 添加 @time_logger 装饰器 在 apiserver/services/graph_compiler.py (监控编译方法执行时间)
- [ ] T084 [P] 添加 @cache_with_expiration 装饰器 在 apiserver/api/node_graphs.py (缓存模板列表和频繁访问的配置)
- [ ] T085 [P] 添加类型注解 在 apiserver/api/node_graphs.py (所有函数参数和返回值类型注解)
- [ ] T086 [P] 添加结构化日志 在 apiserver/api/node_graphs.py (使用 logger.info 记录关键操作)
- [ ] T087 [P] 添加错误处理 在 apiserver/api/node_graphs.py (统一使用 HTTPException 返回错误)

### Ginkgo 质量保证任务

- [ ] T088 [P] 添加代码文件头部注释 在 apiserver/api/node_graphs.py 和 apiserver/services/graph_compiler.py (Upstream/Downstream/Role 三行注释)
- [ ] T089 [P] 验证配置完整性 遵循章程验证完整性原则 (确保数据库表存在，索引正确，配置可从文件读取)
- [ ] T090 [P] 安全检查 在 apiserver/ (确保敏感信息不在代码中，.gitignore 正确配置)

### 前端优化任务

- [ ] T091 [P] 优化节点拖拽性能 在 web-ui/src/components/node-graph/NodeGraphEditor.vue (确保拖拽响应 < 50ms)
- [ ] T092 [P] 优化连接线绘制 在 web-ui/src/components/node-graph/ConnectionLine.vue (确保 > 60fps 更新率)
- [ ] T093 [P] 添加加载状态 在 web-ui/src/api/modules/nodeGraph.ts (请求过程中显示 loading 状态)
- [ ] T094 [P] 添加错误提示 在 web-ui/src/views/Backtest/BacktestGraphEditor.vue (使用 Ant Design Vue message 组件)

### 文档和维护任务

- [ ] T095 [P] 更新 API 文档 在 specs/010-node-graph-backtest/contracts/api.yaml (确保与实现一致)
- [ ] T096 [P] 更新快速开始指南 在 specs/010-node-graph-backtest/quickstart.md (验证所有步骤可执行)
- [ ] T097 运行 quickstart.md 验证测试 (按照快速开始指南完整操作一遍，确保所有步骤正常)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1 (P1) - 节点画布基础操作: No dependencies on other stories
  - US2 (P1) - 节点参数配置: Depends on US1 (需要节点组件和画布)
  - US3 (P2) - 节点图验证与错误提示: Depends on US1 (需要节点和边数据结构)
  - US4 (P2) - 节点图保存与加载: Can run parallel with US2, US3 (独立的后端 API)
  - US5 (P2) - 节点图编译与回测任务创建: Depends on US1 (需要完整的节点图数据)
  - US6 (P3) - 节点图模板与预设: Depends on US1, US4 (需要画布和保存功能)
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundational (Phase 2)
    │
    ├──> US1 (P1) 节点画布基础操作 ───> US2 (P1) 节点参数配置
    │                                      │
    │                                      └──> US3 (P2) 节点图验证
    │
    └──> US4 (P2) 节点图保存与加载 ──────> US6 (P3) 节点图模板
         │
         └──> US5 (P2) 节点图编译
```

### Within Each User Story

- 组件创建可以并行进行 (标记 [P] 的任务)
- 核心逻辑在组件创建之后
- 主页面集成在组件之后
- 每个故事完成后应独立测试

### Parallel Opportunities

- Setup 阶段所有任务可并行
- Foundational 阶段所有模型和类型定义可并行
- US1 中所有组件创建可并行
- US2 中所有参数表单可并行
- US3 中验证逻辑组件可并行
- US4 中后端 API 任务可并行
- US5 中编译服务任务可并行
- US6 中模板数据创建可并行
- Polish 阶段所有优化任务可并行

---

## Parallel Example: User Story 1

```bash
# 所有组件可以并行创建:
Task: "创建节点图编辑器核心组件 在 web-ui/src/components/node-graph/NodeGraphEditor.vue"
Task: "创建画布组件 在 web-ui/src/components/node-graph/NodeGraphCanvas.vue"
Task: "创建节点组件 在 web-ui/src/components/node-graph/NodeComponent.vue"
Task: "创建连接线组件 在 web-ui/src/components/node-graph/ConnectionLine.vue"
Task: "创建节点选择面板 在 web-ui/src/components/node-graph/NodePalette.vue"

# 所有功能可以并行实现:
Task: "实现节点拖拽添加逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue"
Task: "实现节点连接逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue"
Task: "实现节点删除逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue"
Task: "实现连接线删除逻辑 在 web-ui/src/components/node-graph/NodeGraphEditor.vue"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup (安装依赖、创建数据库表、配置认证)
2. Complete Phase 2: Foundational (数据模型、Schema、类型定义、状态管理、API 模块)
3. Complete Phase 3: User Story 1 - 节点画布基础操作
4. Complete Phase 4: User Story 2 - 节点参数配置
5. **STOP and VALIDATE**: 测试节点画布和参数配置功能是否正常工作
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → 基础架构完成
2. Add US1 (画布操作) → 独立测试 → MVP 可演示
3. Add US2 (参数配置) → 独立测试 → 增强功能
4. Add US3 (验证功能) → 独立测试 → 用户体验提升
5. Add US4 (保存加载) → 独立测试 → 数据持久化
6. Add US5 (编译功能) → 独立测试 → 完整功能链路
7. Add US6 (模板功能) → 独立测试 → 降低学习成本
8. Polish → 生产就绪

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (画布操作) + US2 (参数配置)
   - Developer B: US3 (验证功能) + US5 (编译功能)
   - Developer C: US4 (保存加载) + US6 (模板功能)
3. Stories complete and integrate independently

---

## 任务管理原则遵循

根据章程第6条任务管理原则，请确保：

- **任务数量控制**: 活跃任务列表不得超过5个任务，超出部分应归档或延期
- **定期清理**: 在每个开发阶段完成后，主动清理已完成和过期的任务
- **优先级明确**: 高优先级任务优先显示和执行
- **状态实时更新**: 任务状态必须及时更新，保持团队协作效率
- **用户体验优化**: 保持任务列表简洁，避免过长影响开发体验

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- **任务管理原则**: 遵循章程要求，保持任务列表精简高效

---

## Summary

- **Total Tasks**: 97 tasks
- **Tasks per user story**:
  - Phase 1 (Setup): 3 tasks
  - Phase 2 (Foundational): 15 tasks
  - US1 (节点画布基础操作): 12 tasks
  - US2 (节点参数配置): 10 tasks
  - US3 (节点图验证与错误提示): 11 tasks
  - US4 (节点图保存与加载): 13 tasks
  - US5 (节点图编译与回测任务创建): 13 tasks
  - US6 (节点图模板与预设): 7 tasks
  - Phase 9 (Polish): 15 tasks

- **Parallel opportunities**: 60 tasks marked [P] can run in parallel with others in their phase

- **MVP Scope**: Phase 1 + Phase 2 + US1 + US2 (40 tasks) - 基础画布操作和参数配置

- **Independent test criteria for each story**: 验证每个用户故事可以在不依赖其他故事的情况下独立完成和测试
