# Ginkgo Web UI 功能规格书

> 版本: 0.8.1 · 更新日期: 2026-04-18

## 1. 系统概览

### 1.1 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | Vue 3 (Composition API + `<script setup>`) |
| 构建 | Vite |
| 状态管理 | Pinia |
| UI 框架 | Ant Design Vue + shadcn-vue (双 UI 库并存) |
| 样式 | TailwindCSS |
| 图表 | ECharts + Lightweight Charts (TradingView) |
| 代码编辑 | Monaco Editor (vue-monaco-editor) |
| 节点编辑 | 自研 Node Graph Editor |
| HTTP | Axios |
| 实时通信 | WebSocket + SSE (Server-Sent Events) |
| 路由 | Vue Router 4 (HTML5 History Mode) |
| 类型系统 | TypeScript |

### 1.2 架构分层

```
┌─────────────────────────────────────────────────┐
│  Views / Pages (.vue)                           │
├─────────────────────────────────────────────────┤
│  Composables (useXxx)     │  Components         │
├─────────────────────────────────────────────────┤
│  Pinia Stores (useXxxStore)                     │
├─────────────────────────────────────────────────┤
│  API Modules (api/modules/*)                    │
├─────────────────────────────────────────────────┤
│  HTTP Client (api/request.ts) — Axios + JWT     │
└─────────────────────────────────────────────────┘
```

- **HTTP 层**: Axios 实例，自动注入 Bearer Token，401 自动跳转登录
- **API 模块**: 按业务域拆分（backtest、portfolio、live、system 等），每个模块导出类型化的请求方法
- **Store**: Pinia Composition API 风格，管理领域状态、分页、WebSocket 实时更新
- **Composable**: 可复用逻辑（加载状态、错误处理、分页、WebSocket、可取消请求等）
- **Component**: 页面组件 + 公共组件 + 图表组件 + Node Graph 编辑器

### 1.3 全局布局

App.vue 实现侧边栏 + 顶栏 + 内容区布局：

- **侧边栏**: 可折叠（220px / 64px），Logo + 层级菜单 + 子菜单展开 + 路由高亮
- **顶栏** (64px): 折叠按钮 + 面包屑 + 通知铃铛（带未读数）+ 用户下拉菜单（显示名、系统设置、退出）
- **内容区**: `<router-view />`，部分页面全屏模式（无 padding）
- **登录/404 页**: 全屏渲染，无侧边栏

主题色：深色 UI（`#0a0a0f` 背景，`#1890ff` 强调色）

### 1.4 认证机制

| 环节 | 实现 |
|------|------|
| 登录 | `POST /api/v1/auth/login` → JWT access_token |
| Token 存储 | `localStorage['access_token']` |
| 用户信息 | `localStorage['user_info']` |
| 请求鉴权 | Axios 拦截器自动注入 `Authorization: Bearer <token>` |
| 路由守卫 | `router.beforeEach` 检查 `isAuthenticated()` |
| 401 处理 | 响应拦截器清除 token 并跳转 `/login` |
| 角色 | `isAdmin` 计算属性控制管理功能可见性 |

---

## 2. 导航结构

### 2.1 侧边栏菜单

| 分组 | 图标 | 菜单项 | 路由 | 说明 |
|------|------|--------|------|------|
| — | LayoutDashboard | 总览 | `/dashboard` | 系统概览 |
| — | Wallet | 组合管理 | `/portfolio` | 投资组合 CRUD |
| **策略回测** | Rocket | 回测列表 | `/backtest` | 回测任务管理 |
| | | 回测对比 | `/backtest/compare` | 多任务对比 |
| **样本验证** | FlaskConical | 滚动前推 | `/validation/walkforward` | Walk Forward 验证 |
| | | 蒙特卡洛 | `/validation/montecarlo` | 随机模拟 |
| | | 敏感性分析 | `/validation/sensitivity` | 参数敏感性 |
| **模拟盘** | TrendingUp | 模拟交易 | `/paper` | Paper Trading 监控 |
| | | 模拟订单 | `/paper/orders` | Paper Trading 订单 |
| **实盘交易** | Zap | 实盘交易 | `/live` | 实盘监控 |
| | | 实盘订单 | `/live/orders` | 订单管理 |
| | | 实盘持仓 | `/live/positions` | 持仓管理 |
| | | 行情数据 | `/live/market` | 行情订阅 |
| | | 账号配置 | `/live/account-config` | 交易所 API 凭证 |
| | | 账号信息 | `/live/account-info` | 余额与持仓 |
| | | Broker 管理 | `/live/broker-management` | Broker 实例控制 |
| | | 交易历史 | `/live/trade-history` | 历史成交 |
| | | 交易控制 | `/live/trading-control` | 交易启停控制台 |
| — — — | | | | |
| **因子研究** | FileSearch | IC 分析 | `/research/ic` | 信息系数 |
| | | 因子分层 | `/research/layering` | 分层回测 |
| | | 因子正交化 | `/research/orthogonal` | 去相关性 |
| | | 因子对比 | `/research/comparison` | 多因子比较 |
| | | 因子衰减 | `/research/decay` | 信号衰减分析 |
| **参数优化** | BarChart3 | 网格搜索 | `/optimization/grid` | 穷举搜索 |
| | | 遗传优化 | `/optimization/genetic` | 进化算法 |
| | | 贝叶斯优化 | `/optimization/bayesian` | 概率模型搜索 |
| — — — | | | | |
| **组件管理** | Code2 | 策略 | `/components/strategies` | 策略文件编辑 |
| | | 风控 | `/components/risks` | 风控文件编辑 |
| | | 仓位 | `/components/sizers` | 仓位文件编辑 |
| | | 选择器 | `/components/selectors` | 选择器文件编辑 |
| | | 分析器 | `/components/analyzers` | 分析器文件编辑 |
| | | 处理器 | `/components/handlers` | 处理器文件编辑 |
| **数据管理** | Database | 数据总览 | `/data` | 数据统计 |
| | | 股票列表 | `/data/stocks` | 股票信息 |
| | | K线数据 | `/data/bars` | K线查看 |
| | | 数据同步 | `/data/sync` | 同步命令 |
| **系统管理** | Wrench | 系统状态 | `/system/status` | 健康监控 |
| | | Worker 管理 | `/system/workers` | Worker 控制 |
| | | API 密钥 | `/system/api-keys` | 密钥 CRUD |
| | | 用户管理 | `/system/users` | 用户 CRUD |
| | | 用户组 | `/system/groups` | 组权限 |
| | | 通知管理 | `/system/notifications` | 通知模板 |
| | | 告警中心 | `/system/alerts` | 告警管理 |

