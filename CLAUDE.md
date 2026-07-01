# CLAUDE.md
输出内容控制在一屏内,不要滚动。Chat in mandarin.

## Project Overview
Ginkgo: Python 量化交易库。事件驱动回测引擎，支持 ClickHouse/MySQL/MongoDB/Redis，多数据源，完整风控。

## 核心架构规则

### 事件链路
`PriceUpdate → Strategy → Signal → Portfolio → Order → Fill`

### 组件边界（单向流动：`Selector → Strategy → Sizer → Risk`）

| 组件 | 职责 | 输出 | 禁止 |
|---|---|---|---|
| Selector | 选股 | `List[str]` | 生成信号、计算仓位、做风控 |
| Strategy | 交易信号 | `List[Signal]` | 选股、止损止盈、计算仓位 |
| Sizer | 开仓手数 | volume | 风控校验 |
| Risk | 风控拦截 | 调整后 order/signal | 增加订单量 |

### 分层架构（`API/CLI → Service → CRUD → DB`）
1. **API 禁止直接调 CRUD**，必须通过 Service
2. **Service 禁止暴露 CRUD 实例**
3. **CRUD 返回 `ModelList`**，调用方按需转换

### 全局实例
`GLOG`(日志) | `GCONF`(配置) | `GTM`(线程管理)，通过 `from ginkgo import services` 统一访问

## Git 规范
- 分支：`{递增序号}-{类型}/{描述}`，类型：feat/fix/refactor/docs/test/chore
- 创建前查远端最大序号：`git branch -r | grep -oP '\d+(?=-)' | sort -n | tail -1`
- 测试统一放 `tests/`，禁止模块内 `tests/` 子目录

## 开发约束

### 数据库
- **禁止手动 ALTER TABLE**，表由 Model 定义 + `ginkgo init` 自动创建
- Docker 双实例：Master(非Debug) | Test(Debug，端口首位+1)
- ClickHouse=时序 | MySQL=关系 | Redis=缓存 | MongoDB=文档

### Debug 模式
数据库操作前必须开启：`ginkgo debug on`

### 基础组件
**禁止擅自修改 Base 类**（BaseCRUD、BaseService 等），在具体实现层处理

### 归因纪律（防 #4652 类事故）
撞 `ImportError` / 命令跑不通，**禁止直接判"未实现"加 `return`+TODO 存根**。#4652 把 `BacktestEvaluator` 的 import 路径漂移（`ginkgo.trading.evaluation` → `ginkgo.trading.analysis.evaluation.backtest_evaluator`）误判为"功能未实现"，加 stub 屏蔽了 `ginkgo eval stability/monitor-create/monitor-live` 三命令，而底层实现完好、且有 3 个调用方在真实运行。判未实现前必做：
1. `grep` 类名/函数名全仓引用，看有无调用方在使用（有调用方 = 实现必存在）
2. 对比同模块其他文件的 import 路径，确认是否路径漂移
3. 批量修复 PR（如"一次修 15 个 bug"）逐条抽检归因，最易凑合出事

**深层诱因（架构陷阱）：**
- 函数级 import（CLI 为快启把重度 import 延到命令体内）让路径漂移只在命令实跑时暴露——模块 import 不崩，最容易误判"未实现"
- `return` stub 让失败静默（命令"安静失败"而非"响亮报错"），反而盖住真因，后续无人回头查；宁可原样 `raise` 也别加 stub 兜底

## Key Commands
```bash
ginkgo version / status                       # 版本/状态
ginkgo debug on                               # 开启 debug（必须）
ginkgo serve api                              # API 服务器 (:8000)
ginkgo serve webui                            # Web UI (:5173)
ginkgo serve worker-backtest --id test2       # 回测 Worker
```
日志：`/tmp/ginkgo-api.log` | `/tmp/webui.log` | `/tmp/ginkgo-backtest.log`

## Agent skills
- Issue tracker → `docs/agents/issue-tracker.md`
- Triage labels → `docs/agents/triage-labels.md`
- Domain docs → `docs/agents/domain.md`

## 详细参考文档（按需查阅）
- **开发模式/API/风控/日志/实盘** → `docs/claude-dev-reference.md`
- **架构决策记录 (ADR)** → `docs/adrs/README.md`（难逆转/反直觉/真实权衡的决策，触碰架构前先读）
- **CLI 回测全链路操作指南** → 见下方

## CLI 全链路（构建→回测→模拟盘→实盘）

> **可用性（2026-06-28 实测，详见 [e2e 审计](docs/e2e-cli-flow-audit.md)）**：构建 ✅ ｜ 回测 ⚠️（无数据预检、0 交易定位难）｜ 模拟盘 ⚠️（核心修复 #6164 已落地，端到端待复测）｜ 实盘 ⚠️（`account`/`deploy` 命令就绪，端到端待验证）。文档口径以审计报告为权威，勿超前于代码实际能力。

### 流程
创建 Portfolio → 复用/创建 Component → 绑定组件(含参数) → 创建回测 → 运行 → [deploy 模拟/实盘]

**Python 环境**：`/home/kaoru/.ginkgo/.venv/bin/python`

```bash
# Portfolio
ginkgo portfolio create --name "my" --capital 1000000
ginkgo portfolio list
ginkgo portfolio get <uuid> --details

# Component（建议复用已有，basic template 无参数定义）
ginkgo component list

# 绑定（参数格式：'index:value'，字符串带引号，数值直接写）
ginkgo portfolio bind-component <pid> <file_id> --type strategy \
  --param '0:"StrategyName"' --param '1:0.3'

# 回测
ginkgo backtest create --portfolio <pid> --start 2025-05-07 --end 2026-05-07 --name "test" --cash 100000
ginkgo backtest run <backtest_id>
ginkgo backtest cat <backtest_id>

# 部署（模拟盘/实盘）⚠️ 端到端待复测，见 docs/e2e-cli-flow-audit.md
ginkgo deploy deploy <pid> --mode paper                          # 模拟盘
ginkgo deploy deploy <pid> --mode live --account <account_uuid>  # 实盘（需先建账户）
ginkgo deploy info <deployment_id>                               # 部署详情
ginkgo account create <user_id> --exchange okx --name "..." --api-key ... --api-secret ...
ginkgo account list <user_id>
```

### 可用组件

> **实际命名**：DB 组件名多为 `<name>_<type>` 格式（如 `fixed_selector`/`atr_sizer`/`fixed_sizer`），部分带描述前缀（如 `qr_momentum_selector`/`sharpe_ratio`）。`bind-component` 前用 `ginkgo component list` 查实际 `file_id` 与名称；下表为短名速查。

- **Strategy**（内置类 11）: random_signal, moving_average_crossover, mean_reversion, momentum, trend_follow, trend_reverse, dual_thrust, scalping, price_action, volume_activate, ml_predictor；另有 DB 脚本组件（src 无类，DB component 表实例）: social_signal, game_theory, random_choice
- **Selector**: fixed, cn_all, momentum, popularity, multi_params
- **Sizer**: fixed, atr, ratio
- **Risk**: no_risk, position_ratio, loss_limit, profit_target, max_drawdown, volatility, concentration, capital, liquidity, margin, market_cap, sector_rotation, correlation, currency, suspension, trading_time, time_based
