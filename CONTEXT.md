# Ginkgo

事件驱动量化交易回测库。本文件统一核心数据对象的**角色语言**，避免 Entity / ORM Model / DTO / ValueObject 混称——这是项目反复踩坑的根源。

## Language

**Entity**:
有领域身份、承载业务行为与不变量的状态主体。
_Avoid_: Model、DataObject、"DTO"

**ValueObject**:
无领域身份、由字段值描述的领域内数据载体，不持有状态机。
_Avoid_: Entity（现状与之同承 Base，待分离）

**ORM Model**:
数据库表的映射对象（`M*` 前缀），状态的持久归宿。
_Avoid_: Entity、DTO

**DTO**:
跨边界、搬运有状态对象的状态投影、以**隔离两个不耦合世界**为目的的纯数据载体（无自身生命周期）。亚型：BusDTO(Kafka)、WebResponse(HTTP)、CacheEntry(Redis)。
_Avoid_: 把 ORM Model 或 ValueObject 称为 DTO

## Relationships

- **Entity 是状态的主体，DTO 是状态的信使，ORM Model 是状态的归宿。**
- 三者是同一业务对象的不同形态：DTO 不持有不变量，ORM Model 不持有行为，Entity 二者皆有。
- **ValueObject** 与 Entity 同属领域层，区别在有无身份；二者皆不可与 DTO 混称。

## Example dialogue

> **Dev:** "复权因子存哪？"
> **领域专家:** "它是 **ValueObject**——领域内的值，无身份。持久化时由 **Mapper** 转成 **ORM Model** 落表；表的 uuid 是存储键，不是领域身份。"
>
> **Dev:** "那发给交易所的订单呢？"
> **专家:** "订单是 **Entity**（有状态机）。跨进程发给交易所前要转成 **DTO**（OrderSubmissionDTO）——隔离中介，不带行为。"

## Flagged ambiguities

- `entities/__init__.py` 自称 "DTO" → 误称，应为 Entity / ValueObject。
- **Signal** 维持 **Entity**（代码现状 `Signal(TimeMixin,...,Base)` 有 uuid）；`docs/entity-lifecycles-and-flows.md` 的 "Signal as VO" 标为过时。
- "数据对象 / 视图" 泛指时，必须区分 **DTO** vs **ORM Model** vs **Entity**。

## 时间语义 (Time Semantics)

> 决策依据见 `docs/adrs/ADR-023`。系统中存在两种正确性标准不同的时间，**不共享一个 seam**（ADR-022 原则 3「单一接缝」的时间维度推论）。

**Business Time（业务时间）**：
事件链上的时间——信号/订单/bar/分析结果/持仓快照的发生时间。必须经 **TimeProvider**（`trading/time/`），由 `EXECUTION_MODE` 决定 `LogicalTimeProvider`（回测，bar 驱动）或 `SystemTimeProvider`（实盘，墙钟）。承载两个不变量：**回测可复现** + **防未来数据泄露**。组件经 `TimeMixin` 获 `now()`，且 `TimeMixin` 强制 provider-set（未设 `GLOG.ERROR`）并校验数据访问时间。
_Avoid_: 把业务时间戳写成 `datetime.now()`（回测下不可复现、绕过 `TimeMixin` 的防泄露校验）。

**Infra Time（基础设施时间）**：
进程/基础设施的时间——日志时间戳、心跳间隔、WS 重连退避、Redis TTL、Kafka 消息时间戳、scheduler 触发时刻。**刻意用 `datetime.now()`（墙钟）**，不经 TimeProvider，不归 `TimeMixin` 管。
_Avoid_: 把 infra 时间迁进 TimeProvider（与 Redis/交易所/Kafka 的真实墙钟契约冲突，逻辑时钟会制造错误）；把它误判为"违反唯一权威"的 bug 强行"修复"。

**Relationships**:
- Business Time 有两个真实 Adapter（`LogicalTimeProvider`/`SystemTimeProvider`，按模式切换）→ 真 seam（ADR-022 原则 2 存活门槛：≥2 实现者）；Infra Time 只有墙钟一 Adapter → **不构成 seam**。
- "一个时钟统一所有时间"是反模式：两种正确性标准不同的时间共享 seam，会让调用方无法判断某处 `now()` 是否会被逻辑时钟影响。分家后各查各的。
- 测试替身（scheduler 单测跳过 sleep）是 infra 组件的**内部 seam**（私有于自己的测试），独立于生产 TimeProvider——别混。

## Flagged ambiguities（时间）

- `TimeProvider` docstring 旧称"系统中唯一的时间权威，所有时间获取必须通过此接口"（`trading/time/interfaces.py:23-26`）——**已由 ADR-023 订正**为"业务时间的唯一权威"。infra 时间不归它管。
- `trading/livecore/workers` 的 ~74 处 `datetime.now()` 须按本节 triage：事件链上的（business）迁 `TimeMixin.now()`；infra 的（日志/心跳/TTL/退避）标注"刻意墙钟"锚点，非违规。