---

## 3. 功能模块

### 3.1 认证模块

#### 登录页 `/login`

| 属性 | 值 |
|------|-----|
| 路由 | `/login` (requiresAuth: false) |
| 文件 | `views/auth/Login.vue` |

**功能描述**: 赛博朋克风格登录页，含动画终端启动日志、股票代码滚动条、粒子动画。用户名/密码表单，密码可切换明文显示。

**交互流程**:
1. 用户输入用户名 + 密码
2. 点击登录 → `authStore.login()`
3. 成功 → 跳转 `/dashboard`
4. 失败 → Toast 提示错误信息

**API 端点**:
- `POST /api/v1/auth/login` — 登录
- `GET /api/v1/auth/verify` — Token 验证
- `GET /api/v1/auth/me` — 获取当前用户

---

### 3.2 仪表盘 `/dashboard`

| 属性 | 值 |
|------|-----|
| 路由 | `/dashboard` |
| 文件 | `views/dashboard/Dashboard.vue` |
| Store | `useDashboardStore` |

**功能描述**: 系统总览页，展示关键统计指标和四阶段流程卡片。

**页面结构**:
- **统计卡片** (4 个): 运行中组合数、今日回测数、活跃 Worker、系统状态
- **四阶段流程卡片**:
  - 策略回测 (Stage 1): 已完成数、最佳收益率
  - 样本验证 (Stage 2): 待验证数、已通过数
  - 模拟盘 (Stage 3): 运行中数、累计收益
  - 实盘交易 (Stage 4): 运行中数、今日盈亏
- **最近活动** (占位)

**交互**: 每个阶段卡片有导航按钮，点击跳转对应模块

**开发状态**: 部分实现，统计数据暂为硬编码

---

### 3.3 组合管理

#### 3.3.1 组合列表 `/portfolio`

| 属性 | 值 |
|------|-----|
| 路由 | `/portfolio` |
| 文件 | `views/portfolio/PortfolioList.vue` |
| Store | `usePortfolioStore` |

**功能描述**: 投资组合 CRUD，支持搜索、按模式筛选、创建/删除。

**页面结构**:
- 搜索输入框 (防抖)
- 模式筛选 (全部/回测/模拟/实盘)
- 统计卡片 (总数、运行中、平均净值、总资产)
- 组合卡片网格: 名称、模式标签、描述、指标、状态标签、日期
- 每张卡片下拉菜单 (查看详情、删除)
- 无限滚动 (IntersectionObserver)

**交互流程**:
1. 点击"创建组合" → 弹出 PortfolioFormEditor 模态框
2. 填写名称/初始资金/模式/组件 → 保存
3. 点击卡片 → 跳转详情页
4. 下拉"删除" → 确认弹窗 → 删除

**API 端点**:
- `GET /api/v1/portfolio` — 列表（分页）
- `POST /api/v1/portfolio` — 创建
- `DELETE /api/v1/portfolio/:uuid` — 删除
- `GET /api/v1/portfolio/stats` — 统计

#### 3.3.2 组合详情 `/portfolio/:id`

| 属性 | 值 |
|------|-----|
| 路由 | `/portfolio/:id` |
| 文件 | `views/portfolio/PortfolioDetail.vue` |
| Store | `usePortfolioStore` |

**功能描述**: 单个组合的完整视图，含统计、组件配置、回测任务、净值曲线、持仓、策略表现、风控告警。

