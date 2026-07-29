# ADR-037: 滑点成交价统一（FillPriceModel + 回测/模拟盘装配归一 engine_data.slippage）

**Status:** Accepted
**Date:** 2026-07-29
**Related:** ADR-018（回测派发 wire spec slippage_rate）、ADR-033（PaperTradingWorker 装配对称）、ADR-022（抽象层收敛/死抽象判定）、ADR-036（回测 fill 时序）、#6851

## Context

issue #6851 指出滑点抽象"半接"：`SlippageModel`（`trading/paper/slippage_models.py`）接口完整（Fixed/Percentage/No 三实现）但零生产消费方；CLI `--slippage` 死参数；SimBroker 用 scipy 态度采样算成交价而非 `SlippageModel.apply`。经 spike 核实（grep/Read 全仓，锚点如下）：

### 滑点两套概念并存（反直觉）

- `SimBroker`（`trading/brokers/sim_broker.py`）：`scipy.stats` 态度采样（`_get_random_transaction_price:395`，norm/skewnorm 在当日 low~high 区间按 OPTIMISTIC/NEUTRAL/PESSIMISTIC 采样），内置 `slippage_tolerance`（默认 0.05，**采样区间容忍**，`:69`）——"成交价落在日高低区间的随机分布"。
- `SlippageModel`（`trading/paper/slippage_models.py`）：固定金额/百分比**加减到成交价**（`FixedSlippage.apply`/`PercentageSlippage.apply`）——"买卖价差/冲击成本"。
- 两者都叫"滑点"但语义不同；`SlippageModel` 零生产调用方（仅 `get_default_slippage_model` 工厂，无消费）。

### `--slippage` 死参数完整链路（归因）

CLI `backtest create --slippage`（`client/backtest_cli.py:135`）→ `config_snapshot` JSON（key=`slippage_rate`）→ wire spec（`data/services/backtest_task_service.py:804` key 列表含 `slippage_rate`）→ `BacktestConfig.slippage_rate` → `build_engine_data`（`workers/backtest_worker/task_helpers.py:34` **已灌入** `engine_data["slippage_rate"]`）→ `assembly_service.assemble_backtest_engine`（`trading/services/backtest_orchestrator.py:261`）→ `InfrastructureFactory.create_broker_from_config`（`trading/services/_assembly/infrastructure_factory.py:167`，**default_cfg 无 slippage 键、不读 engine_data.slippage_rate ✱ 断点**）→ `SimBroker(**cfg)` 零 slippage。

**单一断点** = `create_broker_from_config` 不消费 `engine_data.slippage_rate`。上游 `build_engine_data:34` 已通，下游 SimBroker 收不到。

### 装配双链路（回测 vs 模拟盘分离）

- **回测**：`BacktestOrchestrator._assemble_engine`（`backtest_orchestrator.py:245`）→ `build_engine_data(config)`（:253）→ `assembly_service.assemble_backtest_engine(engine_data)`（:261）→ `InfrastructureFactory` 工厂 → `create_broker_from_config`。**经工厂、经 engine_data**。
- **模拟盘**：`PaperTradingWorker.assemble_engine`（`workers/paper_trading_worker.py:86`）手写 `SimBroker()` 零参（:132）+ `BacktestFeeder()`+`TradeGateway(brokers=[broker])`（:131-133）。**不走 assembly_service、不走工厂、不经 engine_data**。
- **实盘**：`execution_node/node.py:555-558` 用 `EngineAssemblyService` 加载 portfolio，Kafka 实时架构 + 真 Broker，与回测/模拟盘语义差异大。本 Epic 不含，另开。

### 死代码（spike 副产物）

`TaskEngineBuilder.build_engine_from_task`（`trading/services/_assembly/task_engine_builder.py:45`，内部 :261 `SimBroker(task.config 直构)`）及其门面 `engine_assembly_service.build_engine_from_task:437-439` **零外部调用方**（grep 全仓）——回测真实走 `assemble_backtest_engine` 工厂路径，`build_engine_from_task` 是历史遗留死路径。前期曾误判 `--slippage` 断点在 `task_engine_builder:261`，即因此死路径误导归因。

