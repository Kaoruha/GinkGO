# ADR-010: 数据对象三层角色分离（Entity / ORM / DTO）与独立 Mapper 流转

**Status:** Accepted
**Date:** 2026-06-13
**关联:** #6106（架构评审总览）· #6112（entities 不变量）· #6117（转换层深化）· #3865（反向依赖）；细化 ADR-002，区分于 ADR-001（组件边界）/ ADR-009（BaseCRUD/BaseService）。术语定义见仓库根 `CONTEXT.md`。

## Context

`src/ginkgo/entities/` 一个包塞了三种角色不同的对象，却贴同一个"DTO"标签、共用带 uuid 的 `Base`。经代码（`grep`/`Read`）核实，现状病根：

- **双套转换并存**（真病灶，非"散落"）：套 A——`Entity.from_model/to_model`（11 个 entity 内嵌，6 个 CRUD 内部调用**直接返 Entity**）；套 B——`ModelConversion`+`ModelList`+`ModelCRUDMapping`（注册式，**`BaseCRUD` 通用查询路径默认返 `ModelList`**，调用方 `.to_entities()`/`.to_dataframe()` 惰性转换）。同一 CRUD 层两套机制分裂；且 `ModelList` 是 BaseCRUD 默认返回类型（非 tick/user/file 边缘特性），全删必触改 BaseCRUD。
- **标签错位**：`__init__.py` 自称"DTO"，但 `Order`/`Position` 是带状态机的聚合根、`Bar` 有计算行为——按 `CONTEXT.md` 定义它们是 **Entity**，非 DTO。
- **Entity 越界持久层**：11 个 entity 内嵌 `to/from_model`，方法体内 `from ginkgo.data.models import M*`（延迟 import 无模块级循环，但逻辑层认识了持久层，#3865 源头）。
- **DTO 概念笼统**：DTO 实际分布在三处且用途各异——`interfaces/dtos/`（**Kafka 载荷**，12 个全是消息体）、`data/services/*_schemas.py`（**HTTP 响应**，`api/schemas/` 不存在）、`data/redis_schema.py`（**Redis 缓存**）。笼统称"DTO 传输层"模糊了三者差异。
- **不变量失守方式被误判**：初版诊断"删 Order/Position 裸 setter"——但 `grep` 证实 `Order.volume` setter 被 5+ 个 Risk 组件调用（margin/volatility/liquidity/position_ratio/profit_target），是组件边界（ADR-001）定义的**合法调整通道，不能删**。

判定三条全中（难逆转 / 反直觉 / 有取舍），立本 ADR。

## Decision

### 1. 三层角色定位（详见 `CONTEXT.md`）

| 层 | 对象 | 职责 | 禁止 |
|---|---|---|---|
| 逻辑层 | **Entity**（Bar/Order/Position/Signal） | 业务行为+不变量，**状态的主体** | import ORM/DTO；内嵌转换 |
| 逻辑层 | **ValueObject**（Adjustfactor/Tick 等 8 个） | 无身份的领域值载体 | 身份（uuid）；状态机 |
| 持久层 | **ORM Model**（M*） | 表映射，**状态的归宿** | 业务逻辑；上总线 |
| 边界层 | **DTO** | **状态信使**：跨边界搬运状态投影、隔离两个不耦合世界 | 业务行为；内嵌转换；直接接 ORM |
| 边界 | **Mapper** | 唯一转换点，**独立于 CRUD** | 含业务规则；依赖 CRUD |

DTO 三亚型按介质分：**BusDTO**（Kafka）、**WebResponse**（HTTP）、**CacheEntry**（Redis）。

### 2. 依赖方向（铁律）

**Entity/ValueObject 零外部依赖**：禁 `import ginkgo.data.models`、`ginkgo.interfaces.dtos`。ORM/DTO 可单向依赖 Entity。**Mapper 独立于 CRUD**——只依赖 Entity+ORM+DTO，不 import CRUD。**ModelList 不出 Service 边界**——它是 ORM 容器，client/trading/research 禁接触（禁 import、禁持有），Service 是其唯一消费终点。

### 3. 流转规则（CRUD 返 ORM，Service 为枢纽）

```
外部数据源(DataFrame)                  API / Kafka / Redis
   │ mappers.py(并入)                       ▲ ▼ DTO
   ▼                                        │
┌──────────┐  CRUD(返ORM)  ┌──────────┐ Mapper ┌──────────┐
│ORM Model │ ◄───────────► │ Service  │ ◄────► │  Entity  │
│ MBar/... │   ModelList   │ (枢纽)   │        │ Bar/Order│
└──────────┘               └──────────┘        └──────────┘
```