**页面结构**:
- 顶部操作栏: 启动/停止按钮、编辑按钮（跳转图编辑器）、配置弹窗
- 统计行: 平均净值、回测数、初始资金、平均盈亏
- 组件配置展示: 选择器、仓位、策略（含权重）、风控、分析器
- 回测任务表格: 名称、状态、盈亏、订单数、创建时间
- 净值曲线图 (TradingView 集成规划中)
- 持仓表格: 代码、数量、成本价、现价、市值、盈亏%
- 策略表现网格: 名称、类型、权重、收益率、Sharpe、最大回撤
- 风控告警列表: 级别、类型、处理状态、消息、时间戳

**API 端点**:
- `GET /api/v1/portfolio/:uuid` — 详情
- `POST /api/v1/portfolio/:uuid/start` — 启动
- `POST /api/v1/portfolio/:uuid/stop` — 停止
- `PUT /api/v1/portfolio/:uuid` — 更新配置

#### 3.3.3 组合编辑器 `/portfolio/:id/edit`

| 属性 | 值 |
|------|-----|
| 路由 | `/portfolio/:id/edit` |
| 文件 | `views/portfolio/PortfolioFormEditor.vue` |

**功能描述**: 双面板组合编辑器。左面板基本信息 + 组件选择器；右面板已配置组件列表。

**页面结构**:
- 左面板: 名称、初始资金（格式化显示）、模式选择（BACKTEST/PAPER/LIVE）、基准、描述
- 左面板: 组件类型标签页（选择器/仓位/策略/风控/分析器）+ 下拉选择器
- 右面板: 已配置组件列表，每个组件含版本选择、参数编辑（数字/布尔/选择/文本输入）、权重输入（策略）、删除按钮
- 底部: 保存/取消

**支持模式**: 模态框模式（嵌入 PortfolioList）和独立页面模式

**参数类型**: INT / FLOAT / STRING / BOOL / LIST / DICT

---

### 3.4 策略回测

#### 3.4.1 回测列表 `/backtest`

| 属性 | 值 |
|------|-----|
| 路由 | `/backtest` |
| 文件 | `views/stage1/BacktestList.vue` |
| Store | `useBacktestStore` |

**功能描述**: 回测任务全生命周期管理，支持批量操作、实时进度更新。

**页面结构**:
- 顶部: 刷新 + 创建按钮
- 批量操作栏: 选中时显示（批量启动/停止/取消）
- 统计卡片: 总数、已完成、运行中、失败
- 状态筛选: 全部/待调度/排队中/运行中/已完成/已停止/失败
- 搜索框
- 数据表格 (含复选框): 任务名+UUID、状态（含进度条）、总盈亏、订单数、信号数、创建时间、操作按钮（启动/停止/取消/查看详情）
- 分页: 10/20/50 条/页
- 创建弹窗: 名称、组合选择器、起止日期、初始资金
- 净值曲线弹窗

**实时更新**: WebSocket 推送进度，断连时自动降级为轮询（10s 间隔）

**权限控制**: `canStartTask`、`canStopTask`、`canCancelTask`、`canDeleteTask` 方法

**API 端点**:
- `GET /api/v1/backtest` — 列表（分页）
- `POST /api/v1/backtest` — 创建
- `POST /api/v1/backtest/:uuid/start` — 启动
- `POST /api/v1/backtest/:uuid/stop` — 停止
- `POST /api/v1/backtest/:uuid/cancel` — 取消
- `DELETE /api/v1/backtest/:uuid` — 删除

#### 3.4.2 回测详情 `/backtest/:id`

| 属性 | 值 |
|------|-----|
| 路由 | `/backtest/:id` |
| 文件 | `views/stage1/BacktestDetail.vue` |
| Store | `useBacktestStore` |

**功能描述**: 回测结果完整查看器，标签页式布局。

**标签页**:
- **概览**:
  - 基本信息 (UUID、状态、组合、时长、时间)
  - 进度条 (运行中/待调度)
  - 配置快照 (名称、初始资金、日期范围、组件列表)
  - 回测指标 (最终净值、总盈亏、年化收益、Sharpe、最大回撤、胜率)
  - 执行统计 (订单、信号、持仓、事件、平均耗时、峰值内存)
  - 分析器表格 (名称、最新值、记录数、变化趋势)
  - 净值曲线图 (策略 + 基准)
  - 错误信息
  - 环境信息 JSON
- **分析器**: AnalyzerPanel 组件
- **交易记录**: TradeRecordsPanel 组件
- **日志**: 占位

**操作**: 重新运行、停止、删除（权限控制）

**API 端点**:
- `GET /api/v1/backtest/:uuid` — 详情
- `GET /api/v1/backtest/:uuid/netvalue` — 净值数据
- `GET /api/v1/backtest/:uuid/analyzers` — 分析器数据
- `GET /api/v1/backtest/:uuid/signals` — 信号
- `GET /api/v1/backtest/:uuid/orders` — 订单
- `GET /api/v1/backtest/:uuid/positions` — 持仓

#### 3.4.3 回测对比 `/backtest/compare`

| 属性 | 值 |
|------|-----|
| 路由 | `/backtest/compare` |
| 文件 | `views/stage1/BacktestCompare.vue` |

**功能描述**: 选择 2-5 个已完成回测任务进行对比。