### 存储：配置范式分裂（不止 slippage）

回测运行参数（cash/commission/slippage）存 `MBacktestTask.config_snapshot` JSON 快照（per-task 一次性）；模拟盘运行参数存 `MPortfolio` 独立列（长驻持续，当前 commission/slippage 均**无列、无持久化**）。分裂根源 = 任务快照 vs 长驻列，反映执行语义差异。

判定四条全中（滑点半接难逆转 / slippage_tolerance vs SlippageModel 反直觉 / 存储 P/Q/R 真实权衡 / 装配归一范围真实取舍），立本 ADR。

## Decision

### D1 滑点成交价统一：FillPriceModel（SimBroker 单一切入点）

新建 `FillPriceModel`（Protocol，非 ABC，放 `trading/brokers/sim_broker.py` 同目录），定义成交价计算契约。两实现：
- `AttitudePricing`：移植现有 scipy 态度采样（`_get_random_transaction_price:395` 的 norm/skewnorm + OPTIMISTIC/NEUTRAL/PESSIMISTIC），保留 `slippage_tolerance` 作采样区间参数。**回测行为零回归**。
- `DeterministicSlippage`：包装 `SlippageModel`（Fixed/Percentage/No），成交价 = `SlippageModel.apply(base_price, direction)`。接通 `--slippage`。

SimBroker 的 `_get_random_transaction_price` 改调 `self._fill_price_model.calculate_fill_price(...)`。`slippage_tolerance` 留作 AttitudePricing 内部参数，**不与 SlippageModel 混淆**（本 ADR 强调两套概念边界）。

### D2 装配归一：engine_data.slippage 单点注入（回测 + 模拟盘）

`engine_data["slippage"]` 作为回测/模拟盘共享的滑点配置归一载体，工厂单点消费：
- **回测侧**：`build_engine_data` 已灌 `slippage_rate`（`task_helpers.py:34`，**无需改**）；`create_broker_from_config`（`infrastructure_factory.py:167`）读 `engine_data.slippage_rate` → 构造 `DeterministicSlippage` → 注入 `SimBroker(fill_price_model=...)`。**断点在此接通**。
- **模拟盘侧**：`PaperTradingWorker.assemble_engine`（`paper_trading_worker.py:86`）改注入 engine_data.slippage（从 `MPortfolio.slippage` 读）+ 经 FillPriceModel 装配 SimBroker（替代 :132 手写零参）。**与回测共用 FillPriceModel 路径**。
- **实盘**：不经 FillPriceModel（真 Broker 成交价由交易所定），另开 Epic。

### D3 存储：各随范式（R 方案）

- **回测**：`slippage_rate` 留 `config_snapshot` JSON（已 wire，ADR-018），不动。
- **模拟盘**：`MPortfolio` 加 `slippage` 独立列（长驻持续参数，与 `initial_capital`/`cash` 同范式）。**⚠️ 已被 Amendment 2 回退**：e2e 暴露 schema 漂移 + 共享 SimBroker 存N用1，改 GCONF 配置。
- **归一**：两者上游适配（回测 `build_engine_data` / 模拟盘 `assemble_engine`）都灌入 `engine_data.slippage`；D2 工厂单点消费。**认知统一在 D2 层（engine_data），不在存储物理层**——强行物理统一（P/Q）破坏一侧语义（任务快照 vs 长驻列）。

### D4 死代码清理：整体清理 TaskEngineBuilder（并入 B2）

经 spike 确认 `TaskEngineBuilder`（`trading/services/_assembly/task_engine_builder.py`，271 行）**完全可清理**，非"删方法保类"：

