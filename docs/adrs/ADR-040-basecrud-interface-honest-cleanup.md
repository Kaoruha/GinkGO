# ADR-040: BaseCRUD interface 诚实收口（授权 Base 类变更）

**Status:** Accepted
**Date:** 2026-08-05
**关联:** CLAUDE.md「禁改 Base 类」护栏 · ADR-002（分层架构 API→Service→CRUD→DB）· ADR-029（BaseCRUD 钩子族退役方向）· ADR-031（先例：破例改 Base 经授权）· ADR-032（CH 时序审计 vs MySQL 活状态——默认序字段选择依据）· Epic #6849 · 授权 issue #6883 · 首个 sub-issue #6884 / PR #6888

## Context

CLAUDE.md 明令「禁止擅自修改 Base 类（BaseCRUD/BaseService 等），在具体实现层处理」。BaseCRUD 作为 401 个 `find()` + 61 个 `modify()` 调用点的模板方法基类，其 interface（`find(order_by, desc_order, filters, ...)` / `modify(...)`）签名背后隐藏 7+ 个**未声明不变量**——调用方（service 层）必须知道并手写守卫，否则踩坑。锚点 2026-08-02 实测无漂移：

1. **find 默认无序**：`_do_find` 旧逻辑 `if order_by and hasattr(model, order_by)` 守卫，不传 `order_by` → SQL 无 ORDER BY → DB 默认序（通常取最旧）。`backtest_task_crud.get_by_task_id/get_by_uuid` 不传 `order_by` 取 `results[0]` → 重复行下取哪行不确定。
2. **`order_by="-end_time"` 倒序被静默忽略**：`hasattr(model, "-end_time")` 恒 `False`（Python 属性名不可 `-` 开头）→ 整个 ORDER BY 块跳过。`backtest_task_crud.get_completed_tasks` 的「倒序」是假的。
3. **未知 filter 字段静默丢弃**：`hasattr` 为 False → 该 filter 条件消失，查询范围意外放大。
4. **find 与 modify 不共享 filter DSL**：`_do_find` 用 `_parse_filters` 支持 `__like`/`__in` 等运算符；`_do_modify` 纯等值。
5. **ClickHouse `soft_remove` 实为硬删**：CH 不支持 UPDATE，`is_del` 标记路径在 CH 上是 DELETE。
6. **modify 隐式 stamp `update_at`**（base_crud.py:680-684，service 不知的副作用）。
7. **`__like` 双重 wrap**：`_parse_filters` 已包 `%` + 子类 `fuzzy_search` 再包 → `LIKE '%%q%%'`。

这些不变量「签名背后藏着」——interface 不诚实。service 层每处调用被迫手写守卫（传 `order_by`、校验 filter 字段、绕开 CH soft_remove），守卫遗漏即 bug（典型 drift 温床）。

**与 ADR-002 分层的关系**：ADR-002 定「API→Service→CRUD→DB」。本 ADR 不改分层，只把散落在 service 层的「BaseCRUD 行为守卫知识」**收回 CRUD 一层**——interface 自洽，service 不再被迫重复守卫。与 ADR-029（钩子族退役）方向一致：BaseCRUD 的隐式行为应显式化或消除，而非靠子类/调用方记住。

## Decision

### 原则 1 · 方向 1：interface 诚实收口（不变量收回 CRUD）

采用「interface 诚实收口」而非「调用方自行守卫」：把上述 7+ 不变量**收回 BaseCRUD interface 内**，让签名自洽——`find()` 默认有序且 docstring 化、未知字段响亮报错、find-modify 共享 filter DSL、CH soft_remove 显式失败。调用方不再被迫每处手写守卫。

### 原则 2 · 授权改 BaseCRUD（解除 CLAUDE.md「禁改 Base」对本 epic 的适用）

本 ADR 正式授权 Epic #6849 下各 sub-issue 修改 BaseCRUD。先例：ADR-031（enum 映射下沉 model 字段 `info`，破例改 Base 经授权并落地）。解除 CLAUDE.md「禁改 Base 类」护栏**仅对本 epic 范围内 BaseCRUD 的 interface 收口改动生效**——不构成对 BaseService 或其他 Base 类的通用解禁，亦不授权 BaseCRUD 的非 interface 性改动（如业务逻辑下沉）。

### 原则 3 · 迁移策略：phased per-sub-issue

