# ADR-036: 回测 fill 时序无后视（T+1 延迟队列 + 两阶段推进）

> **编号说明（2026-07-28）**：原拟 ADR-031，与 #6823 的 `ADR-031-enum-mapping-field-info-sink` 撞号，遂顺延至 ADR-036。

**Status:** Accepted
**Date:** 2026-07-28
**关联:** ADR-003（引擎二态）、ADR-019（feeder 价格发布 seam）；细化并固化 memory `arch_backtest_fill_t1_no_lookahead`。

## Context

回测可信度的核心质疑是"是否偷看未来"（lookahead）。Ginkgo 回测（`PortfolioT1Backtest`）的 fill 时序常被误审为"可能用当日收盘价成交"，每次回测审计都要重查 fill 项。

实际引擎层用 **延迟队列 + 两阶段推进** 物理切断 lookahead 路径——任意 fill 天然满足"t 日信号 → t+1 日成交"，无需逐笔核。本 ADR 固化此结论，把 fill 维度从"每次必审"降为"架构免审"。

## Decision

### 1. 信号延迟入队（不进下单链）

`on_signal` 收到 t 日信号时，若 `business_time >= current_time`，入 `self._signals` 延迟队列后 `return`，**不进 sizer/risk/order 链**（`t1backtest.py:271-319`）。

### 2. 两阶段推进（Feeder 先于 Portfolio）

引擎 `advance_time` 先推 Feeder（产 t+1 价入 `BrokerCacheMixin`），再推 Portfolio；Portfolio 步骤 4 批量重发上期延迟信号（`t1backtest.py:142-215`、`time_controlled_engine.py:482-528`）。重发时 sizer→risk→order→SimBroker 全链路的环境**已是 t+1 价**。

### 3. SimBroker 用 t+1 bar 成交

`sim_broker.py:292` 用 `market_data`（t+1 bar 的 high/low/close）算成交价；broker 缓存由 `EventPriceUpdate` 流入更新（`broker_cache_mixin.py:102-150`）。

### 4. A 股 T+1 卖出解冻

持仓结算队列 `process_settlement_queue` 在 T+1 解冻可卖持仓（`t1backtest.py:154-165`、`position.py:333` 结算天数 0=T+0 / 1=T+1 配置）。

## Rationale

延迟队列把"信号生成"与"成交"物理隔离到不同时间步；两阶段推进保证 broker 缓存价在 Portfolio 处理信号**前**已被 t+1 价覆盖。fill 不可能引用 t 日 close——路径被切断，不是约定。

## Consequences

**正面**：
- fill 项审计免查：任意 fill 满足 t→t+1，回测可信度争议中 fill 维度免审。
- A 股 T+1 制度与防未来函数双重约束自然统一。

**负面 / 权衡**：
- 当日信号永不当日成交：A 股 T+1 制度 + 防未来函数双约束下，引擎无"当日信号当日成交"的活路径。
- 历史回放补单分支（`business_time < current_time`）等价补单，非当日成交。

## Alternatives considered

- **A. 即时成交（T+0，signal 同 bar fill）**：引入未来函数风险，且 A 股制度不允许 T+0 卖出。**否决**。
- **B. 批处理路径（`_batch_processing_enabled`）**：与 T+1 共存于代码（`t1backtest.py:280-296`），是另一条优化路径，非 T+1 的替代。**共存**。

## 实证锚点

- `src/ginkgo/trading/portfolios/t1backtest.py:65`（`_signals` 延迟队列）/ `:142-215`（advance_time 两阶段）/ `:271-319`（on_signal T+1 判定）
- `src/ginkgo/trading/engines/time_controlled_engine.py:482-528`（Feeder→Portfolio 两阶段推进）
- `src/ginkgo/trading/brokers/sim_broker.py:292`（t+1 bar 成交价）
- `src/ginkgo/trading/bases/broker_cache_mixin.py:102-150`（行情缓存）
- `src/ginkgo/entities/position.py:333`（结算天数配置）