- CRUD **只懂表**，出口返 ORM ModelList，不转 Entity/DTO。现状套B 已部分实现，6 个套A CRUD 本次统一。
- **Service 是 ModelList 终点**：拿到 ModelList 后用 Mapper 转，对外只返 DF/DTO/Entity（三种 `ServiceResult.data` 形态），**禁透传 ModelList**。
- **Service 返型契约（类型即契约，禁鸭子探测）**：按消费语义提供多出口方法——`get_xxx_df()`→DF、`get_xxx()`→List[Entity]、`get_xxx_dto()`→DTO。调用方按意图调对应方法，`ServiceResult.data` 类型由方法名决定，禁 `hasattr(result.data, "to_dataframe")` 运行时探测。
- Service 用 Mapper 编排；**Entity 按需构造**（纯展示读可 ORM→DTO 跳过 Entity）。
- 六条路径（转换均经 Mapper）：①读-展示 ORM→DTO ②读-业务 ORM→Entity→DTO ③写 DTO→Entity→ORM→CRUD ④总线发 Entity→DTO ⑤总线收 DTO→Entity ⑥外部数据源 DataFrame→ORM。

### 4. 转换收敛到独立 Mapper；ModelList 瘦身（不全删）

- 新建 `data/mappers/XxxMapper`（每 entity 一个），**Entity 转换矩阵**：`from_model`/`to_model`/`from_dto`/`to_dto`/`model_to_dto`（ORM→DTO 直转，路径①）。**不依赖 CRUD**。**不含 `to_dataframe`**——DF 出口留在 CRUD。
- **ModelList 瘦身而非全删**（`ModelList` 由 `BaseCRUD` 构造返回，全删必触改 BaseCRUD，违反铁律）：
  - **删 Entity 转换**：`ModelList.to_entities()`、`ModelConversion.to_entity()`（16 处调用点改 `Mapper.from_models(model_list)`——`ModelList` 是 list 子类可直传）。
  - **留 DF 出口（仅 Service 内部）**：`ModelList.to_dataframe()`、`ModelConversion.to_dataframe()`、`ModelCRUDMapping`（DF 路径 `get_crud_instance` 仍需要）。**DF 出口只供 Service 内部用**——Service 转 DF 后对外返，client/trading 不接触 ModelList。
  - **DataFrame 模拟方法**（`first/count/filter/empty/shape/head/tail`）：grep 证实调用方几乎未用（dead code），瘦身时一并删，缩小 ModelList 表面积。
  - **不删 CRUD mixin `_convert_to_business_objects`**（Entity 钩子）：触 Base 边界，留作 dead code（不盲目删）。
- Entity/DTO 类内抹掉一切转换方法（含 `Bar.to_model`、`BarDTO.from_bar`）。
- 套 C（`data/mappers.py` 外部数据源入站）保留，并入 `data/mappers/`。
- **热路径**：回测 Bar 读走 `ModelList.to_dataframe()`（批量、不经 Entity），不碰 Mapper。

### 5. 字段变更分治（替代"一刀切删 setter"）

`grep` 证实并非所有 setter 都是漏洞。按字段语义分治：

| 字段类 | Order | Position | 处理 |
|---|---|---|---|
| 状态机 | status（本无 setter） | 结算状态 | 只读+行为方法（已如此） |
| 可调整（有外部活跃调用） | volume→**`adjust_volume()`** | price→**`update_price()`** | 包装行为方法；~10 处 Risk/broker 调用点迁移 |
| 创建后不变/关联键 | code/limit_price/fee/direction/order_type/portfolio_id/engine_id/task_id | portfolio_id/engine_id/task_id | 构造注入，删 setter |
| 内部行为已覆盖 | frozen_*/transaction_*/remain | volume（`deal()` 已管）/realized_pnl | 删 setter |

**uuid（身份不变量）**：构造注入（`Base.__init__(uuid=...)` 保留）、**创建后只读**——删 `Base.uuid.setter` + `set_uuid()`（`grep` 证实业务零调用）。

> ⚠️ **关键修正**：初版"删 Order 裸 setter"会摧毁风控。`Order.volume` 是 Risk 合法通道（ADR-001），必须保留为 `adjust_volume()` 行为方法——仅迁移调用点、不删除能力。

### 6. ValueObject 基类（VO 无 uuid）

- 新增 `entities/value_object.py: class ValueObject`：无 uuid / 无 component_type / 无 source。
- 8 个数据 VO 迁继承：Adjustfactor/TradeDay/Mapping/StockInfo/Transfer/Tick/FileInfo/CapitalAdjustment。其中 FileInfo 无 to/from_model（仅改继承）；其余 7 VO + 4 Entity 共 11 个待迁转换（V1）。
- **VO 无 uuid 字段**——持久化时 ORM `MClickBase.uuid`（`default=lambda: uuid4().hex`）自动生成，业务键 `(code,timestamp)` 定位，uuid 不污染领域 VO。
- **Signal 维持 Entity**（代码现状 `Signal(TimeMixin,...,Base)` 有 uuid）；`entity-lifecycles-and-flows.md` 的 "Signal as VO" 标过时。
- 组件（Strategy/Portfolio/Engine/Risk/Sizer）继续 `Base`，不受影响。
- 本 ADR 只调整数据 entity 继承分流，**不修改 `Base`/`BaseCRUD`/`BaseService` 本身**（ADR-009）。

### 7. 正名与归类

