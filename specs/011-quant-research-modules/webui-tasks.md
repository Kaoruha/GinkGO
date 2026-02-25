# WebUI 前端任务列表

**Date**: 2026-02-18
**Branch**: `011-quant-research-modules`
**Prerequisites**: 后端 API 已存在，可直接调用

---

## 任务格式

`[ID] [P?] [模块] 描述`

- **P**: 可并行执行
- 状态: ⏳ 待实现 | 🚧 进行中 | ✅ 完成

---

## P1 高优先级（核心功能）

### 组件管理 - 代码编辑器（6个页面）

共用同一个代码编辑器组件，仅 `type` 参数不同。

#### W001 [P] 创建共享代码编辑器组件 ✅

- **File**: `web-ui/src/components/CodeEditor.vue`
- **Description**: 代码编辑器封装，支持 Python 语法
- **Acceptance**:
  - [x] 代码编辑器集成完成
  - [x] 支持 Python 语法
  - [x] 支持读取/保存文件内容
  - [x] 支持文件列表展示
- **Implemented**: 2026-02-18

#### W001b [P] 创建共享组件列表组件 ✅

- **File**: `web-ui/src/components/ComponentList.vue`
- **Description**: 通用组件列表页面，包含文件列表和编辑器
- **Acceptance**:
  - [x] 文件列表展示（名称、更新时间）
  - [x] 搜索、新建、删除功能
  - [x] 集成代码编辑器组件
  - [x] 保存文件功能
- **Implemented**: 2026-02-18

#### W002 [P] 实现策略组件页面 ✅

- **File**: `web-ui/src/views/components/StrategyList.vue`
- **API**: `GET /api/v1/file_list?type=6` (STRATEGY)
- **Acceptance**:
  - [x] 文件列表展示
  - [x] 搜索、新建、删除功能
  - [x] 集成代码编辑器组件
  - [x] 保存文件功能
- **Implemented**: 2026-02-18

#### W003 [P] 实现风控组件页面 ✅

- **File**: `web-ui/src/views/components/RiskList.vue`
- **API**: `GET /api/v1/file_list?type=3` (RISKMANAGER)
- **Acceptance**: 同 W002
- **Implemented**: 2026-02-18

#### W004 [P] 实现仓位组件页面 ✅

- **File**: `web-ui/src/views/components/SizerList.vue`
- **API**: `GET /api/v1/file_list?type=5` (SIZER)
- **Acceptance**: 同 W002
- **Implemented**: 2026-02-18

#### W005 [P] 实现选股器页面 ✅

- **File**: `web-ui/src/views/components/SelectorList.vue`
- **API**: `GET /api/v1/file_list?type=4` (SELECTOR)
- **Acceptance**: 同 W002
- **Implemented**: 2026-02-18

#### W006 [P] 实现分析器页面 ✅

- **File**: `web-ui/src/views/components/AnalyzerList.vue`
- **API**: `GET /api/v1/file_list?type=1` (ANALYZER)
- **Acceptance**: 同 W002
- **Implemented**: 2026-02-18

#### W007 [P] 实现事件处理器页面 ✅

- **File**: `web-ui/src/views/components/HandlerList.vue`
- **API**: `GET /api/v1/file_list?type=8` (HANDLER)
- **Acceptance**: 同 W002
- **Implemented**: 2026-02-18

#### W028 E2E 测试 - 组件管理 ✅

- **File**: `web-ui/tests/e2e/component-management.test.js`
- **Acceptance**:
  - [x] 测试访问所有 6 个组件页面
  - [x] 测试创建新文件
  - [x] 测试编辑并保存文件
  - [x] 测试搜索文件
- **Implemented**: 2026-02-18

---

### 订单与持仓（4个页面）

#### W008 [P] 实现模拟订单页面 ✅

- **File**: `web-ui/src/views/stage3/PaperTradingOrders.vue`
- **API**: `GET /api/orders?mode=paper`
- **Data**: MOrder (code, direction, order_type, status, volume, price, timestamp)
- **Acceptance**:
  - [x] 订单列表表格展示
  - [x] 筛选：状态、代码、时间范围
  - [x] 排序：按时间倒序
  - [x] 手动刷新按钮
- **Implemented**: 2026-02-18

#### W009 [P] 实现实盘订单页面 ✅

