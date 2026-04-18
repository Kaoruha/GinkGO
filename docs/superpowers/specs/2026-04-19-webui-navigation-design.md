# WebUI 导航架构重设计

**日期:** 2026-04-19
**状态:** Approved
**范围:** 信息架构和导航重构，不含视觉风格变更

## 1. 背景与问题

当前 WebUI 有 13 个顶层菜单、39 个子菜单项，存在以下问题：

- **核心流程断裂** — 回测→验证→模拟→实盘被拆成 4 个独立一级菜单，无流程感
- **实盘交易过重** — 9 个子项混杂了监控、管理、配置
- **缺少层次** — 研究工具、运维工具、核心交易平铺
- **无流程引导** — 新用户不知道从哪开始

## 2. 设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 导航架构 | 极简工作台（6 入口） | 减少认知负担，复杂度下放到页面内 |
| 核心实体 | Portfolio（投资组合） | 全生命周期围绕 Portfolio 展开 |
| 回测归属 | 从属于 Portfolio | 回测必须在 Portfolio 上下文中发起 |
| 交易入口 | 全局监控视图 | 操作在 Portfolio 内，跨组合监控独立入口 |
| 研究入口 | 独立顶层入口 | 因子研究与 Portfolio 流程正交 |
| 管理入口 | 合并为二级 | 低频运维功能降级 |
| 数据入口 | 独立顶层 | 数据查看是高频需求，查看和同步都需便捷访问 |
| 视觉风格 | 保持深色主题，暂不变更 | 先解决架构问题 |
| 功能范围 | 0 个功能删除 | 只重组入口，不删功能 |

## 3. 导航结构

### 3.1 顶层菜单（6 项）

```
📊 工作台    → /dashboard
💼 组合      → /portfolios
🧪 研究      → /research
📡 交易      → /trading
💾 数据      → /data
⚙️ 管理      → /admin
```

不需要折叠子菜单。复杂度通过页面内 Tab、二级路由消化。

### 3.2 工作台（/dashboard）

**定位：** 登录首页，全局一览。

**内容：**
- 指标卡片：组合数、运行中数、总资产、今日盈亏
- 活跃组合列表：每个组合的状态（实盘/模拟/空闲）、关键指标
- 最近活动时间线：回测完成、交易成交、参数变更等事件

**路由：**
- `GET /dashboard` — 工作台首页

### 3.3 组合（/portfolios）

**定位：** 核心工作台，Portfolio 全生命周期管理。

#### 列表页（/portfolios）

- 所有 Portfolio 的卡片或列表视图
- 每项显示：名称、状态标签（实盘/模拟/空闲）、最新净值、收益率
- "新建组合"按钮

#### 详情页（/portfolios/:id）

6 个 Tab，覆盖全生命周期：

| Tab | 路由 | 内容 |
|-----|------|------|
| 概况 | `/portfolios/:id` | 核心指标卡片、净值曲线、最近活动时间线 |
| 回测 | `/portfolios/:id/backtests` | 回测列表、新建回测按钮、回测对比、回测详情（净值/PnL/回撤/分析器）、可视化节点编辑器入口 |
| 验证 | `/portfolios/:id/validation` | 走步验证、蒙特卡洛、敏感性分析（Tab 内子视图切换），选择回测结果做样本外验证 |
| 模拟 | `/portfolios/:id/paper` | 模拟盘监控、订单记录、偏差检测、启动/停止控制 |
| 实盘 | `/portfolios/:id/live` | 实盘监控、订单管理、持仓管理、账户信息、Broker 管理、交易控制、交易历史（Tab 内子视图切换） |
| 组件 | `/portfolios/:id/components` | 策略/选股器/仓位/风控/分析器配置查看与编辑 |

**头部操作栏（始终可见）：**
- 新建回测 → 进入回测创建流程
- 启动模拟 → 从当前 Portfolio 配置启动模拟盘
- 上线实盘 → 从当前 Portfolio 配置启动实盘

