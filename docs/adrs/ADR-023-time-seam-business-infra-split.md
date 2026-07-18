# ADR-023: 时间 Seam 边界（Business Time 走 TimeProvider，Infra Time 走墙钟）

**Status:** Accepted
**Date:** 2026-07-18
**关联:** 候选源自 `/improve-codebase-architecture` 评审 + 拷问；术语见 `CONTEXT.md`「时间语义」；细化 ADR-022 原则 3（单一接缝）的时间维度；同族先例 ADR-011（信号发射 seam）/ ADR-019（feeder 价格发布 seam）；关联 memory `arch_timeprovider_exists_46_bypass`。

## Context

`TimeProvider`（`trading/time/interfaces.py:22`，原 `ITimeProvider`，#6713 去 `I*` 前缀）docstring 主张："**系统中唯一的时间权威，所有时间获取必须通过此接口。避免组件直接使用 datetime.now() 造成时间不一致**"——即 universal authority（下称方案 c）。

经 grep/Read 核实（master base，2026-07-18），现实与 docstring 主张有落差：

- **Seam 已部分强制**（非全瘫痪）：`TimeMixin`（`entities/mixins/time_mixin.py`）经 `set_time_provider()` 注入后，`now()` 走 provider；provider 未设则 `GLOG.ERROR`（time_mixin.py:166）；`set_current_time()` 含时间倒退检查（防回退）；且 `can_access_time()` 路径在 TimeMixin 内校验数据访问时间（:359 "Cannot validate data access time"）——**防未来数据泄露 invariant 已接线**。
- **多注入点**（非只回测）：`time_controlled_engine.py`（回测）、`paper_trading_worker.py:246-262,721`（模拟盘，replay_provider + real_provider，分别灌 portfolio 与 feeder）、`client/validation_cli.py:715`（校验）、`engine_bindable_mixin.py:50`（组件绑定引擎时顺带注入）。实盘/模拟经 `SystemTimeProvider`/`real_provider` 也注入，非恒 None。
- **~74 处 `datetime.now()` 绕过**（`trading` + `livecore` + `workers`）：分布——livecore/scheduler ~20、`trading/interfaces/mixins` 13、workers 11、gateway 6、strategies 5、feeders 5、evaluation 5、其余散落。这些 bypass **既绕过回测可复现、也绕过 TimeMixin 的防泄露校验**。

三种可能的不变量边界：

| 方案 | 范围 | 评价 |
|---|---|---|
| (a) 回测可复现 | 业务时间戳由 provider 决定 | 真 invariant |
| (b) 防未来数据泄露 | 策略取数不越过当前 bar 时间（`can_access_time`） | 真 invariant，TimeMixin 已实现 |
| (c) 通用时间权威 | 连日志/心跳/TTL 都走 provider | **假 invariant**（见 Rationale） |

docstring 喊 (c)，接口设计（`can_access_time`/`advance_time_to`）暗示 (a)+(b)。三者不该共享一个 seam——(a)(b) 是业务时间，(c) 混入了 infra 时间。

判定三条全中（难逆转 / 反直觉 / 真实取舍），立本 ADR。

## Decision

**两种时间不共享一个 seam**（ADR-022 原则 3「每类操作一个权威接缝」的时间维度推论：业务时间是一类操作，infra 时间是另一类）：

### 1. Business Time（业务时间）→ 经 TimeProvider

信号/订单/bar/分析结果/持仓快照的发生时间。经 `TimeProvider`，由 `EXECUTION_MODE` 选 `LogicalTimeProvider`（回测，bar 驱动）或 `SystemTimeProvider`（实盘，墙钟）。组件经 `TimeMixin.now()` 获取，享强制 provider-set + 防泄露校验。承载不变量 (a)+(b)。

**两个真实 Adapter**（按模式切换）→ 满足 ADR-022 原则 2 存活门槛（≥2 实现者），是真 seam。

### 2. Infra Time（基础设施时间）→ 刻意墙钟

日志时间戳、心跳间隔、WS 重连退避、Redis TTL、Kafka 消息时间戳、scheduler 触发时刻。**刻意留在 `datetime.now()`**，不经 TimeProvider，不归 `TimeMixin`。

**只有一个 Adapter（墙钟）**→ 不构成 seam（ADR-022 原则 2：单实现不立抽象）。强行收编 = 假接缝 + 间接层零收益。

### 3. docstring 订正

