# ADR-032: 持久化模型基类分流（CH 时序审计 vs MySQL 活状态）

**Status:** Accepted（含⚠️现状偏离，待决）
**Date:** 2026-07-28
**关联:** ADR-006（多数据库角色分工）、ADR-034（signal 跨库同名，本 ADR 的具体实例）；细化 memory `arch_portfolio_persistence_audit_vs_live_gateway`。

## Context

回测与活路径（模拟/实盘）的订单、信号、持仓、分析记录如何落库，常被误以为"按引擎类型分库"（回测写 CH、实盘写 MySQL）。实际分叉发生在**模型基类**：时序审计记录多重继承 `MClickBase` → ClickHouse（MergeTree append-only），关系活状态继承 `MMysqlBase` → MySQL（行级 UPDATE）。

## Decision

### 1. 模型基类决定落库

- `MClickBase`（`MergeTree(order_by=("timestamp",))`，`model_clickbase.py:31,42`）→ ClickHouse。
- `MMysqlBase`（`model_mysqlbase.py:30`）→ MySQL。

### 2. CH 时序审计表（`_record` 后缀，append-only）

`MSignal`、`MOrderRecord`、`MPositionRecord`、`MAnalyzerRecord`——回测与活路径的"每次状态变更 = 新行"流水都写 CH。

### 3. MySQL 活状态表（无后缀，可 UPDATE）

`MOrder`、`MSignalTracker`——为"查某订单最新状态 / 幂等检查"设计，行级 UPDATE。

### 4. 订单流水回测与活路径同一条 CH 路

`result_service.create_order_record` → CH `order_record`，回测（`t1backtest.py:528-529`）与活路径（`trade_gateway.py:337-338`）**同表同 CRUD**。分叉不在引擎类型，在模型层。

## Rationale

CH `MergeTree` 无 UPDATE、append 极快、列式压缩，契合单次回测 10K–1M 事件的流水语义（MySQL 行锁会成瓶颈）；但"查某订单最新状态"在 CH 须 `ORDER BY timestamp DESC LIMIT 1`，对活路径状态查询不友好——这正是 MySQL 活状态表（行级 UPDATE）的初衷。合库牺牲一方。

## Consequences

**正面**：审计流水高性能 append；活状态查询走关系索引。

**⚠️ 现状偏离（须挂 issue，非本 ADR 决策的一部分）**：
master 上 **MySQL 活状态表的写入点几乎全被注释**，设计意图的双库分叉当前为"CH 单一活跃写入 + MySQL 设计残留"：
- `src/ginkgo/livecore/trade_gateway_adapter.py:184-185,207-208`（MOrder 幂等/状态更新注释）
- `src/ginkgo/livecore/data_sync_service.py:454`（`# order_crud.update_order(order)` 注释）
- `src/ginkgo/workers/execution_node/node.py:1121-1123`（`# order_crud.insert(event)` 注释）

后果：活路径"最新态查询"正退化成 CH 流水尾查。须决（二选一，挂 issue 跟踪）：
1. **重新接线** MySQL 活状态写入（恢复 `MOrder`/`MSignalTracker` 活路径写入）；或
2. **正式废弃** `MOrder`/`MSignalTracker`，走 CH-only，并从 Model 层删除。

> memory `arch_portfolio_persistence_audit_vs_live_gateway` 的"MySQL 活状态走 TradeGateway"描述需据此修正为"MySQL 写入当前休眠"。

## Alternatives considered

- **A. 统一一库**：CH 不擅 UPDATE（活状态退化），MySQL 不擅时序 append（审计变慢）。**否决**。
- **B. 当前 CH-only 事实状态升为正式决策**：可作为备选，但需明文废弃 MySQL 活状态表（见上 #2）。**待决**。

## 实证锚点

- 模型基类：`src/ginkgo/data/models/model_clickbase.py:31,42` / `model_mysqlbase.py:30`
- CH 模型：`model_signal.py:28`、`model_order_record.py:29`、`model_position_record.py:25`、`model_analyzer_record.py:25`
- MySQL 模型：`model_order.py:26-28`、`model_signal_tracker.py:36`
- 回测写入：`t1backtest.py:116`（持仓）/`:482-483`（信号）/`:528-529`（订单）；路由 `result_service.py:648,673-676,686,709-712`
- 活路径写入：`trade_gateway.py:317-365`
- SyncBroker 桥：`src/ginkgo/trading/brokers/sync_facade.py:27`（异步 Broker↔同步回测管线）