- **File**: `web-ui/src/views/stage4/LiveOrders.vue`
- **API**: `GET /api/orders?mode=live`
- **Acceptance**: 同 W008
- **Implemented**: 2026-02-18

#### W010 [P] 实现实盘持仓页面 ✅

- **File**: `web-ui/src/views/stage4/LivePositions.vue`
- **API**: `GET /api/positions`
- **Acceptance**:
  - [x] 持仓列表（代码、名称、数量、成本、现价、盈亏）
  - [x] 汇总信息（总资产、总盈亏、持仓分布）
  - [x] 手动刷新按钮
- **Implemented**: 2026-02-18

#### W011 [P] 完善模拟交易页面 ✅

- **File**: `web-ui/src/views/stage3/PaperTrading.vue`
- **Acceptance**:
  - [x] 显示模拟交易状态
  - [x] 启动/停止控制
  - [x] 设置抽屉（滑点、手续费、延迟）- 已完成框架
- **Implemented**: 2026-02-18

---

## P2 中优先级

### 系统状态

#### W012 实现系统状态页面 ✅

- **File**: `web-ui/src/views/system/SystemStatus.vue`
- **Features**:
  - 系统概览（服务运行状态）
  - 数据库连接状态（ClickHouse/MySQL/Redis/MongoDB）
  - Worker 管理（列表、状态、任务队列）
  - 资源监控（CPU/内存）
- **Acceptance**:
  - [x] 各服务状态展示
  - [x] Worker 列表和状态
  - [x] 实时刷新（定时轮询）
- **Implemented**: 2026-02-18

### 回测对比

#### W013 实现回测对比页面 ✅

- **File**: `web-ui/src/views/stage1/BacktestCompare.vue`
- **API**: `POST /api/backtest/compare`
- **Features**:
  - 多选回测任务（2-5个）
  - BASIC_ANALYZERS 指标对比表
  - 净值曲线对比图
- **Acceptance**:
  - [x] 回测多选组件
  - [x] 指标对比表格
  - [x] 净值曲线叠加图（ECharts）
  - [x] 最佳表现标注
- **Implemented**: 2026-02-18

### 数据同步

#### W014 实现数据同步页面 ✅

- **File**: `web-ui/src/views/data/DataSync.vue`
- **Mechanism**: Kafka `ControlCommandDTO` 到 `ginkgo.data.commands`
- **Commands**: BAR_SNAPSHOT, TICK, STOCKINFO, ADJUSTFACTOR
- **Acceptance**:
  - [x] 命令类型选择
  - [x] 股票代码输入（单个/批量）
  - [x] 参数配置（full/overwrite）
  - [x] 发送命令按钮
  - [x] 已发送命令列表
- **Implemented**: 2026-02-18

### 策略验证（3个页面）

#### W015 [P] 实现走步验证页面 ✅

- **File**: `web-ui/src/views/stage2/WalkForward.vue`
- **API**: `POST /api/validation/walkforward`
- **Features**:
  - 策略/组合选择
  - 参数配置（折数、训练期比例）
  - 结果展示（各 fold 训练/测试收益、退化程度）
- **Acceptance**:
  - [x] 配置表单
  - [x] 执行进度显示
  - [x] 结果表格和图表
- **Implemented**: 2026-02-18

#### W016 [P] 实现蒙特卡洛页面 ✅

- **File**: `web-ui/src/views/stage2/MonteCarlo.vue`
- **API**: `POST /api/validation/montecarlo`
- **Features**:
  - 数据源选择（历史回测结果）
  - 参数配置（模拟次数、置信水平）
  - 收益分布直方图、VaR/CVaR
- **Acceptance**:
  - [x] 配置表单
  - [x] 分布直方图（ECharts）
  - [x] VaR/CVaR 结果展示
- **Implemented**: 2026-02-18

#### W017 [P] 实现敏感性分析页面 ✅

- **File**: `web-ui/src/views/stage2/Sensitivity.vue`
- **API**: `POST /api/validation/sensitivity`
- **Features**:
  - 策略选择、参数名、测试值列表
  - 参数值 vs 收益曲线图
  - 敏感性分数
- **Acceptance**:
  - [x] 配置表单
  - [x] 敏感性曲线图
  - [x] 结果表格
- **Implemented**: 2026-02-18