**页面结构**:
- 勾选表格 (任务 ID、名称、状态、总收益率、Sharpe、最大回撤)
- "开始对比"按钮
- 指标对比表 (最优值高亮)
- 净值曲线叠加对比

**API 端点**:
- `GET /api/v1/backtest/compare` — 对比数据

---

### 3.5 样本验证

#### 3.5.1 滚动前推验证 `/validation/walkforward`

| 属性 | 值 |
|------|-----|
| 路由 | `/validation/walkforward` |
| 文件 | `views/stage2/WalkForward.vue` |

**功能描述**: 时间序列交叉验证，评估策略样本外表现。

**配置项**: 回测任务选择器、折数、训练比例（滑块）、窗口类型（扩展/滚动）

**结果指标**: 平均训练/测试收益、退化度、稳定性评分、分折详情表

#### 3.5.2 蒙特卡洛模拟 `/validation/montecarlo`

| 属性 | 值 |
|------|-----|
| 路由 | `/validation/montecarlo` |
| 文件 | `views/stage2/MonteCarlo.vue` |

**功能描述**: 随机模拟评估风险分布和极端损失概率。

**配置项**: 回测任务选择器、模拟次数、置信水平

**结果指标**: VaR、CVaR、期望收益、损失概率、最大/最小收益、标准差、偏度

#### 3.5.3 敏感性分析 `/validation/sensitivity`

| 属性 | 值 |
|------|-----|
| 路由 | `/validation/sensitivity` |
| 文件 | `views/stage2/Sensitivity.vue` |

**功能描述**: 评估策略对参数变化的鲁棒性。

**配置项**: 回测任务选择器、参数名、参数值（CSV 输入）

**结果指标**: 敏感性评分、最优值、最优收益、数据点表（最优值标记）

**API 端点** (三个验证共用):
- `POST /v1/validation/walkforward`
- `POST /v1/validation/montecarlo`
- `POST /v1/validation/sensitivity`

---

### 3.6 模拟盘

#### 3.6.1 模拟交易 `/paper`

| 属性 | 值 |
|------|-----|
| 路由 | `/paper` |
| 文件 | `views/stage3/PaperTrading.vue` |

**功能描述**: Paper Trading 监控面板。

**页面结构**: 启动/停止/刷新/设置按钮、统计卡片（今日盈亏、持仓数、可用资金、运行天数）、持仓表格、订单表格（占位）

#### 3.6.2 模拟订单 `/paper/orders`

| 属性 | 值 |
|------|-----|
| 路由 | `/paper/orders` |
| 文件 | `views/stage3/PaperTradingOrders.vue` |

**功能描述**: 模拟盘历史订单查询。

**筛选**: 状态（待成交/已成交/已取消/部分成交）、股票代码、日期范围

**订单表格**: 时间、代码、方向、数量、价格、状态等

**API 端点**:
- `GET /v1/paper-trading/accounts` — 账号列表
- `POST /v1/paper-trading/:id/start` — 启动
- `POST /v1/paper-trading/:id/stop` — 停止
- `GET /v1/paper-trading/:id/positions` — 持仓
- `GET /v1/paper-trading/:id/orders` — 订单
- `DELETE /v1/paper-trading/:id/orders/:oid` — 撤单

---

### 3.7 实盘交易

#### 3.7.1 实盘监控 `/live`

| 属性 | 值 |
|------|-----|
| 路由 | `/live` |
| 文件 | `views/stage4/LiveTrading.vue` |

**功能描述**: 实盘实时监控面板。

**页面结构**: 紧急停止按钮、刷新、统计卡片（总资产、今日盈亏、持仓市值、可用资金）、持仓详情表、今日订单表

#### 3.7.2 实盘订单 `/live/orders`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/orders` |
| 文件 | `views/stage4/LiveOrders.vue` |

**功能描述**: 实盘订单管理。筛选条件同模拟订单。

#### 3.7.3 实盘持仓 `/live/positions`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/positions` |
| 文件 | `views/stage4/LivePositions.vue` |

**功能描述**: 实盘持仓管理。

**页面结构**: 股票代码搜索、统计（持仓数、总市值、总盈亏、总手续费）、持仓数据表格

#### 3.7.4 行情数据 `/live/market`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/market` (requiresAuth: false) |
| 文件 | `views/stage4/MarketData.vue` |

**功能描述**: 交易对订阅管理和实时行情。加密货币方向，WebSocket 连接。

**页面结构**: 刷新交易对、WebSocket 连接/断开开关、统计（交易对数、已订阅、API 状态、实时数据状态）、交易对列表含报价货币筛选、订阅管理

#### 3.7.5 账号配置 `/live/account-config`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/account-config` |
| 文件 | `views/live/AccountConfig.vue` |

**功能描述**: 管理交易所 API 凭证。

**页面结构**: 添加账号按钮、账号表格（名称、交易所、状态、最后验证时间、操作）、添加/编辑/删除账号弹窗

