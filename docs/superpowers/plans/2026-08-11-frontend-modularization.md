# Frontend 模块化/组件化/复用重构 Plan

> **执行方式:** Epic #6910 分支 `epic-6910-frontend-electron-dual-form` 上直接提交。7 阶段按风险升序;阶段 0-3 为确定性工作,4-6 为高风险(动 UI,需逐项验收)。

**Goal:** 消除死代码、归位散落目录、抽公共 composable、拆 5 个超大文件,使 frontend/src/renderer 达到"组件分层清晰、跨页复用充分、单文件 <500 行"。

**当前体量:** 65 页面 / 30924 行 .vue / Top5 大文件 1919·1275·1029·1018·1017。

---

## 阶段 0 — 删死代码(零风险,无引用)

**Files - Delete:**
- `views/components/AnalyzerList.vue` `RiskList.vue` `SelectorList.vue` `SizerList.vue` `StrategyList.vue` `HandlerList.vue`(6 个 7 行 wrapper,router 不走、零 import,所传 prop 被 ComponentListPage 无视)
- `components/ComponentList.vue`(657 行,旧 master-detail,零引用)
- `composables/useComponentList.ts`(零调用方)
- `views/stage2/MonteCarlo.vue`(199 行,零引用,与 portfolio/validation/MonteCarlo 逐字重复)
- `views/stage3/PaperTradingOrders.vue`(零引用)
- `views/stage4/LiveOrders.vue` `views/stage4/LivePositions.vue`(零引用)

**验收:** `vue-tsc --noEmit` EXIT=0;`grep -r <删掉的符号>` 全仓零命中;dev server 起得来。

**收益:** ~900 行死代码清除。

---

## 阶段 1 — validation 去重 + 路由清理

**Files - Delete/Modify:**
- Delete `views/validation/ValidationListPage.vue`(281 行,与 ValidationTab 功能重复,只是顶级页手填 task_id)
- Modify `router/index.ts`:删 `/validation` 顶级路由;保留旧 `/validation/{walkforward,montecarlo,sensitivity}` → `/portfolios` redirect(已存在)
- Modify 菜单配置(App.vue menuItems / config/menu.ts 见阶段 3):"验证"入口改跳 `/portfolios`

**验收:** `/validation` 不再可达;`/portfolios/:id/validation`(ValidationTab)仍正常。

**收益:** 消除一份重复实现。

---

## 阶段 2 — 目录归位(按业务域,与路由前缀对齐)

stage2/3/4 是早期"流程阶段编号"遗留,现已不对应流程。`settings/`+`system/` 同挂 `/admin/*` 却拆两目录。

**Files - Move(+ 改 import + 改 router 路径):**
- `views/stage2/WalkForward.vue` `Sensitivity.vue` → `views/portfolio/validation/`(与 MonteCarlo/SegmentStability 合流)
- `views/stage3/PaperTrading.vue` → `views/trading/`
- `views/stage4/LiveTrading.vue` `MarketData.vue` → `views/live/`
- `views/settings/{UserManagement,UserGroupManagement,NotificationManagement}.vue` + `views/system/{SystemStatus,WorkerManagement,ApiKeyManagement,AlertCenter,TaskTimerHistory}.vue` → `views/admin/`(8 文件,与 `/admin` 路由前缀对齐)
- Delete 空 `stage2/` `stage3/` `stage4/` `settings/` `system/` 目录

**验收:** `vue-tsc` EXIT=0;每个移动文件的页面路由仍可达 + 渲染正常。

**收益:** 目录名 = 路由前缀 = 业务域;消除 5 个临时目录。

---

## 阶段 3 — App.vue 拆分

App.vue 559 行 = 120 template + 159 script + **278 scoped CSS(50%)**。script 已干净(路由守卫在 router、状态在 Pinia),但 layout+CSS 全内嵌。

**Files - Create:**
- `components/layout/AppSider.vue` — template sider 块 + `.sider/.menu/.menu-item` 样式
- `components/layout/AppHeader.vue` — template header 块 + 点击外部关闭逻辑 + `.header/.notification/.avatar/.dropdown` 样式
- `config/menu.ts` — 合并 `menuItems` + `routeToKeyMap` + `getRouteForKey` 三份冗余配置为一份;`isEditorPage`/`isFullPage` 移入路由 `meta`

**Files - Modify:**
- `App.vue` — 退化为 `<AppSider/><AppHeader/><router-view/>` + 生命周期,~150 行
- 清理 stub:`showToast`(console.log)、`showNotifications`(TODO 空函数)

**验收:** `vue-tsc` EXIT=0;菜单导航/用户下拉/主题切换全正常。

**收益:** App.vue 559 → ~150;菜单配置单源。

---

## 阶段 4 — 通用 composable(跨文件去重)

