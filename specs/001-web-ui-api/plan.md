# Implementation Plan: Web UI and API Server

**Branch**: `001-web-ui-api` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-web-ui-api/spec.md`

## Summary

构建Ginkgo量化交易系统的Web用户界面和API Server，提供实时监控仪表盘、策略回测管理、回测组件管理、数据管理界面和警报中心等功能。

**核心功能**:
- 实时监控仪表盘（支持多Portfolio分屏展示）
- 策略回测管理（Backtest → Paper → Live模式流转）
- 回测组件管理（Strategy/Selector/Sizer/RiskManager/Analyzer）
- 数据管理界面（股票信息、K线、Tick数据）
- API Server（RESTful + WebSocket）
- 警报中心（实时警报和历史记录）

**技术方案**:
- **后端**: FastAPI独立进程，通过ServiceHub访问Ginkgo核心服务
- **前端**: Vue 3 + Vite + TailwindCSS + Ant Design Vue
- **通信**: RESTful API（同步）+ WebSocket（实时推送）
- **图表**: Lightweight Charts（K线）+ ECharts（统计图表）

## Technical Context

**Language/Version**: Python 3.12.8 (后端), TypeScript (前端)
**Primary Dependencies**:
- 后端: FastAPI, uvicorn, Pydantic, kafka-python, websockets
- 前端: Vue 3, Vite, Pinia, Ant Design Vue, Lightweight Charts, ECharts
- 存储: ClickHouse (时序数据), MySQL (关系数据), MongoDB (文档数据), Redis (缓存/心跳)
- 消息: Kafka (实时数据推送)

**Storage**:
- ClickHouse: K线数据、Tick数据、净值历史
- MySQL: 股票信息、用户数据、组件元数据
- MongoDB: 通知历史、回测结果详情
- Redis: 缓存、Session、心跳状态

**Testing**: pytest (后端), Vitest (前端), TDD流程
**Target Platform**: Linux server (后端), 现代浏览器 (前端)

**Project Type**: multi (后端Python + 前端TypeScript)

**Performance Goals**:
- API响应时间 < 500ms (95th percentile)
- WebSocket消息延迟 < 100ms
- 支持100并发用户
- 仪表盘数据刷新延迟 < 2秒

**Constraints**:
- API Server必须通过ServiceHub访问核心服务，不直接访问数据库
- Web UI仅通过API与后端交互
- 必须遵循事件驱动架构
- Paper和Live模式配置锁死
- Web前端构建由用户手动执行（不包含在自动化任务中）

**Scale/Scope**:
- 支持Portfolio横向扩展（无数量限制）
- 常用2-4个Portfolio分屏展示
- 支持多策略并行回测
- 处理千万级历史数据

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 安全与合规原则 (Security & Compliance)
- [x] 所有代码提交前已进行敏感文件检查
- [x] API密钥、数据库凭证等敏感信息使用环境变量或配置文件管理（.env文件）
- [x] 敏感配置文件已添加到.gitignore

### 架构设计原则 (Architecture Excellence)
- [x] 设计遵循事件驱动架构 (PriceUpdate → Strategy → Signal → Portfolio → Order → Fill)
- [x] 使用ServiceHub统一访问服务，通过`from ginkgo import service_hub`访问服务组件
- [x] 严格分离数据层、策略层、执行层、分析层和服务层职责

### 代码质量原则 (Code Quality)
- [x] 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器
- [x] 提供类型注解，支持静态类型检查（Pydantic + TypeScript）
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

### 验证完整性原则 (Verification Integrity)
- [x] 配置类功能验证包含配置文件检查（不仅检查返回值）
- [x] 验证配置文件包含对应配置项
- [x] 验证值从配置文件读取，而非代码默认值
- [x] 验证用户可通过修改配置文件改变行为
- [x] 外部依赖验证包含存在性、正确性、版本兼容性检查

### DTO消息队列原则 (DTO Message Pattern)
- [x] 所有Kafka消息发送使用DTO包装（ControlCommandDTO等）
- [x] 发送端使用DTO.model_dump_json()序列化
- [x] 接收端使用DTO(**data)反序列化
- [x] 使用DTO.Commands常量类定义命令/事件类型
- [x] 使用DTO.is_xxx()方法进行类型判断

## Project Structure

### Documentation (this feature)

```text
specs/001-web-ui-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
├── architecture.md      # 详细架构设计（前端组件、Layout、API封装）
├── spec.md              # Feature specification
└── checklists/          # Quality checklists
```

### Source Code (repository root)

```text
ginkgo/
├── apiserver/                      # API Server (独立项目)
│   ├── main.py                     # FastAPI应用入口
│   ├── api/                        # API路由模块
│   │   ├── __init__.py
│   │   ├── auth.py                 # 认证接口
│   │   ├── dashboard.py            # 仪表盘接口
│   │   ├── portfolio.py            # Portfolio接口
│   │   ├── backtest.py             # 回测接口
│   │   ├── components.py           # 组件管理接口
│   │   ├── data.py                 # 数据管理接口
│   │   ├── notifications.py        # 通知接口
│   │   ├── arena.py                # 竞技场接口
│   │   └── websocket.py            # WebSocket处理
│   ├── models/                     # Pydantic DTOs
│   │   ├── __init__.py
│   │   ├── common.py               # 通用模型
│   │   ├── portfolio.py            # Portfolio相关DTO
│   │   ├── backtest.py             # 回测相关DTO
│   │   ├── component.py            # 组件相关DTO
│   │   └── arena.py                # 竞技场相关DTO
│   ├── services/                   # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── portfolio_service.py    # Portfolio业务逻辑
│   │   ├── backtest_service.py     # 回测业务逻辑
│   │   ├── component_service.py    # 组件管理业务逻辑
│   │   └── arena_service.py        # 竞技场业务逻辑
│   ├── middleware/                 # 中间件
│   │   ├── __init__.py
│   │   ├── auth.py                 # 认证中间件
│   │   ├── error_handler.py        # 错误处理中间件
│   │   └── rate_limit.py           # 限流中间件
│   ├── core/                       # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py               # 配置管理
│   │   └── security.py             # 安全配置
│   ├── websocket/                  # WebSocket处理
│   │   ├── __init__.py
│   │   ├── manager.py              # WebSocket连接管理
│   │   └── handlers/               # 消息处理器
│   │       ├── portfolio_handler.py
│   │       └── signal_handler.py
│   └── requirements.txt            # Python依赖
│
├── web-ui/                         # Web前端 (独立项目)
│   ├── src/
│   │   ├── main.ts                 # 应用入口
│   │   ├── App.vue                # 根组件
│   │   ├── layouts/                # 布局组件
│   │   │   ├── DashboardLayout.vue
│   │   │   ├── BacktestLayout.vue
│   │   │   ├── ComponentLayout.vue
│   │   │   ├── SettingsLayout.vue
│   │   │   └── EmptyLayout.vue
│   │   ├── views/                  # 页面组件
│   │   │   ├── Dashboard/
│   │   │   │   └── index.vue       # 首页（竞技场+信号流+资讯）
│   │   │   ├── Portfolio/
│   │   │   ├── Backtest/
│   │   │   ├── Components/
│   │   │   ├── Data/
│   │   │   └── Settings/
│   │   ├── components/            # 通用组件
│   │   │   ├── base/               # 基础组件
│   │   │   │   ├── DataTable.vue
│   │   │   │   ├── FilterBar.vue
│   │   │   │   ├── ActionBar.vue
│   │   │   │   └── StatCard.vue
│   │   │   ├── charts/             # 图表组件
│   │   │   │   ├── KLineChart.vue
│   │   │   │   ├── NetValueChart.vue
│   │   │   │   ├── PnLChart.vue
│   │   │   │   └── PositionPieChart.vue
│   │   │   ├── arena/              # 竞技场组件
│   │   │   │   ├── ArenaRanking.vue
│   │   │   │   ├── SignalStream.vue
│   │   │   │   ├── NewsFeed.vue
│   │   │   │   └── MyStats.vue
│   │   │   ├── forms/              # 表单组件
│   │   │   └── editors/            # 编辑器组件
│   │   │       ├── MonacoEditor.vue
│   │   │       └── NodeGraphEditor.vue
│   │   ├── composables/           # 组合式函数
│   │   │   ├── useTable.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── usePagination.ts
│   │   ├── stores/                # Pinia状态管理
│   │   ├── api/                   # API调用封装
│   │   │   ├── index.ts
│   │   │   ├── request.ts
│   │   │   └── modules/
│   │   │       ├── stockinfo.ts
│   │   │       ├── bars.ts
│   │   │       ├── portfolio.ts
│   │   │       ├── backtest.ts
│   │   │       ├── components.ts
│   │   │       ├── arena.ts
│   │   │       └── notifications.ts
│   │   ├── config/                # 配置文件
│   │   │   └── tailwind.config.js
│   │   ├── styles/                # 样式文件
│   │   │   └── main.css
│   │   ├── types/                 # TypeScript类型
│   │   └── utils/                 # 工具函数
│   ├── public/                    # 静态资源
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── src/                            # Ginkgo核心库(已存在)
│   └── ginkgo/
│       ├── data/
│       ├── trading/
│       ├── notifier/
│       └── ...
│
└── .conf/                          # 配置和Docker文件统一存放
    ├── Dockerfile.api-server       # API Server容器
    ├── Dockerfile.dataworker       # Data Worker容器(已存在)
    ├── docker-compose.yml          # 服务编排
    └── .env                        # 环境变量