`entities/__init__.py` 的"DTO"标签改为"领域实体（Entity）与值对象（ValueObject）"。`IdentityUtils` 移出 `entities/`（→ `libs/`）。

## Rationale

- **独立 Mapper + ModelList 瘦身，而非全删**：`ModelList` 是 `BaseCRUD` 默认返回类型（不只 tick/user/file），全删必触改 BaseCRUD（违反铁律）且爆破 79 处（`to_dataframe` 63 + `to_entities` 16）。真实诉求是"CRUD 不做 Entity 转换"，非"消灭 ModelList"——故瘦身：Entity 转换移 Mapper（16 处），DF 出口留 CRUD（63 处不动）。代价：迁移 16 处 `to_entities`、Entity/DTO 抹内嵌转换。
- **字段分治而非全删 setter**：`Order.volume` 是组件边界（ADR-001）定义的 Risk 调整通道，删了摧毁风控。分治保留调整能力（行为方法）同时堵不变量漏洞。
- **VO 无 uuid**：ORM `MClickBase.uuid` default 兜底 + 业务键定位，uuid 对 VO 是装饰，去掉让"无身份"定义真正落地。
- **CRUD 返 ORM**：职责单一，Entity 按需构造，省聚合根实例化成本。

## Consequences

**违规→目标清单（#6112 验收：违规点标注）**

| # | 现状违规 | 目标 |
|---|---|---|
| V1 | 11 个 Entity 内嵌 to/from_model（**20 方法**） | 迁 `XxxMapper`（20 方法迁出） |
| V2 | Entity 方法内 import data.models | 随 V1 消除 |
| V3 | 6 个 CRUD from_model 返 Entity（套A） | 改返 ORM ModelList；转换归 Service+Mapper |
| V4 | Position.volume setter | 删（`deal()` 已管） |
| V5 | Order setter | **分治**：volume→`adjust_volume()`（迁 Risk 调用点）；其余删 |
| V6 | `__init__.py` "DTO" 标签 | 正名 |
| V7 | IdentityUtils 误入 entities/ | 移 libs/ |
| V8 | VO 强加 uuid | ValueObject 基类（无 uuid） |
| V9 | ModelList/ModelConversion 做 Entity 转换（越界） | 瘦身：删 `to_entities/to_entity`（16 处改 Mapper）；删 dead 模拟方法；DF 出口留（仅 Service 内） |
| V10 | Base uuid.setter + set_uuid() | 删（构造注入只读） |
| V11 | Service 透传 ModelList 给 client/trading（stockinfo 等） | 不透传：Service 内 Mapper 转 DF/DTO/Entity 对外；~35 处外部 `to_dataframe()` 改 `result.data` |
| V12 | trading `hasattr(result.data,"to_dataframe")` 鸭子探测返型（data_preparer/selectors/engine_assembly ~7 处） | 改 Service 多出口方法明确调用（`get_xxx_df()`/`get_xxx()`），类型即契约 |

**执行顺序（单分支，每步测试门）**

1. 建 `data/mappers/`，迁 11 个 to/from_model + DTO 内嵌转换 → `XxxMapper`；Entity/DTO 抹转换。
2. 新增 ValueObject 基类，8 VO 迁继承。
3. 6 个套A CRUD 改返 ORM ModelList。
4. ModelList 瘦身 + Service 不透传 + 返型契约：删 `to_entities`/`to_entity`（16 处改 Mapper）+ 删 dead 模拟方法；Service 按消费语义提供多出口方法（`get_xxx_df`/`get_xxx`/`get_xxx_dto`），禁透传 ModelList、禁 hasattr 探测（~35 处外部 `to_dataframe()` + ~7 处 hasattr 改明确方法调用）。
5. 字段分治：删 Base uuid setter；Order/Position setter 分治（volume→`adjust_volume` 迁 Risk ~10 处；其余删）。
6. 正名 `__init__.py`；移 IdentityUtils。

**风险与边界**

- 全量测试 OOM（~20GB）：主门用分模块测试 + 关键回测路径，全量终验。
- 热路径（Bar 大量读）Mapper 性能：批量转换，避免逐条。
- Risk 调用点迁移（~10 处）：每处确认语义，`adjust_volume()` 行为方法保留原调整能力。
- pass-through VO 在"CRUD 返 ORM"下存在性存疑——本次保留，标后续删除候选。
- Order 状态机驱动方缺失归 #6107。
- **ModelList 瘦身方案直接源于 BaseCRUD 约束**：`ModelList` 由 `base_crud.py` 构造返回，全删即改 BaseCRUD；瘦身（删 Entity 转换、留 DF）是唯一不触铁律的路径。**严格不透传**：ModelList 封闭在 CRUD↔Service，爆破 ~51 处（to_entities 16 + 外部 to_dataframe 35），换来 client/trading 与持久层解耦。
- 不修改 `Base`/`BaseCRUD`/`BaseService` 本身（ADR-009）。

## 验收（对齐 #6112）

- [x] 不变量文档化 → 本 ADR + `CONTEXT.md`
- [x] 违规点清单标注 → V1-V10