**API 端点**:
- `GET /api/v1/accounts` — 账号列表
- `POST /api/v1/accounts` — 创建账号
- `PUT /api/v1/accounts/:uuid` — 更新
- `DELETE /api/v1/accounts/:uuid` — 删除
- `POST /api/v1/accounts/:uuid/validate` — 验证连接
- `PUT /api/v1/accounts/:uuid/status` — 启用/禁用

#### 3.7.6 账号信息 `/live/account-info`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/account-info` |
| 文件 | `views/live/AccountInfo.vue` |

**功能描述**: 实盘账户余额和持仓实时展示。

**页面结构**: 按账号刷新、余额展示（总权益、可用、冻结、分币种明细）、持仓展示（币对、方向、数量、均价、现价、未实现盈亏、保证金）

**API 端点**:
- `GET /api/v1/accounts/:uuid/balance` — 余额
- `GET /api/v1/accounts/:uuid/positions` — 持仓

#### 3.7.7 Broker 管理 `/live/broker-management`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/broker-management` |
| 文件 | `views/live/BrokerManagement.vue` |

**功能描述**: 管理 Broker 实例（连接组合与实盘账号的桥梁）。

**Broker 状态机**: `uninitialized → initializing → running → paused → stopped`，含 `error`、`recovering` 异常状态

**操作**: 启动、暂停、停止、重启

#### 3.7.8 交易历史 `/live/trade-history`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/trade-history` |
| 文件 | `views/live/TradeHistory.vue` |

**功能描述**: 历史成交记录查询。

**页面结构**: 日期范围筛选、统计（总成交数、买入/卖出数、总数量/金额/手续费、交易标的数）、成交记录表格、导出功能、详情弹窗

#### 3.7.9 交易控制 `/live/trading-control`

| 属性 | 值 |
|------|-----|
| 路由 | `/live/trading-control` |
| 文件 | `views/live/TradingControl.vue` |

**功能描述**: 实盘交易控制面板，管理 Broker 实例的启停。

**页面结构**: Broker 实例列表含状态、订单统计（已提交/已成交/已取消/已拒绝）、心跳监控、启动/停止/暂停按钮含确认弹窗

**API 端点** (实盘交易共用):
- `GET /v1/live-trading/accounts` — 账号列表
- `POST /v1/live-trading/accounts/:id/connect` — 连接
- `POST /v1/live-trading/accounts/:id/disconnect` — 断开
- `GET /v1/live-trading/:id/positions` — 持仓
- `GET /v1/live-trading/:id/active-orders` — 活跃订单
- `DELETE /v1/live-trading/:id/orders/:oid` — 撤单
- `GET /v1/live-trading/:id/capital` — 资金信息
- `GET /v1/live-trading/:id/risk/status` — 风控状态
- `POST /v1/live-trading/:id/risk/circuit-breaker` — 熔断

---

### 3.8 因子研究

所有因子研究页面遵循统一模式：**配置表单 → 提交 → 结果展示**。

#### 3.8.1 IC 分析 `/research/ic`

**功能**: 信息系数分析，评估因子预测能力。
**配置**: 回测任务选择器、收益周期（1/5/10/20 天）
**结果**: IC 均值、IC 标准差、ICIR、正值占比、t 统计量

#### 3.8.2 因子分层 `/research/layering`

**功能**: 按因子值分组验证选股效果。
**配置**: 回测任务选择器、分组数（3-10）
**结果**: 多空收益、最优组、分组收益表

#### 3.8.3 因子正交化 `/research/orthogonal`

**功能**: 使用 Gram-Schmidt 或 PCA 去除因子间相关性。
**配置**: 回测任务选择器、方法选择（Gram-Schmidt / PCA）
**结果**: 原始 vs 正交化平均相关矩阵对比

#### 3.8.4 因子对比 `/research/comparison`

**功能**: 多因子交叉比较（IC、ICIR、换手率维度）。
**配置**: 回测任务选择器
**结果**: 最优因子、综合评分、因子对比表

#### 3.8.5 因子衰减 `/research/decay`

**功能**: 衡量因子信号有效性随时间的衰减。
**配置**: 回测任务选择器、最大周期（5-60 天）
**结果**: 半衰期、最优调仓频率、IC 衰减表

**API 端点**:
- `POST /v1/research/ic`
- `POST /v1/research/layering`
- `POST /v1/research/orthogonalize`
- `POST /v1/research/compare`
- `POST /v1/research/decay`

---

### 3.9 参数优化

所有优化页面遵循统一模式：**策略选择 + 参数配置 → 执行 → 结果展示**。

#### 3.9.1 网格搜索 `/optimization/grid`

**功能**: 穷举参数组合搜索，适合 2-3 个参数。
**配置**: 策略选择器、参数 JSON
**结果**: 总组合数、最优收益、最优 Sharpe、最优参数

#### 3.9.2 遗传优化 `/optimization/genetic`

**功能**: 进化算法参数优化，适合高维空间。
**配置**: 策略选择器、种群大小（10-200）、迭代数（10-500）、变异率（0.01-0.5）
**结果**: 最优适应度、最优参数、迭代进度

#### 3.9.3 贝叶斯优化 `/optimization/bayesian`

**功能**: 概率模型智能参数搜索。
**配置**: 策略选择器、迭代数（10-200）、初始采样点（3-20）
**结果**: 总迭代数、最优得分、收敛信息