```

**Structure Decision**: 采用前后端分离的多项目结构，API Server作为独立进程通过ServiceHub访问Ginkgo核心服务，Web UI作为独立前端项目通过API与后端交互。

## Complexity Tracking

> No constitution violations - standard event-driven architecture with service container pattern.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 多项目结构 (API Server + Web UI) | API Server服务于多种客户端（Web、移动端、第三方），需要独立部署和扩展 | 单体应用会导致前端与后端紧耦合，无法独立扩展和部署 |
| FastAPI + Vue 3 技术栈 | 需要现代化的异步框架和响应式前端，支持实时数据推送 | 传统Flask + jQuery无法满足WebSocket实时推送和组件化开发需求 |

## Phase 0: Research & Technology Decisions

### Research Tasks

1. **FastAPI最佳实践调研**
   - 目标: 确定FastAPI项目结构、依赖注入模式、WebSocket实现
   - 输出: FastAPI项目结构建议、中间件使用指南

2. **Vue 3 + Vite + Pinia最佳实践**
   - 目标: 确定前端项目结构、状态管理模式、路由方案
   - 输出: Vue 3项目结构建议、Pinia store设计模式

3. **TailwindCSS + Ant Design Vue集成方案**
   - 目标: 确定TailwindCSS配置规范、Ant Design Vue组件定制方案
   - 输出: TailwindCSS配置文件、主题定制方案

4. **Lightweight Charts集成方案**
   - 目标: 确定K线图表组件封装方式、实时数据更新方案
   - 输出: K线图表组件设计、数据更新接口设计

5. **WebSocket实时推送架构**
   - 目标: 确定WebSocket连接管理、消息广播、断线重连机制
   - 输出: WebSocket架构设计、连接管理器设计

### Technology Decisions

| 技术选型 | 决策 | 理由 | 备选方案 |
|---------|------|------|---------|
| 后端框架 | FastAPI | 现代异步框架、自动OpenAPI文档、原生WebSocket支持 | Flask, Django |
| 前端框架 | Vue 3 (Composition API) | 响应式设计、组件化开发、优秀生态 | React, Svelte |
| 构建工具 | Vite | 快速热更新、生产优化 | Webpack, esbuild |
| UI组件库 | Ant Design Vue | 丰富的企业级组件、Vue 3支持 | Element Plus, Naive UI |
| CSS框架 | TailwindCSS | 原子化CSS、无运行时CSS、高度可定制 | styled-components, Sass |
| 状态管理 | Pinia | Vue 3官方推荐、轻量级、TypeScript支持 | Vuex, Redux |
| K线图表 | Lightweight Charts | TradingView开源、专业金融图表、高性能 | ECharts K线图 |
| 统计图表 | ECharts | 功能全面、国内文档完善 | Chart.js, D3.js |
| 代码编辑器 | Monaco Editor | VS Code同款、Python语法高亮 | CodeMirror, Ace |
| WebSocket库 | Socket.IO (后端) / native WebSocket (前端) | 成熟稳定、自动重连 | SockJS, ws |

*详见 `research.md`*

## Phase 1: Design & Contracts

### Data Model Design

详见 `data-model.md`，包含以下实体：

#### 核心实体
- **User**: 用户实体（单用户场景）
- **BacktestJob**: 回测任务
- **Portfolio**: 投资组合（含mode字段: Backtest/Paper/Live）
- **Component**: 回测组件
- **RiskAlert**: 风控警报

#### 实体关系
```
User (1) ←→ (N) BacktestJob
Portfolio (1) ←→ (N) Strategy
Portfolio (1) ←→ (1) RiskConfig
Portfolio (1) ←→ (N) RiskAlert
Component (N) ←→ (1) BacktestJob
```

### API Contracts

详见 `contracts/` 目录下的OpenAPI规范：

#### REST API接口分组
- `POST /api/auth/login` - 用户认证
- `GET /api/dashboard/stats` - 仪表盘统计数据
- `GET /api/portfolio` - Portfolio列表
- `POST /api/backtest` - 创建回测任务
- `GET/POST/PUT/DELETE /api/components` - 组件管理
- `GET /api/data/stockinfo` - 股票信息查询
- `GET /api/arena/portfolios` - 竞技场Portfolio列表
- `POST /api/arena/comparison` - Portfolio对比数据

#### WebSocket接口
- `ws://{host}/ws/portfolio` - Portfolio实时数据推送
- `ws://{host}/ws/signals` - 信号实时推送
- `ws://{host}/ws/system` - 系统状态推送