`TimeProvider` docstring（interfaces.py:23-26）由"**系统中唯一的时间权威，所有时间获取必须通过此接口**"改为"**业务时间的唯一权威，事件链上的时间获取必须通过此接口；infra 时间（日志/心跳/TTL/退避）刻意用墙钟，不归本接口**"。同步订正 `clock.py` 顶部 Role 注释。

### 4. 现存 ~74 处 `datetime.now()` triage（非全违规）

- **Business bypass（真 bug，迁）**：事件链上的——strategies/feeders/evaluation/gateway 中决定信号/订单/bar/分析时间戳处。迁 `TimeMixin.now()` 或 `clock.now()`。
- **Infra（刻意墙钟，标注豁免）**：livecore/scheduler（WS/心跳/退避）、workers（Redis/调度）、日志时间戳。加注释锚点 `# infra time: wall-clock by design (ADR-023)`，防静态扫描/后人误判为违规。
- **死代码里的**（如 `trading/interfaces/mixins` 的 13 处若在死 mixin）随死代码清理，不单列。

triage 明细与执行门见关联 issue（构建中）。

## Rationale

- **删除测试否定方案 (c)**：删掉 (c)（infra 不走 provider）复杂度直接消失——infra 调用方继续 `datetime.now()`，行为不变；反过来把 infra 塞进 provider，复杂度只搬进 provider 内部、调用方零收益 → (c) 是穿透层，不挣钱。
- **两个 Adapter 原则**：业务时间有 `Logical/System` 两 Adapter（真 seam）；infra 时间只有墙钟一 Adapter（假 seam）。强加间接只赔不赚。
- **infra 与外部系统签真实墙钟契约**：Redis TTL/WS 退避/Kafka 时间戳必须真秒数；逻辑时钟冻结则永不过期、加速则错乱。回测里把它们喂逻辑时钟是主动制造错误，不是统一。
- **"一个时钟"是表象简单、实质更乱**：两种正确性标准不同的时间塞进同 seam，调用方须猜"这个 `now()` 会不会被逻辑时钟影响"。分家后各查各的，心智模型反而清晰。这是对 ADR-022 原则 3 的精准应用：原则 3 要求"每类操作一个权威入口"，而业务时间与 infra 时间是**两类操作**，本就该两个入口（其中 infra 那个入口就是裸 `datetime.now()`）。
- **测试替身诉求是内部 seam，非生产 provider**：scheduler/退避的单测想跳过 sleep → 给该 infra 组件注入一个假时钟（**内部 seam**，私有于自己的测试，LANGUAGE.md 概念），不是把 infra 收进生产 TimeProvider。今天 livecore 几乎无此类单测，诉求目前假设，不预付。

## Consequences

- **`CONTEXT.md`** 新增「时间语义」节：Business Time / Infra Time 定义 + Relationships + Flagged ambiguities（docstring 订正 + triage 口径）。
- **docstring/注释订正**：`TimeProvider`（interfaces.py:23-26）、`clock.py` Role 注释。
- **infra 豁免锚点**：infra 调用点加 `# infra time: wall-clock by design (ADR-023)`，配合未来 CI 静态扫描（若有）白名单。
- **business bypass 迁移**：~十余处迁 `TimeMixin.now()`/`clock.now()`（范围/门见 issue）；不动 `TimeProvider`/`TimeMixin` 接口签名。
- **不与既有 ADR 冲突**：
  - **ADR-022 原则 3（单一接缝）**：本 ADR 是其时间维度细化，非冲突——"业务时间一个权威入口"正是原则 3 的实例（同 ADR-011/019 的 `publish_price_update` 范例同族）。
  - **ADR-003（引擎二态）**：`BACKTEST`/非 `BACKTEST` 与本 ADR 的 `Logical`/`System` provider 切换同构，互补。
- **未决（与本 ADR 正交，单独处理）**：(b) 防泄露 `can_access_time()` 在 TimeMixin 内已实现，但 bar 数据读取路径是否全经该校验——需另查 feeder/data 取数路径，不在本 ADR 范围。

## 判定标准自检

- ① **难逆转**：infra "刻意墙钟"豁免标注 + docstring 作废，未来 dev/CI 须据此判断某处 `datetime.now()` 是否违规——中等。
- ② **反直觉**：见 ~74 处 `datetime.now()` 会想"违反唯一权威，该批量修"——本 ADR 解释为何 infra 处是设计、business 处才是 bug——满足。
- ③ **真实权衡**：方案 (c) 通用权威 vs (a)+(b) 业务时间分家（**本 ADR**）——选后者，有删除测试 + 两 Adapter 原则支撑——满足。