**Files - Create:**
- `composables/useFormatters.ts` — PnL 着色(`getPnLColor`)+ 数字/货币/百分比/体积格式化。消费方:BacktestTab、AccountInfo、MarketData(三处各写一份)
- `composables/usePolling.ts` — `usePolling(fn, interval)` 通用轮询,封装 `setInterval`+`onUnmounted`+可见性暂停。消费方:AccountInfo(10s)、MarketData(5s),grep `setInterval` 扩查 live 目录其他消费方

**Files - Modify:** 上述三页替换内联实现 → import composable。

**验收:** `vue-tsc` EXIT=0;三页数字/着色/轮询行为不变;`composables/__tests__` 补 usePolling 单测。

**收益:** 三处格式化去重;轮询逻辑单源。

---

## 阶段 5 — 大文件拆分(高风险,逐文件做+逐文件验收)

### 5a. BacktestTab.vue 1919 → ~1400(拆 LogsTab + DatePicker + MetricCard + formatters)

**Create:**
- `components/charts/backtest/LogsTab.vue` + `LogEntry.vue` — 15 种 event_type 分支(template 140 行 + 样式 70)
- `components/common/DatePicker.vue` — start/end 双份自研日历合并(MetricCard 同构卡片)
- `components/common/MetricCard.vue` — 10 张同构指标卡
- `composables/useBacktestFormatters.ts` — 15 个 format/color 纯函数(~100 行)

**Modify:** BacktestTab 替换内联块。

### 5b. PortfolioFormEditor.vue 1275 → ~400

**Create:**
- `components/form/ParamInput.vue` — 4 类型分支去重(~150 行)
- `composables/useComponentManager.ts` — 参数化 add/remove/changeVersion,消灭 5 类型 if/else(~250 行)
- `components/portfolio/ComponentConfigSection.vue` + `ComponentConfigItem.vue` — 5 section → v-for

**Modify:** 顺手删死代码 `selectedXxx` 5 ref + 修 `isEditMode` 永远走 create 的半成品。

### 5c. Login.vue 1029 → ~400

**Create:** `composables/useBootLog.ts` `useTerminalTypewriter.ts` `useStockTicker.ts` + `components/auth/BootLog.vue` `StockTicker.vue` `ParticleBackground.vue` + `LoginForm.vue`(业务隔离,登录本体仅 ~20 行)。

**注意:** 用户约束"当前登录页面的风格尽可能保留" — 拆分必须视觉零差异,纯结构重组,不改样式/动画。

### 5d. AccountInfo.vue 1018 → ~400

**Create:** `components/live/AccountCard.vue`(template 砍一半)+ `composables/useAccountPolling.ts`(状态+加载+轮询 ~180 行,接阶段 4 usePolling)。

### 5e. MarketData.vue 1017 → ~400

**Create:** `composables/useMarketWebSocket.ts`(150 行 WS:连接/重连/订阅/价格方向)+ `usePriceAnimation.ts`(三表状态机)+ `useMarketDataApi.ts`。
**清理:** 3 个 console.log 调试 watch + 调试 computed。

**每文件验收:** `vue-tsc` EXIT=0 + 手动看对应页面(回测详情/组合编辑/登录/账户/行情)渲染 + 交互无回归。

---

## 阶段 6 — 列表/表格统一

**Modify:**
- `components/common/ListPage.vue` — 内嵌 `<table class="pro-table">`+分页块 → 改用 `<DataTable>`(ListPage 退化为 header+search+create 外壳)
- 4 个 Factor 视图(`FactorComparison`/`FactorDecay`/`FactorLayering`/`ICAnalysis`)手写 `<table class="data-table">` → 改用 `<DataTable>`
- `components/ui/table/*`(shadcn 原子,全仓仅 TradeHistory 1 处用)→ **决策**:要么 ListPage/DataTable/Factor 全改用它统一,要么删。倾向删(已有 DataTable 满足,半引进僵局不如清掉)。

**验收:** `vue-tsc` EXIT=0;ListPage 消费方(ComponentListPage/PortfolioList/BacktestListPage)+ Factor 4 页表格/分页/排序正常。

**收益:** "表格+分页"单源(DataTable);消除 4 处样式复制。

---

## 风险与回退

- 全程在 `epic-6910-frontend-electron-dual-form` 分支,**每阶段独立 commit**,出问题 `git reset` 单阶段。
- 阶段 5(大文件拆分)每文件一个 commit + vue-tsc 闸门,视觉回归靠用户验收。
- 阶段 2(文件移动)用 `git mv` 保历史;改 import 用全路径 grep 批量替换。
- 不动:`ui/`(shadcn 原子)、`api/`(request 封装已规范)、`styles/`(阶段 0 的对比度修复已落地)。