- 唯一公共方法 `build_engine_from_task:45` 零外部调用，其门面 `engine_assembly_service.build_engine_from_task:437-439` 也零外部调用；
- 构造函数 4 参数（:30）docstring 自注"保留接口，当前未直接使用"；`_task_engine_builder` 字段（`engine_assembly_service.py:160-165`）只服务死门面；
- 类内唯一的活引用 `assemble_live_portfolio`（:130 调用）是**共享 portfolio 加载器**，其真正活调用方在 `node.py:562`（实盘）与 `task_processor.py:255`（回测 portfolio 元数据加载，非 broker 装配），均不经 TaskEngineBuilder。

清理范围（8 处）：删整个类 + 删文件 + 删 `_assembly/__init__.py` 导出（:18 import + :24 `__all__` 条目）+ 删 `engine_assembly_service.py` 的 `_task_engine_builder` 字段（:160-165）与 `build_engine_from_task` 门面（:437-439）+ 删 2 个测试（`test_task_engine_builder_smoke.py` + `test_task_engine_builder_service_path.py`）。清理后回测装配链单一清晰（`assemble_backtest_engine` 工厂路径），降低未来归因成本（ADR-022 死抽象判定）。

## Considered Options

- **滑点接入**：
  - A `SimBroker` 同时跑 scipy 态度 + SlippageModel（串行叠加）：否决——两套语义叠加难解释、难测，`slippage_tolerance` 与 SlippageModel 双重滑点。
  - **B FillPriceModel 包装（本 ADR）**：单一切入点，AttitudePricing 保现状、DeterministicSlippage 接通 --slippage，二者互斥择一。
  - C 弃 scipy 态度、SimBroker 直接用 SlippageModel：否决——破坏回测现有成交价分布行为（大面积策略结果漂移），回测可信度断裂（违 ADR-036）。

- **存储统一**：
  - P `MPortfolio` 加 config_snapshot JSON 列（模拟盘也走快照）：否决——长驻参数塞进"任务快照"语义不自然 + 加 JSON 解析。
  - Q 回测 slippage 从 config_snapshot 提独立列：否决——破坏回测 JSON 范式（cash/commission 还在 JSON，独提 slippage 不一致）+ 改 wire（ADR-018）。
  - **R 各随范式 + D2 engine_data 归一（本 ADR）**：回测留 JSON / 模拟盘加列；认知统一在 D2。

- **装配归一范围**：
  - A 回测 + 模拟盘 + 实盘全统一：否决——实盘 Kafka + 真 Broker 架构差异大，滑点语义不同（交易所定 vs 模拟），强行统一抽象泄漏。
  - **B 回测 + 模拟盘（本 ADR，实盘另 Epic）**：两者都用 SimBroker（模拟成交），FillPriceModel 适用；实盘另开。

- **死代码处置**：并入 B2（本）/ 单独 chore issue / 不清。选并入（减 issue、B2 改装配链顺手）。

## Rationale

- **FillPriceModel 是 SimBroker 成交价的单一切入点**：把"成交价怎么算"从 SimBroker 内联 scipy 抽成可替换策略，AttitudePricing 保现状、DeterministicSlippage 接 --slippage，互斥不叠加——消除"两套滑点"混淆。
- **engine_data.slippage 是认知统一的真杠杆**：存储物理分裂（任务快照 vs 长驻列）反映执行语义，强行统一破坏建模；D2 在工厂单点消费 engine_data.slippage，回测/模拟盘上游各自适配，认知负担收敛在装配层而非存储层。
- **死代码清理防再误导**：TaskEngineBuilder 死路径曾导致 --slippage 断点误判（归因到死代码 :261），清理后装配链单一清晰，降低未来归因成本（ADR-022 死抽象判定）。
- **与 ADR-018/033 一致**：slippage_rate 留 wire spec（ADR-018）；模拟盘装配对称（ADR-033），D2 模拟盘注入 FillPriceModel 沿用 assemble_engine 装配契约。

## Sub-issues（#6851 Epic）

