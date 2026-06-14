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