### Quick Start Guide

详见 `quickstart.md`，包含：

#### 开发环境设置
```bash
# 1. 后端开发
cd apiserver
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# 2. 前端开发（用户手动执行）
cd web-ui
pnpm install
pnpm dev
```

#### Docker部署
```bash
cd .conf
docker-compose up -d
```

## Phase 2: Task Breakdown

*Note: 详细任务列表将由 `/speckit.tasks` 命令生成*

### 核心任务组

#### 任务组1: API Server基础框架 (P1)
- FastAPI项目初始化
- 配置管理和环境变量加载
- 认证中间件和JWT实现
- 错误处理中间件
- 请求限流中间件
- API文档自动生成（OpenAPI）

#### 任务组2: 核心API接口 (P1)
- 认证接口（登录、Token刷新）
- 仪表盘接口（统计数据、实时状态）
- Portfolio接口（CRUD、状态查询、详情）
- 回测接口（创建、启动、停止、查询、结果）
- 组件接口（CRUD、代码验证、版本历史）
- 数据管理接口（股票信息、K线、Tick）
- 竞技场接口（Portfolio列表、对比数据）

#### 任务组3: WebSocket实时推送 (P1)
- WebSocket连接管理器
- Portfolio数据推送处理器
- 信号推送处理器
- 系统状态推送处理器
- 断线重连机制
- 消息广播优化