- **B1** FillPriceModel Protocol + AttitudePricing（移植 scipy）+ DeterministicSlippage（包装 SlippageModel）；SimBroker 改调
- **B2** engine_data.slippage 通路（`create_broker_from_config` 读 → FillPriceModel）+ 清 TaskEngineBuilder 死代码（D4）
- **A1** 模拟盘装配统一（`assemble_engine` 注入 engine_data.slippage + FillPriceModel）+ `MPortfolio.slippage` 列（D3）
- **B3** `--slippage` 端到端生效 + 态度采样行为零回归（测试）

## Amendment (2026-07-29): 方案B 显式 fill_price_policy

实现 B3 e2e 时暴露 D2 的设计冲突: D2 "create_broker_from_config 读 slippage_rate → DeterministicSlippage" 未处理 **slippage_rate 默认值 0.0001**——默认回测走 DeterministicSlippage 而非 AttitudePricing, 违背 D1 "回测行为零回归" 与 Considered C 否决理由 ("破坏回测现有成交价分布行为")。

### 决策: 分离"模型选择"与"率值"

新增 `fill_price_policy` 字段 (attitude/slippage), 与 `slippage_rate` (率值) 分离:

- **policy='attitude' (默认)**: AttitudePricing → 回测零回归 (默认不接通滑点, 保 scipy 态度采样分布)
- **policy='slippage'**: DeterministicSlippage(PercentageSlippage(slippage_rate)) → 显式接通 `--slippage`

工厂签名改为 `build_fill_price_model(policy="attitude", slippage_rate=None)`。向后兼容: 旧 config_snapshot / engine_data 无 `fill_price_policy` key → 默认 attitude (零回归, 旧快照可复现)。

### 各层落地

- **wire spec**: `config_snapshot.fill_price_policy` key; DTO `BacktestAssignmentConfig.fill_price_policy`; schema `EngineConfig.fill_price_policy` (均默认 "attitude")
- **状态主体**: `BacktestConfig.fill_price_policy` (required, ADR-018 纪律——新字段同样无默认, assignment 显式传全)
- **装配**: `build_engine_data` 灌入 `engine_data.fill_price_policy`; `create_broker_from_config` 传 `(policy, rate)` 给工厂
- **paper 侧**: 保留 A1 语义 (`slippage_rate` 推导 policy: 有值→slippage, None→attitude)。paper 是实时模拟盘无零回归约束, 不强制 policy 显式; `MPortfolio.fill_price_policy` 列留作后续增强

### 与 Considered C 的关系

方案B 不否定 Considered C (弃 scipy 态度)。C 否决的是"**默认**弃态度"; 方案B 保留 AttitudePricing 作**默认** (零回归), 仅在显式 `policy='slippage'` 时用 DeterministicSlippage, 二者互斥择一 (Considered A 否决叠加)。Epic 目标"--slippage 端到端生效"由"显式选择 policy='slippage'"达成, 而非 D2 原始的"默认 slippage_rate 接通"——后者会破坏零回归。

## Amendment 2 (2026-07-29): D3 回退 — 模拟盘 slippage 改 GCONF 配置（共享 SimBroker 存 N 用 1 + schema 漂移根因）

### 触发

B3 e2e 验证暴露 D3（`MPortfolio.slippage` 列）的两个致命缺陷：

1. **schema 漂移**：`MPortfolio.slippage` 列由 model 定义，但 MySQL 表无此列（`create_all` 只建表不 ALTER，ADR 纪律）。回测 `portfolio create` 的 INSERT 带 slippage 列 → `Unknown column 'slippage'` → 回测 portfolio create 全失败、e2e 阻断。mock smoke（`test_model_portfolio_slippage_smoke`）不命中 DB INSERT，完全漏检（同 arch_create_all_no_alter_drift 教训）。

2. **共享 SimBroker 存 N 用 1**（深度装配分析）：slippage 存 `MPortfolio`（per-portfolio）或 `MDeployment`（per-department）都导致"存多个值，worker 只用一个"——语义错配。

### 根因：共享 SimBroker → slippage 是 broker 级 = worker 级