**路由：**
- `GET /portfolios` — 组合列表
- `GET /portfolios/create` — 创建组合（FormEditor 或 NodeGraphEditor）
- `GET /portfolios/:id` — 详情-概况
- `GET /portfolios/:id/backtests` — 详情-回测
- `GET /portfolios/:id/backtests/:backtestId` — 回测详情
- `GET /portfolios/:id/backtests/compare` — 回测对比
- `GET /portfolios/:id/validation` — 详情-验证
- `GET /portfolios/:id/paper` — 详情-模拟
- `GET /portfolios/:id/live` — 详情-实盘
- `GET /portfolios/:id/components` — 详情-组件
- `GET /portfolios/:id/edit` — 编辑组合

### 3.4 研究（/research）

**定位：** 独立的因子研究工作台，与 Portfolio 流程正交。

**子视图（Tab 切换）：**

| 子视图 | 路由 | 内容 |
|--------|------|------|
| 因子分析 | `/research/factor` | IC 分析、因子分层、因子正交化、因子比较、因子衰减（二次 Tab 切换） |
| 参数优化 | `/research/optimization` | 网格搜索、遗传算法、贝叶斯优化（二次 Tab 切换） |

**路由：**
- `GET /research` — 研究首页（重定向到因子分析）
- `GET /research/factor` — 因子分析
- `GET /research/factor/ic` — IC 分析
- `GET /research/factor/layering` — 因子分层
- `GET /research/factor/orthogonal` — 因子正交化
- `GET /research/factor/comparison` — 因子比较
- `GET /research/factor/decay` — 因子衰减
- `GET /research/optimization` — 参数优化
- `GET /research/optimization/grid` — 网格搜索
- `GET /research/optimization/genetic` — 遗传算法
- `GET /research/optimization/bayesian` — 贝叶斯优化

### 3.5 交易（/trading）

**定位：** 跨组合的全局交易监控。只做监控和全局视角，操作回到 Portfolio 内完成。

**子视图：**

| 子视图 | 路由 | 内容 |
|--------|------|------|
| 模拟盘 | `/trading/paper` | 所有 Portfolio 的模拟盘状态一览、全局订单流、偏差告警，点击跳转对应 Portfolio |
| 实盘 | `/trading/live` | 所有 Portfolio 的实盘运行状态、全局持仓汇总、风控状态、盈亏汇总、市场数据，点击跳转对应 Portfolio |

**路由：**
- `GET /trading` — 交易首页（重定向到模拟盘）
- `GET /trading/paper` — 模拟盘全局监控
- `GET /trading/live` — 实盘全局监控
- `GET /trading/live/market` — 市场数据

### 3.6 数据（/data）

**定位：** 独立的数据查看与管理入口。数据查看是高频需求（研究时频繁浏览股票、K线），数据同步/更新也需便捷访问。

| 子视图 | 路由 | 内容 |
|--------|------|------|
| 数据概览 | `/data` | 数据统计（股票数、K线条数、Tick 摘要）、数据源状态 |
| 股票信息 | `/data/stocks` | 股票列表浏览、搜索、分页 |
| K线数据 | `/data/bars` | K线数据查看、按代码和日期范围筛选 |
| 数据同步 | `/data/sync` | 数据更新操作（stockinfo/bars/ticks/adjustfactor）、同步状态 |

**路由：**
- `GET /data` — 数据概览
- `GET /data/stocks` — 股票信息
- `GET /data/bars` — K线数据
- `GET /data/sync` — 数据同步

### 3.7 管理（/admin）

**定位：** 低频运维功能，两个二级入口。

| 二级入口 | 路由 | 内容 |
|----------|------|------|
| 组件 | `/admin/components` | 策略、风控、仓位、选股器、分析器、事件处理器（组件库管理） |
| 系统 | `/admin/system` | 系统状态、Worker 管理、API Key、用户管理、用户组、通知管理、告警中心 |

**路由：**
- `GET /admin` — 管理首页（重定向到组件）
- `GET /admin/components` — 组件库
- `GET /admin/components/:type` — 组件列表（strategies/risks/sizers/selectors/analyzers/handlers）
- `GET /admin/components/:type/:id` — 组件详情
- `GET /admin/system` — 系统状态
- `GET /admin/system/workers` — Worker 管理
- `GET /admin/system/api-keys` — API Key 管理
- `GET /admin/system/users` — 用户管理
- `GET /admin/system/groups` — 用户组管理
- `GET /admin/system/notifications` — 通知管理
- `GET /admin/system/alerts` — 告警中心