---

## P3 低优先级

### 因子研究（5个页面）

#### W018 [P] 实现 IC 分析页面 ✅

- **File**: `web-ui/src/views/research/ICAnalysis.vue`
- **API**: `POST /api/research/ic`
- **Features**: 因子选择、收益周期、IC 统计表格、IC 时序图
- **Implemented**: 2026-02-18

#### W019 [P] 实现因子分层页面 ✅

- **File**: `web-ui/src/views/research/FactorLayering.vue`
- **API**: `POST /api/research/layering`
- **Features**: 因子选择、分层数、各组收益曲线、多空收益
- **Implemented**: 2026-02-18

#### W020 [P] 实现因子正交化页面 ✅

- **File**: `web-ui/src/views/research/FactorOrthogonalization.vue`
- **API**: `POST /api/research/orthogonalize`
- **Features**: 多因子选择、正交化方法、相关性矩阵对比
- **Implemented**: 2026-02-18

#### W021 [P] 实现因子对比页面 ✅

- **File**: `web-ui/src/views/research/FactorComparison.vue`
- **API**: `POST /api/research/compare`
- **Features**: 多因子选择、IC 对比表、综合评分
- **Implemented**: 2026-02-18

#### W022 [P] 实现因子衰减页面 ✅

- **File**: `web-ui/src/views/research/FactorDecay.vue`
- **API**: `POST /api/research/decay`
- **Features**: 因子选择、最大周期、IC 衰减曲线、半衰期
- **Implemented**: 2026-02-18

### 参数优化（3个页面）

#### W023 [P] 实现网格搜索页面 ✅

- **File**: `web-ui/src/views/optimization/GridSearch.vue`
- **API**: `POST /api/optimization/grid`
- **Features**: 策略选择、参数范围定义、进度条、结果排名表、热力图
- **Implemented**: 2026-02-18

#### W024 [P] 实现遗传算法页面 ✅

- **File**: `web-ui/src/views/optimization/GeneticOptimizer.vue`
- **API**: `POST /api/optimization/genetic`
- **Features**: 策略选择、种群配置、进化曲线、最优参数
- **Implemented**: 2026-02-18

#### W025 [P] 实现贝叶斯优化页面 ✅

- **File**: `web-ui/src/views/optimization/BayesianOptimizer.vue`
- **API**: `POST /api/optimization/bayesian`
- **Features**: 策略选择、迭代配置、收敛曲线、后验分布图
- **Implemented**: 2026-02-18

---

## 共享组件

#### W026 [P] 创建参数配置组件 ⏭️

- **File**: `web-ui/src/components/ParamConfig.vue`
- **Description**: 可复用的参数范围配置组件
- **Status**: 暂不实现，各页面直接内联配置

#### W027 [P] 创建结果图表组件 ⏭️

- **File**: `web-ui/src/components/ResultChart.vue`
- **Description**: ECharts 封装，支持常见图表类型
- **Status**: 暂不实现，项目使用 lightweight-charts

---

## 任务统计

| 优先级 | 任务数 | 完成数 | 说明 |
|--------|--------|--------|------|
| P1 | 11 | 11 | 组件管理(7) + 订单持仓(4) |
| P2 | 6 | 6 | 系统状态 + 回测对比 + 数据同步 + 验证(3) |
| P3 | 8 | 8 | 因子研究(5) + 参数优化(3) |
| 共享组件 | 2 | 0 | 暂不需要 |
| E2E测试 | 3 | 3 | component-management + order-position + validation-pages |
| **总计** | **30** | **28** | |

**E2E 测试结果：35/35 全部通过**

---

## 执行顺序建议

```
共享组件 (W026, W027)
     ↓
┌────┴────┐
↓         ↓
W001     W012-W017    (可并行)
代码编辑器   P2 页面
     ↓
W002-W007    (可并行)
组件管理页面
     ↓
W008-W011    (可并行)
订单持仓页面
     ↓
W018-W025    (P3 - 最后)
因子研究 + 参数优化
```

---

## 删除/搁置的页面

| 页面 | 原因 |
|------|------|
| `/stage3/paper/config` | 已合并到 PaperTrading.vue 设置抽屉 |
| `/system/workers` | 已合并到 SystemStatus.vue |
| `/system/alerts` | 搁置，暂不实现 |
