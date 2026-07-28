# ADR-033: PaperTradingWorker INIT/deploy 装配对称契约

**Status:** Accepted
**Date:** 2026-07-28
**关联:** ADR-003（引擎二态）、ADR-017（事件订阅归组件）；固化 memory `arch_paper_worker_init_deploy_assembly_symmetry`（#6473 修复）。

## Context

`PaperTradingWorker`（`workers/paper_trading_worker.py:40`，1 Worker = N PAPER Portfolio）有**两条装配 portfolio 的路径**：

- **INIT 冷启动** `assemble_engine()`（`:86-240`）：批量装配，建共享 `BacktestFeeder`/`SimBroker`/`TradeGateway`/`ComponentLoader`，per-portfolio 装配 + 状态 restore + REPLAY/LIVE_PAPER mode 识别。
- **运行期 deploy** `_handle_deploy()`（`:858-972`）：Kafka 命令热加载单 portfolio，复用已挂引擎的共享组件。

两者装配的是**同一个 engine 同一个 portfolio**，行为必须不可区分。已知陷阱 #6473：deploy 路径漏调 `_seed_selectors` → 新 portfolio 的 selector `_interested` 永空 → 不发 `EventInterestUpdate` → `BacktestFeeder._interested_codes` 永不收该 portfolio → 喂 0 bar → **0 signal/order，但 DB state=RUNNING、心跳正常，静默无交易**，仅 worker 重启走 INIT 才自愈。

## Decision

### 1. 单 portfolio 装配六步，两路径必须一致

`collect_portfolio_components` → `PortfolioT1Backtest()` → `perform_component_binding` → `engine.add_portfolio` → **`_seed_selectors`** → 状态置 RUNNING/restore。

### 2. 对称关键点 `_seed_selectors` 抽为共用 helper

`_seed_selectors`（`:833-856`）是 #6473 抽出的对称化修复。INIT（`assemble_engine` 第 7 步，`:186-188`）与 deploy（`_handle_deploy`，`:942-944`，注释 "#6473: …与 INIT 启动路径 assemble_engine 第 7 步对称"）**都必须调用**。

### 3. 不强行合并两路径

INIT 还承担：共享组件创建（feeder/gateway/loader 进程级一次性，`:131-138`）+ persisted state restore + REPLAY/LIVE_PAPER mode 识别（`:190-245`）；deploy 永远是"新部署 RUNNING"，复用已挂引擎的共享组件（`:890` 取 container）。生命周期差异是必要的，强行合并会引入"冷热分支"。

## Rationale

两路径装配同一 engine 同一 portfolio，漏任一步（尤其 `_seed_selectors`）会导致状态正常但静默无交易——这种"安静失败"最危险（状态/心跳全绿）。对称契约用共用 helper 保障，而非强行合并路径（合并反而稀释对称契约的可读性）。

## Consequences

**正面**：deploy 热加载与 INIT 冷启动行为对齐，消除 0-signal 静默陷阱。

**负面 / 权衡**：
- 新增单 portfolio 装配步骤须**同步改两处**（INIT + deploy），否则对称破坏。
- `_seed_selectors` 含 #6159 陷阱：`pick(time=None)` → `None-timedelta` 崩，须传 `datetime.now()`。

## Alternatives considered

- **A. 统一 `_assemble_single_portfolio(portfolio_id)` 共享函数**：scope 不对齐（INIT 进程级共享组件 vs deploy 复用），且 INIT 有 restore/mode 判定维度，deploy 无——统一须引入"是否首次"分支，稀释可读性。**否决**，改为抽共用 helper（`_seed_selectors` + `perform_component_binding` + `collect_portfolio_components`）保留必要差异。

## 实证锚点

- INIT 全流程：`paper_trading_worker.py:86-240`（单 portfolio 装配 L141-178，`_seed_selectors` L186-188）
- deploy 全流程：`paper_trading_worker.py:858-972`（对称 `_seed_selectors` L942-944）
- 共用 helper `_seed_selectors`：`:833-856`（含 #6159 陷阱）
- 命令分发：`_handle_command` `:1031-1055`
- ExecutionNode（LIVE 节点，独立 worker，非本文"双路径"所指）：`execution_node/node.py:53-90`