## 4. 当前路由到新路由的映射

| 当前路由 | 新路由 | 备注 |
|----------|--------|------|
| `/dashboard` | `/dashboard` | 重写内容 |
| `/portfolio` | `/portfolios` | 复数形式 |
| `/portfolio/create` | `/portfolios/create` | |
| `/portfolio/:id` | `/portfolios/:id` | 增强 6 Tab |
| `/portfolio/:id/edit` | `/portfolios/:id/edit` | |
| `/backtest` | `/portfolios/:id/backtests` | 移入 Portfolio |
| `/backtest/create` | Portfolio 详情内发起 | |
| `/backtest/:id` | `/portfolios/:id/backtests/:backtestId` | |
| `/backtest/compare` | `/portfolios/:id/backtests/compare` | |
| `/validation/walkforward` | `/portfolios/:id/validation` | 合并为 Tab 内子视图 |
| `/validation/montecarlo` | `/portfolios/:id/validation` | 合并为 Tab 内子视图 |
| `/validation/sensitivity` | `/portfolios/:id/validation` | 合并为 Tab 内子视图 |
| `/paper` | `/portfolios/:id/paper` + `/trading/paper` | 双入口 |
| `/paper/orders` | `/portfolios/:id/paper` | 合并到 Tab 内 |
| `/live` | `/portfolios/:id/live` + `/trading/live` | 双入口 |
| `/live/orders` | `/portfolios/:id/live` | 合并到 Tab 内 |
| `/live/positions` | `/portfolios/:id/live` | 合并到 Tab 内 |
| `/live/market` | `/trading/live/market` | |
| `/live/account-config` | `/portfolios/:id/live` + `/admin` | 操作在 Portfolio，配置在管理 |
| `/live/account-info` | `/portfolios/:id/live` | 合并到 Tab 内 |
| `/live/broker-management` | `/portfolios/:id/live` | 合并到 Tab 内 |
| `/live/trade-history` | `/portfolios/:id/live` | 合并到 Tab 内 |
| `/live/trading-control` | `/portfolios/:id/live` | 合并到 Tab 内 |
| `/research/*` | `/research/factor/*` | 保持，增加父路由 |
| `/optimization/*` | `/research/optimization/*` | 移入研究 |
| `/components/*` | `/admin/components/*` | 降为二级 |
| `/data/*` | `/data/*` | 独立顶层入口 |
| `/system/*` | `/admin/system/*` | 降为二级 |

## 5. 技术影响

### 前端变更
- **路由重写：** 89 条路由 → 约 40 条（合并后减少）
- **App.vue：** 侧边栏从 13 项缩减为 6 项，移除子菜单折叠逻辑
- **Portfolio Detail：** 新增 6 Tab 页面结构，作为核心页面
- **Store 调整：** backtest store 需关联 portfolio_id
- **页面迁移：** 部分独立页面转为 Tab 内子组件

### 后端变更
- **无新增 API**
- **路由路径变更：** 前端路由变化不影响后端 API 路径

### 不变
- API 层（request.ts、各 module）
- WebSocket/SSE 实时通信
- 认证逻辑
- 组件库（shadcn-vue）
- 视觉主题（深色）

## 6. 实现策略

### 阶段划分建议

**Phase 1: 路由和导航**
- 重写 App.vue 侧边栏（6 项）
- 重写 router/index.ts
- 添加路由重定向（旧路由 → 新路由）

**Phase 2: Portfolio 详情页**
- 实现 6 Tab 布局框架
- 迁移现有 Portfolio 列表/创建/编辑
- 迁移回测列表/详情到 Tab 内

**Phase 3: 其他页面迁移**
- 研究页面整合
- 交易监控页面
- 管理页面降级

**Phase 4: 工作台重写**
- Dashboard 重写（当前是 stub）

### 兼容性
- 旧路由设置 redirect 到新路由，避免 bookmark 失效
- E2E 测试需要更新选择器和路由

## 7. 开放问题

（无 — 所有设计决策已确认）