#### 任务组4: Web UI基础框架 (P1)
- Vue 3 + Vite项目初始化
- TailwindCSS配置
- Ant Design Vue集成
- 路由配置（Vue Router）
- 状态管理（Pinia）
- API封装层（axios interceptors）
- TypeScript类型定义

#### 任务组5: 核心页面组件 (P1)
- 首页（竞技场+信号流+资讯+我的指标）
- Portfolio详情页
- 回测配置和结果页
- 组件管理页
- 数据管理页
- 系统设置页

#### 任务组6: 图表组件 (P1)
- K线图表组件（Lightweight Charts）
- 净值曲线组件（ECharts）
- 盈亏分析组件（ECharts）
- 持仓分布组件（ECharts）
- 技术指标组件（ECharts）

#### 任务组7: 通用组件 (P1)
- DataTable（配置驱动数据表格）
- FilterBar（配置驱动筛选栏）
- ActionBar（操作栏）
- StatCard（统计卡片）
- MonacoEditor（代码编辑器）
- NodeGraphEditor（节点图编辑器）

#### 任务组8: 测试和文档 (P1)
- API单元测试
- WebSocket集成测试
- 前端组件测试
- API文档生成
- 用户手册编写

---

**Next Step**: Run `/speckit.tasks` to generate detailed task breakdown.
