# Implementation Plan: 节点图拖拉拽配置回测功能

**Branch**: `010-node-graph-backtest` | **Date**: 2026-02-02 | **Spec**: [spec.md](../spec.md)
**Input**: Feature specification from `/specs/010-node-graph-backtest/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

为 Ginkgo 量化交易系统添加可视化节点图编辑器，使用户能够通过拖拽节点和连接线来配置回测任务，替代传统表单配置方式。

**技术方案**:
- **前端**: Vue 3 + TypeScript，使用 `@vue-flow/core` 库实现节点图编辑器
- **后端**: FastAPI 扩展，新增节点图配置 CRUD API 和编译服务
- **存储**: MySQL 新增 `node_graphs` 和 `node_templates` 表
- **集成**: 节点图编译为现有的 BacktestTaskCreate 格式，复用现有回测执行流程

## Technical Context

**Language/Version**:
- 后端: Python 3.12.8
- 前端: TypeScript 5.3 + Vue 3.4

**Primary Dependencies**:
- 后端: FastAPI, asyncmy, Pydantic, kafka-python
- 前端: @vue-flow/core, Vue Router 4, Pinia 2, Ant Design Vue 4

**Storage**:
- ClickHouse (时序数据)
- MySQL (关系数据 - 新增 node_graphs, node_templates 表)
- MongoDB (文档数据)
- Redis (缓存)

**Testing**: pytest with TDD workflow, unit/integration/database/network 标记分类

**Target Platform**: Linux server (后端) + 现代浏览器 (前端)

**Project Type**: hybrid (Python 后端 + TypeScript 前端)

**Performance Goals**:
- 节点拖拽响应 < 50ms (< 100 节点时)
- 连接线绘制 > 60fps
- 节点图验证 < 500ms (50 节点规模)
- 配置保存/加载成功率 > 99%

**Constraints**:
- 前端必须支持现代浏览器 (Chrome, Firefox, Safari, Edge 最新两版本)
- 节点图编译结果必须兼容现有 BacktestTaskCreate API
- 遵循 Ginkgo 事件驱动架构原则

**Scale/Scope**:
- 支持最多 100 个节点的节点图
- 支持 9 种节点类型 (Engine, Feeder, Broker, Portfolio, Strategy, Selector, Sizer, RiskManagement, Analyzer)
- 支持至少 5 个预设模板

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理
- [x] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import services`访问服务组件
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [x] 提供类型注解，支持静态类型检查
- [x] 禁止使用hasattr等反射机制回避类型错误
- [x] 遵循既定命名约定 (CRUD前缀、模型继承等)

### 测试原则 (Testing Excellence)
- [x] 遵循TDD流程，先写测试再实现功能
- [x] 测试按unit、integration、database、network标记分类
- [x] 数据库测试使用测试数据库，避免影响生产数据

### 性能原则 (Performance Excellence)
- [x] 数据操作使用批量方法 (如add_bars) 而非单条操作
- [x] 合理使用多级缓存 (Redis + Memory + Method级别)
- [x] 使用懒加载机制优化启动时间

### 任务管理原则 (Task Management Excellence)
- [x] 任务列表限制在最多5个活跃任务
- [x] 已完成任务立即从活跃列表移除
- [x] 任务优先级明确，高优先级任务优先显示
- [x] 任务状态实时更新，确保团队协作效率

### 文档原则 (Documentation Excellence)
- [x] 文档和注释使用中文
- [x] 核心API提供详细使用示例和参数说明
- [x] 重要组件有清晰的架构说明和设计理念文档

### 代码注释同步原则 (Code Header Synchronization)
- [x] 修改类的功能、添加/删除主要类或函数时，更新Role描述
- [x] 修改模块依赖关系时，更新Upstream/Downstream描述
- [x] 代码审查过程中检查头部信息的准确性
- [x] 定期运行`scripts/verify_headers.py`检查头部一致性
- [x] CI/CD流程包含头部准确性检查
- [x] 使用`scripts/generate_headers.py --force`批量更新头部

### 验证完整性原则 (Verification Integrity)
- [x] 配置类功能验证包含配置文件检查（不仅检查返回值）
- [x] 验证配置文件包含对应配置项（如 grep config.yml notifications.timeout）
- [x] 验证值从配置文件读取，而非代码默认值（打印原始配置内容）
- [x] 验证用户可通过修改配置文件改变行为（修改配置后重新运行）
- [x] 验证缺失配置时降级到默认值（删除配置项后验证）
- [x] 外部依赖验证包含存在性、正确性、版本兼容性检查
- [x] 禁止仅因默认值/Mock使测试通过就认为验证完成

### DTO消息队列原则 (DTO Message Pattern)
- [x] 所有Kafka消息发送使用DTO包装（ControlCommandDTO等）
- [x] 发送端使用DTO.model_dump_json()序列化
- [x] 接收端使用DTO(**data)反序列化
- [x] 使用DTO.Commands常量类定义命令/事件类型
- [x] 使用DTO.is_xxx()方法进行类型判断
- [x] 禁止直接发送字典或裸JSON字符串到Kafka
- [x] DTO使用Pydantic BaseModel实现类型验证

**Gate Status**: ✅ PASSED - 所有原则检查通过，无需复杂性追踪

## Project Structure

### Documentation (this feature)