**API 端点**:
- `POST /v1/optimization/grid`
- `POST /v1/optimization/genetic`
- `POST /v1/optimization/bayesian`

---

### 3.10 组件管理

#### 3.10.1 组件列表页

六个组件类型共享 `ComponentListPage` 通用组件：

| 类型 | 路由 | file_type |
|------|------|-----------|
| 策略 | `/components/strategies` | 6 |
| 风控 | `/components/risks` | 3 |
| 仓位 | `/components/sizers` | 5 |
| 选择器 | `/components/selectors` | 4 |
| 分析器 | `/components/analyzers` | 1 |
| 处理器 | `/components/handlers` | 8 |

**通用功能**: 搜索、文件列表表格（名称、更新时间、操作：编辑/删除）、分页、创建文件弹窗

#### 3.10.2 组件详情（代码编辑器）

| 属性 | 值 |
|------|-----|
| 路由 | `/components/:type/:id` |
| 文件 | `views/components/ComponentDetail.vue` |

**功能描述**: Python 文件在线编辑器，基于 Monaco Editor。

**页面结构**: 返回按钮、文件信息（名称、类型标签、未保存标记）、重置按钮、保存按钮、全功能代码编辑器（语法高亮）

**API 端点**:
- `GET /api/v1/components/strategies` — 策略列表
- `GET /api/v1/components/selectors` — 选择器列表
- `GET /api/v1/components/risks` — 风控列表
- `GET /api/v1/components/sizers` — 仓位列表
- `GET /api/v1/components/analyzers` — 分析器列表
- `GET /v1/file_list` — 文件列表
- `GET /v1/file/:id` — 文件内容
- `POST /v1/file` — 创建文件
- `POST /v1/update_file` — 更新文件
- `DELETE /v1/file/:id` — 删除文件

---

### 3.11 数据管理

#### 3.11.1 数据总览 `/data`

| 属性 | 值 |
|------|-----|
| 路由 | `/data` |
| 文件 | `views/data/DataOverview.vue` |

**功能描述**: 市场数据统计摘要。

**页面结构**: 刷新按钮、可点击统计卡片（股票总数 → `/data/stocks`、K线条数 → `/data/bars`、同步信息）

#### 3.11.2 股票列表 `/data/stocks`

| 属性 | 值 |
|------|-----|
| 路由 | `/data/stocks` |
| 文件 | `views/data/StockList.vue` |

**功能描述**: 股票信息浏览和搜索。

**页面结构**: 代码/名称搜索、刷新、同步按钮、统计（总数、沪市、深市）、可排序数据表格（代码、名称、交易所、行业、上市日期、状态）

#### 3.11.3 K线数据 `/data/bars`

| 属性 | 值 |
|------|-----|
| 路由 | `/data/bars` |
| 文件 | `views/data/BarData.vue` |

**功能描述**: K线数据查看器，含图表展示。

**配置**: 股票选择器、起止日期、频率（日线/周线/月线）、复权类型（前复权/后复权/不复权）

**展示**: K线蜡烛图

#### 3.11.4 数据同步 `/data/sync`

| 属性 | 值 |
|------|-----|
| 路由 | `/data/sync` |
| 文件 | `views/data/DataSync.vue` |

**功能描述**: 发送数据同步命令和查看同步历史。

**命令表单**: 命令类型（BAR_SNAPSHOT / TICK / STOCKINFO / ADJUSTFACTOR）、股票代码（文本域）、全量同步开关、覆盖开关、发送按钮

**同步历史**: 日志展示

**API 端点**:
- `GET /api/v1/data/stats` — 统计
- `GET /api/v1/data/stockinfo` — 股票信息
- `GET /api/v1/data/bars/:code` — K线数据
- `POST /api/v1/data/sync` — 同步命令
- `GET /api/v1/data/status` — 同步状态

---

### 3.12 系统管理

#### 3.12.1 系统状态 `/system/status`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/status` |
| 文件 | `views/system/SystemStatus.vue` |
| Store | `useSystemStore` |

**功能描述**: 系统健康监控面板。

**页面结构**: 自动刷新开关、手动刷新、6 格统计网格（服务状态、版本、运行时间、CPU、内存、磁盘）、详细系统信息

#### 3.12.2 Worker 管理 `/system/workers`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/workers` |
| 文件 | `views/system/WorkerManagement.vue` |
| **状态** | **占位页面** — "功能开发中" |

#### 3.12.3 API 密钥 `/system/api-keys`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/api-keys` |
| 文件 | `views/system/ApiKeyManagement.vue` |

**功能描述**: API 密钥 CRUD。

**页面结构**: 创建按钮、统计（总数、活跃、已过期、未激活）、密钥表格（名称、前缀、状态等）、创建弹窗

**API 端点**:
- `GET /api/v1/api-keys` — 列表
- `POST /api/v1/api-keys` — 创建
- `GET /api/v1/api-keys/:uuid` — 详情
- `PUT /api/v1/api-keys/:uuid` — 更新
- `DELETE /api/v1/api-keys/:uuid` — 删除
- `POST /api/v1/api-keys/:uuid/reveal` — 揭示密钥
- `POST /api/v1/api-keys/verify` — 验证
- `POST /api/v1/api-keys/check-permission` — 权限检查

