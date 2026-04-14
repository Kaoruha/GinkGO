# 研究链路 MVP 设计

**日期**: 2026-04-14
**目标**: 打通「数据导入 → 策略研发 → 回测 → 验证 → 模拟盘 → 结果分析」全链路，达到内部团队（5-50人）可交付的 MVP 标准。
**方案**: 方案A — 最小研究链路，聚焦已有断点修复。

## 背景

Ginkgo 项目核心架构完成度高（回测引擎90%、分析器95%、模拟盘Worker100%、Kafka95%），但存在若干断点导致研究链路端到端不通。本设计只修复这些断点，不扩展实盘和多市场。

## 范围

### 做什么
1. 修复枚举值冲突 + 模拟盘Worker失败测试
2. 补充4个常用量化策略（均值回归、趋势跟踪、动量因子、配对交易）
3. 补全 Web UI ↔ API 端到端连通（Dashboard真实数据、PaperTrading API、实盘账号API）
4. Playwright E2E 验证关键流程

### 不做什么
- AKShare/Yahoo 数据源实现
- Binance Broker
- FuturesBroker / HKStockBroker / USStockBroker
- 8个骨架风控填充
- CI/CD 流水线
- Arena 模块

## 阶段一：Bug 修复

### 1.1 枚举值冲突

`SOURCE_TYPES` 枚举中 `PAPER_REPLAY=18` 与 `MANUAL=18` 冲突，`PAPER_LIVE=19` 与 `OKX=19` 冲突。

**方案**: 给 MANUAL 和 OKX 重新分配不冲突的枚举值（如 20、21），全局搜索引用点更新。

**涉及文件**: `src/ginkgo/enums.py` + 所有引用 MANUAL/OKX 枚举值的文件。

### 1.2 模拟盘Worker测试修复

`tests/unit/workers/test_paper_trading_worker.py` 中43个测试有4个失败。

**方案**: 逐个分析失败原因并修复。

## 阶段二：策略库补充

从6个空文件中选4个最有研究价值的实现，另外2个（`game_theory`、`social_signal`）删除空文件。

### 2.1 均值回归策略（`mean_reversion.py`）

- 基于 RSI 超买超卖信号
- 可选 Bollinger Bands 辅助确认
- 参数：RSI周期、超买/超卖阈值、持仓周期

### 2.2 趋势跟踪策略（`trend_reverse.py`）

- 多均线趋势判断（短/中/长期均线排列）
- ATR 动态止损
- 参数：均线周期组合、ATR倍数

### 2.3 动量因子策略（新建或复用空文件）

- 截面动量排名选股
- 定期调仓
- 参数：动量回看期、持仓数量、调仓频率

### 2.4 配对交易策略（新建或复用空文件）

- 协整关系检测
- 价差标准化 + 均值回归开平仓
- 参数：协整窗口、开仓阈值、平仓阈值

### 实现标准

- 继承 `BaseStrategy`，实现 `cal(portfolio_info, event)`
- 通过 `@time_logger` 监控性能
- 每个策略配单元测试

## 阶段三：API 端到端连通

### 3.1 Dashboard 真实数据

**文件**: `apiserver/api/dashboard.py`

替换硬编码数据，接入：
- 运行中 Portfolio 数量（从 `PortfolioCRUD` 查询）
- 回测任务统计（从 `BacktestTaskCRUD` 查询，按状态分组）
- 最近回测结果摘要（关联 `AnalyzerRecord`）
- 系统健康状态（Kafka/数据库连接检查）

### 3.2 PaperTrading API 路由

**前端现状**: `web-ui/src/api/modules/trading.ts` 已定义完整API接口（`getPaperAccounts`、`startPaperTrading`、`getPaperPositions` 等），但后端路由缺失或未注册。

**方案**: 在 `apiserver/api/` 下补全对应路由，对接已有的 `PaperTradingWorker` Kafka 控制命令和 CRUD 查询。

### 3.3 实盘账号 API 路由

**前端现状**: `web-ui/src/api/modules/live.ts` 已定义完整API客户端（`getAccounts`、`createAccount`、`validateAccount` 等）。

**方案**: 补全 `/api/v1/accounts` 等端点路由注册，对接已有的 `LiveAccountService`。

## 阶段四：E2E 验证

用 Playwright 覆盖关键研究流程：

1. 登录 → Dashboard 显示真实统计数据
2. 创建 Portfolio → 添加策略和风控 → 保存
3. 创建回测任务 → 运行 → 查看结果
4. 模拟盘页面显示 Portfolio 列表和状态

**验证标准**: 从前端 UI 最终显示判断，而非中间环节。
