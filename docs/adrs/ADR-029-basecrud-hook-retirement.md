# ADR-029: BaseCRUD 转换钩子族退役,Entity↔ORM 收敛到 Mapper

**Status:** Accepted
**Date:** 2026-07-26
**Revision:** 2026-08-02 合 master。适配 ADR-031(PR #6823)落地后的现状:Mapper 反向入路命名 `to_model`→`entity_to_model`、`__table__` 反射独立性、§4 前提 1 已就绪(11/11)。决策原意不变。
**关联:** 修订 ADR-010 §4(钩子处理条款)· 承 ADR-009 line 28(Base 保护)的 ADR 背书例外 · ADR-025 原则 1 / 步骤 ⑤(DB Mapper 收尾)· **ADR-031**(enum 映射下沉,让 Mapper 经 `__table__` 反射独立于 CRUD)· Epic E #6701(CRUD/Mapper seam 集中化)· 审计 issue #6629 · 执行 issue #6298

## Context

ADR-010 §4(2026-06-13)对 BaseCRUD mixin 转换钩子族定下「**瘦身而非全删**」策略,原文:

> ModelList 由 BaseCRUD 构造返回,全删必触改 BaseCRUD(违反 ADR-009 line 28 铁律);故**不删 CRUD mixin `_convert_to_business_objects`**(Entity 钩子):触 Base 边界,**留作 dead code(不盲目删)**。

当时的判断正确:瘦身是「不触 ADR-009 line 28 的唯一路径」,冒进全删属 AFK 擅动受 ADR 保护的 Base。此后两步落地,逐步断开钩子族的外部调用方:

- **ADR-010 第 4 阶段 Task 4.1**(commit `ef8a1ca3`,2026-06-14):删 `ModelList.to_entities()`/`to_entity()` 懒转换入口 + 4 个 mock(filter/empty/shape/tail),改 4 处调用方切 Mapper。断开钩子族的 ModelList 调用方。
- **commit `8b32a25f`**(2026-07-11,#6628):删 `CRUDResult` 类本体。断开钩子族的 CRUDResult 调用方。

**现状(2026-07-26 立稿,#6629 审计核实;2026-08-02 Revision 更新):**

| 维度 | 现状 |
|---|---|
| 钩子族定义 | BaseCRUD mixin:`_convert_to_business_objects` / `_convert_models_to_business_objects` / `_convert_input_item` / `_convert_input_batch` / `_convert_output_items` / `_convert_enum_values` / `_convert_models_to_dataframe`(`src/ginkgo/data/crud/mixins/_conversion.py`) |
| 活跃内部调用 | `base_crud.py` 5 处(`add_batch` / `_do_add_batch` / `find` / `_parse_filters` / batch 入站) |
| 子类 override | **32 个 CRUD** 重写 `_convert_input_item` 做各自 Entity→ORM 入站转换(2026-08-02 实测) |
| **外部调用方** | **零**(ModelList / CRUDResult 两路已断) |
| 出站 Model→Entity 调用方 | **mapper 已活跃**(6 处:`bar_service`/`stockinfo_service`(ADR-010 出口样板)+ `portfolio_base`/`validation_cli`/`backtest_feeder`×2);CRUD 出站 hook(`_convert_models_to_business_objects`)0 override = 死路 |
| 入站 Entity→Model 调用方 | **mapper 几乎未用**(仅 `portfolio_base:845` 1 处);32 CRUD `_convert_input_item` override 是活路径;转换落点须迁到 **Service 写路径**(非 CRUD 内部) |
| Mapper 方法就绪 | 11 个 DB Mapper 全有 `entity_to_model`/`model_to_entity`(由 #6823/ADR-031 落地,经 `__table__` 反射独立于 CRUD);仅 `cache_mapper`(Redis dict↔wire 边界)无,本就不需要 |

ADR-025(2026-07-24)立 **Mapper 家族覆盖四边界**,DB 边界 `XxxMapper` 承担 ORM↔Entity↔DTO。立稿时 11 个 Mapper **只有 `from_model`(ORM→Entity 出路),缺 `to_model`(Entity→ORM 入路)**——故 CRUD 入库仍走 `_convert_input_item` 钩子,钩子族无法退役。**此 gap 已由 #6823(ADR-031,2026-07-28 合并)补齐**:Mapper 改名 `entity_to_model`/`model_to_entity` 并经 `__table__` 反射 enum 映射,**独立于 CRUD**(不 import CRUD)——§4 前提 1 就绪,钩子族退役的唯一技术阻塞已消除。

**死活混杂治理僵局**:钩子族里有的活(内部调用 + 32 子类 override)、有的死(外部调用方已断);ADR-010 §4「留作 dead code」+ ADR-009 line 28「禁擅改 Base」锁死不可删 → 治理卡住。case-by-case 标 `deprecated` 既不统一又难追踪(用户反馈:「为了架构,应该统一,别区分那么细了」)。

判定三条全中(难逆转 / 反直觉 / 有取舍),立本 ADR 收口。

## Decision

### 1. 钩子族整体退役,转换统一收敛到 Mapper

Entity↔ORM 转换**由 Mapper 家族(DB 边界 `XxxMapper`)单一承担**,BaseCRUD mixin 转换钩子族**整体退役**(非一钩子一判)。一个机制管全部,呼应 ADR-025 原则 1「每边界一个权威转换点」+ ADR-022 原则 3「单一接缝」。

**转换调用方为 Service 层**(CRUD 只读写 Model,不持有转换,呼应分层架构 ADR-002「API→Service→CRUD→DB」):入站 `service 调 mapper.entity_to_model(entity)` → `crud.add(model)`;出站 `crud.find()` → ModelList → `mapper.models_to_entities()` → 返 Entity。`bar_service`/`stockinfo_service` 已是出站样板(ADR-010 出口②),入站待按同模式补齐。

退役范围:`_conversion.py` 钩子族 + 32 子类 override + `tick_crud` 等私有 `_convert_to_*`(`tick_crud` 作 `MTick`(`__abstract__`=True)抽象模型例外,经审计确认全为 Entity↔ORM 转换职责,无其他语义)。

### 2. 修订 ADR-010 §4(部分修订,非整篇 superseded)

ADR-010 §4 钩子处理条款「**不删 CRUD mixin `_convert_to_business_objects`:触 Base 边界,留作 dead code(不盲目删)**」**修订为**:

> CRUD mixin 转换钩子族(`_convert_to_business_objects` 等)**授权退役**,Entity↔ORM 转换统一由 Mapper 家族承担。退役前提:Mapper 补 `entity_to_model` 反向入路。详见 ADR-029。

ADR-010 其余部分(三层角色定位、依赖方向铁律、流转规则、字段分治、ValueObject 基类、ModelList DF 出口、正名归类)**不变**,仍 Accepted。V9(ModelList/ModelConversion Entity 转换越界)的瘦身已完成(Task 4.1),本 ADR 收口其遗留的 mixin 钩子。

### 3. 对 ADR-009 line 28 的关系(Base 保护的 ADR 背书例外)

ADR-009 line 28「重构时禁止擅自修改 Base 类」原则**不变**。本 ADR 是 line 28 立下以来**首次对 BaseCRUD mixin 本体的 ADR + HITL 背书变更**——非 AFK 擅动,属 line 28 允许的例外。

> line 28 防的是「累积技术债的擅动」,非「Base 本身不可演进」。退役钩子族是经审计(#6629)+ HITL(本文档)背书的有意收敛,正是 line 28 要拦的反面。

退役必须遵循本 ADR §4 前置条件与顺序;**任何绕过前置条件的 Base 改动仍违规**。

### 4. 前置条件(不可省,缺一不可)

1. **Mapper `entity_to_model` 反向入路** ✅ **方法已就绪**(2026-08-02 实测):11 个 DB Mapper 全有 `entity_to_model`。由 #6823(ADR-031)落地,Mapper 经 `__table__` 反射 enum 映射,**不 import CRUD**(独立性)。**注意**:方法就绪 ≠ 调用方已切换——当前入站仅 `portfolio_base` 1 处用 mapper,32 CRUD 仍走 `_convert_input_item` hook;§5.3 的工作 = 把这 32 处的调用方从 CRUD hook 迁到 Service 写路径。此项 = ADR-025 步骤 ⑤ DB Mapper 收尾 / Epic E #6298 DB seam。
2. **契约测试锁**:转换行为(字段映射、枚举转换、batch 语义)先有契约测试,退役前后行为一致方算通过。呼应 ADR-025 原则 2「严格模式」+ CLAUDE.md「失败必须响亮」。**(此项覆盖率待 §5.3 分批迁移前核)**

### 5. 退役顺序(门禁串联,不可跳步)

1. ~~Mapper 补 `entity_to_model` 反向(§4 前提 1)~~ ✅ 已就绪(#6823/ADR-031)→ 契约测试就位(§4 前提 2,**待核**)
2. ✅ **本 ADR 生效**(本文档 Accepted,本 PR 合 master 即生效)
3. ⏳ 分批迁移:32 个 CRUD `_convert_input_item` override 的转换逻辑迁到 **对应 Service 写路径**(`service 调 mapper.entity_to_model(entity)` → `crud.add(model)`),删 CRUD override,每批跑该域测试门(**未开始**)
4. ⏳ Base mixin 钩子本体最后删(此时全仓零调用方)
5. ⏳ 验收:转换单一走 Mapper,`grep` 钩子族零定义零调用

## Rationale

- **为何现在收敛(非停在 ADR-010 §4「留 dead code」)**:ADR-010 当时留 dead code 是因条件未备——ModelList 全删触 Base、Mapper 家族未立。此后 ADR-025 Mapper 家族覆盖四边界 + Service 多出口已落实 + Task 4.1 / `8b32a25f` 断开外部调用方 + #6823(ADR-031)补齐 Mapper 反向入路并独立于 CRUD,**收敛条件已成熟**。继续「留 dead code」= 持续维护死活混杂的认知税。
- **为何整体退役非一钩子一判**:钩子族职责单一(Entity↔ORM 转换),无混合语义;case-by-case 标 `deprecated` 既不统一(用户已拒)又难追踪。一个机制管全部,呼应 ADR-022 原则 3。
- **为何需 Mapper 补反向入路前提**:入库是 32 CRUD 的活跃路径,退役入库钩子(`_convert_input_item`)前必须先有 Mapper 替代,否则断入库(呼应 #4652:宁响亮 `raise`,不静默 stub 兜底)。**此前提已由 #6823 满足。**
- **为何经 ADR 背书而非直接改 Base**:ADR-009 line 28 保护 Base,非 Base 不可演进,而是防 AFK 擅动累积债。退役钩子族是经审计 + HITL 背书的有意重构,非擅动——正是 line 28 要拦的反面。
- **三条全中**:① 难逆转(转换机制单一化一旦立,回退即重引入死活混杂)② 反直觉(钩子族零外部调用方却不删?因 ADR 保护,非无用)③ 真实取舍(整体退役 vs 留 dead code / 经 ADR 背书 vs 擅改 / 补 Mapper 反向 vs 断入库)。

## Consequences

- **转换机制单一化**:Entity↔ORM 全走 Mapper,DB 边界转换真相源唯一,消除 32 子类重复 override。
- **与 ADR-025 步骤 ⑤ 合流**:本 ADR 是步骤 ⑤(DB Mapper 收尾)的授权前置;步骤 ⑤ 执行 = 本 ADR §4 前提 1(✅)+ §5 顺序 3-5 落地。
- **对 Epic E #6701 的连带**:串成主线 `#6629(审计) → ADR-029(本文档,授权) → #6298 + #6117 + #6469(收口迁移)`。
- **对 ADR-010 的标注**:ADR-010 顶部加「§4 钩子处理条款修订见 ADR-029」,其余不变。
- **退役期风险**:每批迁移须跑该 CRUD 测试门(全量测试 OOM,分批 + xdist `-n auto`);热路径(Bar 大量读)Mapper `entity_to_model` 批量转避免逐条(呼应 ADR-010 §4 热路径)。
- **删除测试(ADR-025 同款验收)**:退役后转换集中到 Mapper,删任一 Mapper 即断该 CRUD 转换 = Mapper 在发挥作用,非 pass-through;退役前钩子族同理。