#### 3.12.4 用户管理 `/system/users`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/users` |
| 文件 | `views/settings/UserManagement.vue` |

**功能描述**: 管理员用户管理。

**页面结构**: 添加用户按钮、用户名搜索、状态筛选（活跃/禁用）、用户表格（用户名、邮箱、状态、角色、最后登录、操作）、创建/编辑弹窗

**API 端点**:
- `GET /v1/settings/users` — 用户列表
- `POST /v1/settings/users` — 创建
- `PUT /v1/settings/users/:uuid` — 更新
- `DELETE /v1/settings/users/:uuid` — 删除
- `POST /v1/settings/users/:uuid/reset-password` — 重置密码

#### 3.12.5 用户组 `/system/groups`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/groups` |
| 文件 | `views/settings/UserGroupManagement.vue` |

**功能描述**: 用户组和权限管理。

**页面结构**: 添加组按钮、组表格（名称、描述、用户数、权限标签、操作：编辑/权限/删除）、创建/编辑弹窗

**API 端点**:
- `GET /v1/settings/user-groups` — 组列表
- `POST /v1/settings/user-groups` — 创建
- `PUT /v1/settings/user-groups/:uuid` — 更新
- `DELETE /v1/settings/user-groups/:uuid` — 删除
- `GET /v1/settings/user-groups/:uuid/members` — 成员
- `POST /v1/settings/user-groups/:uuid/members` — 添加成员

#### 3.12.6 通知管理 `/system/notifications`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/notifications` |
| 文件 | `views/settings/NotificationManagement.vue` |

**功能描述**: 通知模板和发送历史管理。

**页面结构**: 标签页切换（模板 / 历史）、模板表格（名称、类型标签、启用/禁用开关、操作）、创建模板弹窗

**API 端点**:
- `GET /v1/settings/notifications/templates` — 模板列表
- `POST /v1/settings/notifications/templates` — 创建模板
- `PUT /v1/settings/notifications/templates/:uuid` — 更新
- `DELETE /v1/settings/notifications/templates/:uuid` — 删除
- `POST /v1/settings/notifications/templates/:uuid/test` — 测试发送
- `GET /v1/settings/notifications/history` — 发送历史

#### 3.12.7 告警中心 `/system/alerts`

| 属性 | 值 |
|------|-----|
| 路由 | `/system/alerts` |
| 文件 | `views/system/AlertCenter.vue` |
| **状态** | **占位页面** — "功能开发中" |

---

## 4. 数据层

### 4.1 Pinia Store 清单

| Store | 文件 | 职责 |
|-------|------|------|
| `useAuthStore` | `stores/auth.ts` | 认证状态、JWT、登录/登出、角色判断 |
| `usePortfolioStore` | `stores/portfolio.ts` | 组合 CRUD、生命周期控制、统计、分页 |
| `useBacktestStore` | `stores/backtest.ts` | 回测任务全生命周期、实时进度、批量操作、权限检查 |
| `useSystemStore` | `stores/system.ts` | 系统状态监控、Worker 管理、自动刷新 |
| `useLoadingStore` | `stores/loading.ts` | 全局优先级加载状态 (LOW/NORMAL/HIGH/CRITICAL) |
| `useNodeGraphStore` | `stores/nodeGraph.ts` | 节点图编辑器状态 |
| `useDashboardStore` | `stores/dashboard.ts` | 仪表盘统计 (占位) |

### 4.2 API 模块清单

| 模块 | 文件 | 基础路径 | 端点数 |
|------|------|----------|--------|
| auth | `modules/auth.ts` | `/api/v1/auth/` | 5 |
| portfolio | `modules/portfolio.ts` | `/api/v1/portfolio` | 8 |
| backtest | `modules/backtest.ts` | `/api/v1/backtest` | 13 |
| system | `modules/system.ts` | `/v1/system/` | 10 |
| live | `modules/live.ts` | `/api/v1/accounts` | 8 |
| trading | `modules/trading.ts` | `/v1/paper-trading/` + `/v1/live-trading/` | 18 |
| data | `modules/data.ts` | `/api/v1/data/` | 8 |
| components | `modules/components.ts` | `/api/v1/components/` | 6 |
| file | `modules/file.ts` | `/v1/` | 5 |
| settings | `modules/settings.ts` | `/v1/settings/` | 20+ |
| nodeGraph | `modules/nodeGraph.ts` | `/v1/node-graphs/` | 9 |
| research | `modules/research.ts` | `/v1/research/` | 5 |
| optimization | `modules/optimization.ts` | `/v1/optimization/` | 3 |
| validation | `modules/validation.ts` | `/v1/validation/` | 3 |
| order | `modules/order.ts` | `/api/v1/orders` + `/api/v1/positions` | 4 |
| market | `modules/market.ts` | `/api/v1/market/` | 8 |
| apiKey | `modules/apiKey.ts` | `/api/v1/api-keys/` | 8 |