401 find + 61 modify 调用点不可一次性 review。每个不变量独立 sub-issue，各自审计调用点 + 单测 + 行为变更评估，phased 推进。不强求 mega-PR。

### 原则 4 · Scope（本 ADR 覆盖的不变量）

| # | 不变量 | sub-issue | 状态 |
|---|---|---|---|
| 1 | find 默认有序 + `order_by="-x"` 前缀归一 | #6884 / PR #6888 | 首个，代码就绪待合（依赖本 ADR 授权） |
| 2 | 未知 filter 字段 raise（不静默丢） | 待立 | — |
| 3 | find-modify 共享 filter DSL | 待立 | — |
| 4 | ClickHouse soft_remove 显式报错 | 待立 | — |
| — | modify 隐式 stamp `update_at`（记入 scope，不单列 sub-issue） | 随 #3 | — |
| — | `__like` 双重 wrap（记入 scope，不单列） | 随 #3 | — |

## Rationale

- **为何收口而非 service 守卫**：守卫知识放错层——BaseCRUD 是行为发生地，却让 401 个调用方各自记住「要传 order_by」「filter 字段要校验」「CH 不能 soft_remove」。守卫遗漏即 bug，且 review 难以逐处发现。收口后真值单源在 CRUD，调用方零负担。
- **默认序字段选择 `business_timestamp → create_at → 无`**：依据 ADR-032「CH 时序审计 vs MySQL 活状态」分流——时序模型（MOrder/MSignal/MPosition 等 CH 审计流）有 `business_timestamp`，按业务时间倒序；关系模型（MStockInfo/MPortfolio 等 MySQL 活状态）经 `MMysqlBase` 有 `create_at`，按创建时间倒序；二者皆无的 CH 行情表（MBar/MTick/MTickSummary/MAdjustfactor/MFactor/MTransferRecord，只有 `timestamp`）回退不排序保持旧行为（这些表多按时间范围查，默认排序无收益且 CH 大表排序代价高）。
- **`-` 前缀与 `desc_order` 优先级**：`order_by="-x"` 剥离前缀后须为模型字段；`is_desc = desc_order or negated`——`-` 前缀或 `desc_order=True` 任一即倒序（显式倒序意图）。缺省 `order_by` 时 `desc_order` 被忽略（默认序已倒序，语义一致；docstring 标注「显式 order_by 时生效」）。
- **未知字段先 WARNING 回退、raise 留给后续**：首个 sub-issue 聚焦默认序 + `-` 前缀；未知字段 raise（scope 第 2 项）需对称收口 filter 字段，单立 sub-issue。WARNING 比「假装排了序」诚实。

## Consequences

正面：
- BaseCRUD.find 默认「最新在最前」——消除「静默取最旧」语义 bug，401 调用点中依赖原序的（唯一键查找）不受影响。
- `order_by="-end_time"` 倒序真正生效（`get_completed_tasks` 的函数名语义变真）。
- 后续 4 项不变量收口有 ADR 授权依据，无需逐 sub-issue 重开「能否改 Base」讨论。

负面 / 风险：
- **行为变更爆炸半径**：缺省 `order_by` 的 find 调用从「无序」变「默认有序」。MySQL 表加 `ORDER BY create_at`（通常有索引，影响小）；CH 时序表无 `business_timestamp`/`create_at` 者回退不排序（无影响）。401 调用点审计：绝大多数是唯一键查找或已显式传 `order_by`，行为变更集中在「依赖取最旧 / 对序无感」的 `results[0]`/`page_size=1` 类——这些本就想要最新，修正符合预期。
- **性能**：默认 ORDER BY 对大表有排序代价。已通过「无时间戳字段模型回退不排序」规避 CH 行情表；MySQL `create_at` 有索引。后续若发现热点查询受影响，可显式传 `order_by=None` 禁用（待 scope 第 2 项收口时考虑）。
- **distinct_field 分支不受影响**：`_do_find` 的 DISTINCT 查询分支（`order_by == distinct_field` 独立守卫）与常规分支互斥，命中即 return，`_resolve_order` 不介入——DISTINCT 单列查询按其他列排序无 SQL 语义。

首个 sub-issue（#6884 / PR #6888）代码就绪——落地原则 1 的第 1 项不变量 + 9 项单测，`tests/unit/data/crud/` 633 passed 零回归（10 failed 经 master base 实测比对全为既有）；待本 ADR 合并授权后合入 #6888。