paper worker 装配（`PaperTradingWorker.assemble_engine` INIT 路径）事实：
- 单 `TimeControlledEventEngine`（约 L152，单例）
- `broker = SimBroker(fill_price_model=...)` 在 portfolio 遍历**之外**建（循环外，约 L170，只建一次）
- 遍历所有 PAPER portfolio（约 L188）→ `engine.add_portfolio()`，**多 portfolio 共用同一 broker**

→ 一个 worker 一个常驻 SimBroker，一个 fill_price_model，一个 slippage。per-portfolio / per-department 存了多个 slippage，worker 只取一个（`_resolve_slippage_from_portfolios` 取 `db_portfolios[0]`），其余静默丢弃。运行时 deploy（`_handle_deploy`）更甚：只 add_portfolio 不重建 broker，T1+ deploy 的 slippage 进黑洞。严格是"存 N，用 ≤1"。

### 决策：回退 D3 + 模拟盘 slippage 改 GCONF 配置

- **回退 D3**：删 `MPortfolio.slippage` 列 + `update()` 的 slippage 分支。回测 portfolio create 不再带此列 → schema 漂移消除 → e2e 解阻。
- **GCONF 加 slippage 配置项**（paper worker 专属段，默认 None→attitude 零滑点）。
- **paper worker INIT 改读 GCONF**：`_resolve_slippage_from_portfolios` → 读 GCONF，配 SimBroker。方法语义不变（None→attitude / 有值→slippage），仅数据源从 MPortfolio 列换 GCONF。
- **回测不动**：slippage 仍走 `config_snapshot` JSON（per-task，ADR-018），经 `fill_price_policy` 显式（Amendment 1）。
- **deploy 命令不传 slippage**：运行时改不了已建 broker。

### 三方案对比（模拟盘 slippage 存储位置）

| 方案 | 与共享 SimBroker 语义 | schema 漂移 | 评价 |
|---|---|---|---|
| ~~MPortfolio.slippage（D3 原方案）~~ | 存 N 用 1 | ✅ 污染回测 portfolio create | 最差（已回退）|
| MDeployment.slippage | 存 N 用 1 | 仅 deploy 链路 | 次优（per-department 假象误导）|
| **GCONF（本方案）** | ✅ 一 broker 一值，存=用=1 | ✅ 零（脱离 DB）| 最优 |

### 回测/模拟盘分叉的架构依据（非疏忽）

- **回测 SimBroker 是 per-task**（每次回测新建，跑完弃）→ slippage per-task = `config_snapshot` JSON 合理。
- **模拟盘 SimBroker 是 worker 级常驻**（一个 worker 一个，挂多 portfolio）→ slippage worker 级 = GCONF 合理。
- 分叉反映 per-task vs worker 级 SimBroker 的执行语义差异，非设计疏忽。二者仍汇入同一个 `DeterministicSlippage` 适配器（D1 模型实现统一）——这才是 Epic "死深度 + 死参数" 修复本质（L0 模型实现 / L1 数值载体统一，L2 激活 / L3 存储各随范式）。
- 实盘（真 Broker）无 slippage（交易所定价），GCONF slippage 不影响实盘。

### 生效语义与限制

- GCONF slippage 改后需**重启 worker**（SimBroker 在 INIT 建一次，不热更）。
- 当前 slippage 是 **PercentageSlippage（固定百分比）**，非市场冲击模型——`成交价 = close × (1 ± 百分比)`，与订单量/深度/波动率无关。Epic 标题"死深度"实质只修了"抽象零 caller + 死参数"，未建模真实深度（平方根冲击等仍无实现，留后续）。

### 与 Amendment 1（方案 B）的关系

Amendment 1 的方案 B（显式 `fill_price_policy`）覆盖**回测侧**（config_snapshot + policy 显式）；本 Amendment 2 修订**模拟盘侧存储**（MPortfolio.slippage → GCONF）。paper 侧仍保留 A1 语义（slippage_rate 推导 policy：有值→slippage，None→attitude），只是 rate 来源从 MPortfolio 列改为 GCONF。