### 4.3 实时通信

#### WebSocket (`composables/useWebSocket.ts`)

- 单例连接，自动重连（5s 间隔）
- 发布/订阅模式: `subscribe(eventType, handler)`
- 支持通配符 `'*'` 监听所有事件
- 开发环境端口映射: 5173 → 8000
- 端点: `/ws`
- 用途: 回测进度实时推送

#### SSE (`composables/useRealtime.ts`)

- Server-Sent Events 封装
- 接受 `{ url, onMessage, onError }` 配置
- 返回 `{ connect, disconnect, isConnected, data, error }`
- 组件卸载时自动关闭

---

## 5. 公共组件库

### 5.1 通用组件 (`components/common/`)

| 组件 | 用途 |
|------|------|
| `StatusTag` | 状态显示标签（颜色+文本） |
| `StatCard` | 统计指标卡片 |
| `TableActions` | 表格行操作按钮 |
| `ListPageLayout` | 列表页通用布局 |
| `EmptyState` | 空状态占位 |
| `GlobalLoading` | 全页加载指示器 |
| `LoadingOverlay` | 叠加层加载动画 |

### 5.2 图表组件 (`components/charts/`)

| 组件 | 类型 | 用途 |
|------|------|------|
| `BaseChart` | 基类 | ECharts 基础封装 |
| `LineChart` | 折线图 | 通用折线 |
| `AreaChart` | 面积图 | 面积填充 |
| `CandlestickChart` | 蜡烛图 | K线展示 |
| `HistogramChart` | 柱状图 | 分布展示 |
| `NetValueChart` | 净值曲线 | 回测净值+基准 |
| `DrawdownChart` | 回撤图 | 最大回撤可视化 |
| `PnlChart` | 盈亏图 | 盈亏分布 |
| `PositionChart` | 持仓图 | 持仓可视化 |
| `ICIRChart` | ICIR 图 | 因子 ICIR 趋势 |
| `LayeringReturnChart` | 分层收益图 | 分组收益对比 |

### 5.3 Node Graph 编辑器 (`components/node-graph/`)

| 组件 | 用途 |
|------|------|
| `NodeGraphEditor` | 主编辑器容器 |
| `NodeGraphCanvas` | 画布渲染 |
| `NodeComponent` | 单节点渲染 |
| `NodePalette` | 可拖拽节点面板 |
| `NodePropertyPanel` | 属性编辑面板 |
| `NodeCreateMenu` | 节点创建上下文菜单 |
| `GraphValidator` | 验证结果显示 |
| `ConnectionLine` | 连线渲染 |

**Composable**: `useNodeGraph` — 提供 20 步撤销/重做、节点/边 CRUD、验证（引擎+组合节点、连接规则、环路检测）

**节点类型**: `strategy` | `selector` | `sizer` | `risk`

### 5.4 Composable 清单

| Composable | 用途 |
|------------|------|
| `useWebSocket` | 单例 WebSocket 连接管理 |
| `useRealtime` | SSE 连接封装 |
| `useLoading` | 全局加载状态 (Set-based) |
| `useErrorHandler` | 错误捕获和展示 |
| `useFormErrorHandler` | 表单提交错误处理 |
| `useApiError` | HTTP 状态码感知错误处理 |
| `useRequestCancelable` | 可取消的单请求（AbortController） |
| `useMultiRequestCancelable` | 可取消的多请求 |
| `useTable<T>` | 通用表格状态（分页、加载） |
| `useListPage<T, P>` | 完整列表页模式（搜索+分页+筛选） |
| `useCrudStore<T>` | 通用 CRUD Store 工厂 |
| `useNodeGraph` | 节点图编辑操作（撤销/重做/验证） |
| `useComponentList` | 组件列表弹窗状态 |
| `useStatusFormat` | 状态格式化映射 |

---

## 6. 开发状态

### 6.1 已完成 (功能完整、API 已接入)

- 登录认证
- 组合列表 + 详情 + 编辑器
- 回测列表 + 详情 + 创建 + 对比
- 组件管理 (列表 + Monaco 代码编辑器)
- 实盘账号配置、账号信息、Broker 管理、交易控制、交易历史
- 系统状态、API 密钥管理、用户管理、用户组管理、通知管理
- 数据总览、股票列表、K线数据、数据同步

### 6.2 部分实现 (有 UI，部分数据硬编码)

- 仪表盘 (统计数据硬编码)
- 模拟盘监控 (订单表占位)
- 实盘监控 (持仓和订单表占位)

### 6.3 开发中 (UI 已有，后端 API 未完全对接)

- 滚动前推验证
- 蒙特卡洛模拟
- 敏感性分析
- IC 分析、因子分层、因子正交化、因子对比、因子衰减
- 网格搜索、遗传优化、贝叶斯优化

### 6.4 占位页面

- Worker 管理 (`/system/workers`) — "功能开发中"
- 告警中心 (`/system/alerts`) — "功能开发中"

### 6.5 规划中 (代码存在但未注册路由)

- Node Graph 编辑器 (`BacktestGraphEditor.vue`) — 可视化拖拽编辑器，可编译为回测任务
