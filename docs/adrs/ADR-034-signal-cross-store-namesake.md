# ADR-034: signal 跨库同名陷阱（CH 事件流 vs MySQL tracker）

**Status:** Accepted（含⚠️现状偏离，待决）
**Date:** 2026-07-28
**关联:** ADR-032（模型基类分流，本文是其 signal 维度实例）、ADR-006（多数据库角色分工）；细化 memory `arch_signal_ch_vs_tracker_mysql`。

## Context

"signal" 在 Ginkgo 里同时是 **CH 时序事件流表名**、**MySQL tracker 的关联字段名**。同一 signal uuid 在两库语义不同，查询时按"signal"模糊调用会错库——count 与列表结果完全不同；CH 主键叫 `uuid`、tracker 字段叫 `signal_id`（值同），按错字段名查直接报错。

## Decision

### 1. MSignal（CH，`signal` 表，`MClickBase`）

append-only 时序事件流，记录"信号本身"（portfolio_id/code/direction/volume/strength/confidence/business_timestamp），策略每次触发即追加一行，按时间范围扫描。**所有场景（回测/模拟/实盘）都写**。

### 2. MSignalTracker（MySQL，`signal_tracker` 表，`MMysqlBase`）

可变状态机，记录"信号执行追踪"（expected_*/actual_*/tracking_status/notification_sent_at/execution_confirmed_at/reject_reason），`NOTIFIED→EXECUTED/TIMEOUT` 状态流转需 UPDATE。**仅模拟/实盘写**（`account_type` 区分 0=回测 / 1=模拟 / 2=实盘；回测不建 tracker）。

### 3. 跨库关联无 JOIN

`MSignalTracker.signal_id`（`model_signal_tracker.py:35`）→ 引用 `MSignal.uuid`（`model_clickbase.py:47`），跨库不能 JOIN，须两步查。

## Rationale

CH signal 是 append-only 时序（高写、按时间扫描，靠 MergeTree `order_by timestamp`）；MySQL tracker 是可变状态机（频繁 UPDATE `actual_*`/`execution_confirmed_at`、按 `tracking_status` 索引查询）。访问模式截然不同，合库牺牲一方。

**陷阱根源在"同名"而非"分库"**——分库是正解，但 `signal` 一名两用让调用方容易错库。

## Consequences

**正面**：事件流与状态机各得其所。

**查询陷阱（须在 service 层防御）**：
- 按"signal"语义模糊调用：CH 返事件流、MySQL tracker 返状态机，结果不同。
- 须用显式命名（`find_ch_signal_by_uuid` / `find_tracker_by_signal_id`），或将 tracker 改名 `signal_execution_tracker` 消歧（待定）。

**⚠️ 现状偏离（与 ADR-032 一致，待决）**：
`MSignalTracker` 的服务/CRUD 完整，但 master 上**找不到非 test、非注册的真实调用点**——写入实质休眠。与 ADR-032 的 MySQL 活状态休眠同根：重新接线或正式废弃，二选一（挂同一 issue）。

## Alternatives considered

- **A. 合一单表**：CH 不擅 UPDATE（状态机退化）、MySQL 不擅时序 append（事件流变慢）。**否决**。
- **B. tracker 改名 `signal_execution_tracker` 消歧**：可行，缓解同名陷阱，不改变分库决策。**待定**（若保留 MySQL tracker 路线则建议执行）。

## 实证锚点

- 模型：`model_signal.py:26-28`（`MSignal(MClickBase, MBacktestRecordBase)`）/ `model_signal_tracker.py:25,32,35`（`MSignalTracker(MMysqlBase)`，`signal_id` 字段）
- CRUD 分流：`crud/signal_crud.py:24` / `crud/signal_tracker_crud.py:25`
- DI 独立注册：`data/containers.py:169,171`（两 crud key）/ `:263-269`（两 service）
- Service 自承：`services/signal_service.py:123`（`#5009：… MSignal 为 ClickHouse`）