```text
specs/010-node-graph-backtest/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api.yaml         # OpenAPI specification
│   └── graph-schema.ts  # TypeScript types for node graph
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# 前端结构 (web-ui/)
web-ui/src/
├── views/
│   └── Backtest/
│       ├── BacktestGraphEditor.vue           # 节点图编辑器主页面 (新建)
│       ├── BacktestList.vue                  # 现有
│       └── BacktestCreate.vue                # 现有（保留或改造）
├── components/
│   └── node-graph/                            # 节点图组件目录 (新建)
│       ├── NodeGraphEditor.vue               # 节点图编辑器核心
│       ├── NodeGraphCanvas.vue               # 画布组件
│       ├── NodeComponent.vue                 # 节点组件
│       ├── ConnectionLine.vue                # 连接线组件
│       ├── NodePalette.vue                   # 节点选择面板
│       ├── NodePropertyPanel.vue             # 节点属性编辑面板
│       ├── GraphValidator.vue                # 验证结果展示
│       └── types.ts                          # TypeScript 类型定义
├── stores/
│   └── nodeGraph.ts                          # 节点图状态管理 (新建)
├── composables/
│   └── useNodeGraph.ts                       # 节点图操作 composable (新建)
├── router/
│   └── index.ts                              # 添加节点图路由
└── api/
    └── modules/
        └── nodeGraph.ts                      # 节点图 API 模块 (新建)

# 后端结构 (apiserver/)
apiserver/
├── api/
│   ├── node_graphs.py                        # 节点图配置 API (新建)
│   └── backtest.py                           # 扩展（支持节点图编译）
├── models/
│   └── node_graph.py                         # 节点图数据模型 (新建)
├── services/
│   ├── graph_compiler.py                     # 节点图编译服务 (新建)
│   └── graph_validator.py                    # 节点图验证服务 (新建)
├── schemas/
│   └── node_graph.py                         # Pydantic schemas (新建)
└── migrations/
    └── create_node_graphs.sql                # 节点图表创建脚本 (新建)
```

**Structure Decision**:
- **前端**: 在现有 Vue 3 项目中新增 `node-graph` 组件目录，使用 `@vue-flow/core` 作为节点图基础库
- **后端**: 在现有 FastAPI 项目中新增节点图相关 API，复用现有数据库连接和认证中间件
- **存储**: MySQL 新增两张表存储节点图配置和模板
- **集成**: 节点图编译为现有的 BacktestTaskCreate 格式，通过 Kafka 发送到 Worker

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | Constitution Check 全部通过 | 无需复杂性追踪 |

## Phase 0: Research & Technology Decisions

### Research Tasks

1. **前端节点图库选型**
   - 评估 `@vue-flow/core` vs `vue-dag` vs `react-flow` (with Vue wrapper)
   - 确认 TypeScript 支持和文档质量
   - 验证与 Ant Design Vue 的兼容性

2. **节点图数据结构设计**
   - 定义节点类型枚举和端口配置
   - 设计节点连接规则验证逻辑
   - 确定撤销/重做历史存储方案

3. **后端编译服务设计**
   - 研究现有 Engine 装配逻辑 (`engine_assembly_service.py`)
   - 设计节点图到 BacktestTaskCreate 的映射规则
   - 确认是否需要新的 DTO 类型

4. **数据库设计验证**
   - 确认 MySQL JSON 字段性能表现
   - 设计节点图版本历史预留字段
   - 确定索引策略 (user_uuid, is_template)

## Phase 1: Design & Contracts

### Data Model Design

详见 `data-model.md`:
- `NodeGraph` 实体
- `NodeTemplate` 实体
- `GraphNode` 类型
- `GraphConnection` 类型
- 节点端口定义 Schema

### API Contracts

详见 `contracts/api.yaml`:
- `GET /api/node-graphs` - 列出节点图配置
- `POST /api/node-graphs` - 创建节点图配置
- `GET /api/node-graphs/{uuid}` - 获取节点图详情
- `PUT /api/node-graphs/{uuid}` - 更新节点图配置
- `DELETE /api/node-graphs/{uuid}` - 删除节点图配置
- `POST /api/node-graphs/{uuid}/compile` - 编译节点图为回测配置
- `GET /api/node-graphs/templates` - 获取模板列表

### Frontend Types

详见 `contracts/graph-schema.ts`:
- TypeScript 类型定义
- 节点配置 Schema
- 验证规则定义

## Phase 2: Implementation Tasks

(由 `/speckit.tasks` 命令生成，不在本计划中)

## Implementation Phases Summary

### Phase 0: Research ✅ Completed
- [x] 代码库结构探索
- [x] 技术选型调研（选择 @vue-flow/core）
- [x] 数据结构设计
- [x] 生成 `research.md`

### Phase 1: Design ✅ Completed
- [x] 数据模型设计 (`data-model.md`)
- [x] API 契约定义 (`contracts/api.yaml`)
- [x] 前端类型定义 (`contracts/graph-schema.ts`)
- [x] 快速开始指南 (`quickstart.md`)
- [x] 更新 agent 上下文

### Phase 2: Implementation
- [ ] 由 `/speckit.tasks` 命令生成详细任务列表

---

**Post-Phase 1 Constitution Re-evaluation**: ✅ PASSED

Phase 1 设计完成后，重新评估所有原则检查项，确认设计符合 Ginkgo 项目章程：
- 数据模型使用 MySQL JSON 字段，符合数据存储原则
- API 契约遵循 FastAPI 约定，符合架构设计原则
- 前端类型定义完整，符合代码质量原则
- 无需额外的复杂性追踪
