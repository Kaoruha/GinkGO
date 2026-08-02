# ADR-029: Entity↔ORM 全链路收敛到 Mapper,BaseCRUD 转换钩子族退役

**Status:** Accepted
**Date:** 2026-08-02
**Revision:** 2026-08-02 从「分步退役 + 留 dead code + 门禁串联」**重写**为「全链路替换 + 契约保证可用 + 不留 dead code」。原版未合 master,重写无历史包袱。决策原意(钩子族退役、转换收敛 Mapper)不变,执行策略从保守分步改为全链路一次到位。
**关联:** 修订 ADR-010 §4(钩子处理条款)· 承 ADR-009 line 28(Base 保护)的 ADR 背书例外 · ADR-025 原则 1 / 步骤 ⑤(DB Mapper 收尾)· **ADR-031**(enum 映射下沉,让 Mapper 经 `__table__` 反射独立于 CRUD)· Epic E #6701(CRUD/Mapper seam 集中化)· 审计 issue #6629 · 执行 issue #6298

## Context

ADR-010 §4(2026-06-13)对 BaseCRUD mixin 转换钩子族定下「**瘦身而非全删**」策略,原文:

> ModelList 由 BaseCRUD 构造返回,全删必触改 BaseCRUD(违反 ADR-009 line 28 铁律);故**不删 CRUD mixin `_convert_to_business_objects`**(Entity 钩子):触 Base 边界,**留作 dead code(不盲目删)**。

此后两步落地,断开钩子族的外部调用方:

- **ADR-010 第 4 阶段 Task 4.1**(commit `ef8a1ca3`,2026-06-14):删 `ModelList.to_entities()`/`to_entity()` 懒转换入口 + 4 个 mock,改 4 处调用方切 Mapper。断开 ModelList 调用方。
- **commit `8b32a25f`**(2026-07-11,#6628):删 `CRUDResult` 类本体。断开 CRUDResult 调用方。
- **#6823(ADR-031,2026-07-28 合并)**:11 个 DB Mapper 全有 `entity_to_model`/`model_to_entity`,经 `__table__` 反射 enum 映射,**独立于 CRUD**(不 import CRUD)。§4 前提 1(反向入路方法)就绪。

**2026-08-02 全链路调研核实**(为本次重写提供事实基础,详见执行 issue #6298 调研报告):

### 关键机制发现

- **`_convert_input_item` 只被 `add_batch` 触发**(`base_crud.py:192`/`504` 经 `_convert_input_batch` `_conversion.py:94`);`add(entity)`(`base_crud.py:170` → `_do_add:488`)**不触发**,只做 `_validate_item_enum_fields`。即**入站隐式 Entity→Model 转换只在批量写路径**;`add(entity)` 对纯 Entity 是潜在 bug 路径(直传 SA session)。
- **出站 hook `_convert_models_to_business_objects` 已 0 override**(默认 `return models`)。出站 mapper 化已落地 7 处(`bar_service:814`/`stockinfo_service:496`/`backtest_feeder:239,334`/`strategy_data_mixin:158`/`portfolio_base:903`/`validation_cli:751`)。

### 32 个 `_convert_input_item` override 三分类

| 类 | 数量 | 代表域 | 迁移成本 |
|---|---|---|---|
| **空实现**(`return None` / 已是 Model 则透传) | 8 | `user_credential`/`user_group*`/`user_contact`/`user`/`live_account`/`market_subscription` | **零**(直接删,`_convert_input_batch` 的 `isinstance(item, model_class)` 分支已处理透传) |
| **纯字段映射 + 枚举 + 默认值** | 13 | `bar`/`stockinfo`/`trade_day`/`param`/`engine`/`handler`/`engine_portfolio_mapping`/`engine_handler_mapping`/`portfolio_file_mapping`/`portfolio`/`position`/`tick_summary`/`adjustfactor` | **低**(mapper 补字段缺口后替代) |
| **特殊逻辑**(非纯 setattr) | 11 | `tick`(动态表分发)/`signal_tracker`(4 路多态)/`order`(双触发条件)/`order_record`(跨类型)/`transfer*2`/`signal`/`capital_adjustment`(dict+对象)/`position_record`(dict+对象)/`file`(string→enum 手工表)/`factor`(只接 dict) | **中-高**(逐域核实) |

### 真活域(有 `add_batch` 调用方传 Entity)

- **5 个可直迁**:`bar`(`bar_service:197`)、`tick`(`tick_service:215`)、`stockinfo`(`stockinfo_service:225,265,274`)、`trade_day`(`trade_day_service:161,171,206,218`)、`position`(`position_service:37,176`)。均有 service 写方法 + mapper 已存在。
- **2 个阻塞**:`signal`、`order`。mapper 有,但 `signal_service`/`order_service` **无写方法**(只 find/remove/count),需先建 `add`/`save`。
- **1 个特殊**:`factor`。override 只接 dict/Series 不接 Entity(`factor_crud:94-116` 转 `_create_from_params`),不属于 Entity→Mapper 范式。

### 死代码域(无 `.add()`/`.add_batch()` 写调用方,override 实质死代码)

`transfer`/`transfer_record`/`position_record`/`order_record`/`tick_summary`/`capital_adjustment`/`handler`/`market_subscription`。写路径只经 `.create(**kwargs)`(走 `_create_from_params`,不经 `_convert_input_item`)。

### Mapper 缺口(逐域核实,差异是字段缺失,非逻辑分歧)

| Mapper | 缺口 | override 有 mapper 无 |
|---|---|---|
| `BarMapper` | `source`(私有 `_source`)、`uuid` 还原 | `bar_crud:88,100` |
| `SignalMapper` | `business_timestamp`、`source` 兜底 SIM | `signal_crud:130` |
| `PositionMapper` | `source`、`business_timestamp` | `position_crud:133` |
| `StockInfoMapper` | `market`(自承丢失 bug,`stockinfo_mapper:35-37`) | — |
| `SignalMapper` | `uuid`(自承丢失 bug,`signal_mapper:55-57`) | — |

判定三条全中(难逆转 / 反直觉 / 有取舍),立本 ADR 收口。

## Decision

### 1. 全链路收敛到 Mapper(CRUD 只读写 Model,不持有转换)

呼应分层架构 ADR-002「API→Service→CRUD→DB」:

- **入站**:`service 调 mapper.entity_to_model(entity)` → `crud.add(model)` / `crud.add_batch(models)`。
- **出站**:`crud.find()` → `ModelList` → `mapper.models_to_entities()` → 返 Entity。
- CRUD 只读写 ORM Model,不调任何 DB Mapper,不做 Entity 转换。

`bar_service`/`stockinfo_service` 已是出站样板(ADR-010 出口②);入站待按同模式补齐。

### 2. 钩子族 + 32 override 全删(不留 dead code)

**与原版「留 dead code 分步」不同,本版目标明确:全删。** 退役范围:`_conversion.py` 钩子族 + 32 子类 override + 私有 `_convert_to_*`(`tick_crud` 动态表逻辑迁调用方)。分类执行(详见 §5):

- 空实现(8)+ 死代码域(8):**直接删**,零运行时风险。
- 活域纯映射(5):补 mapper 缺口 → 契约 → 迁调用方 → 删 override。
- 阻塞域(2 signal/order):先建 service 写方法 → 补 mapper → 契约 → 迁 → 删 override。
- 特殊域 factor:保留 hook 或扩 `FactorMapper` 加 `dict_to_model`(语义特殊,本就不接 Entity,不强制塞进 Entity→Mapper 范式)。
- mixin 本体:全仓零调用方后删。

### 3. 保证可用:契约测试锁每域行为

每域迁移**前置**:契约测试锁定 Entity↔Model 转换行为(字段映射、枚举转换、默认值、batch 语义),迁移前后行为一致方算过。呼应 ADR-025 原则 2「严格模式」+ CLAUDE.md「失败必须响亮」。

调研证实 mapper 与 override 差异**是字段缺失(source/uuid/business_timestamp),非逻辑分歧**——契约测试能精确锁住这些差异,迁移时补全字段即通过。

### 4. 修订 ADR-010 §4(部分修订,非整篇 superseded)

ADR-010 §4 钩子处理条款「**不删 CRUD mixin `_convert_to_business_objects`:触 Base 边界,留作 dead code(不盲目删)**」**修订为**:

> CRUD mixin 转换钩子族(`_convert_to_business_objects` 等)**授权退役**,Entity↔ORM 转换全链路由 Mapper 家族单一承担。退役前提:Mapper 补 `entity_to_model` 反向入路 + 字段缺口、契约测试锁行为。详见 ADR-029。

ADR-010 其余部分(三层角色定位、依赖方向铁律、流转规则、字段分治、ValueObject 基类、ModelList DF 出口、正名归类)**不变**,仍 Accepted。V9(ModelList/ModelConversion Entity 转换越界)的瘦身已完成(Task 4.1),本 ADR 收口其遗留的 mixin 钩子。

### 5. 对 ADR-009 line 28 的关系(Base 保护的 ADR 背书例外)

ADR-009 line 28「重构时禁止擅自修改 Base 类」原则**不变**。本 ADR 是 line 28 立下以来**首次对 BaseCRUD mixin 本体的 ADR + HITL 背书变更**——非 AFK 擅动,属 line 28 允许的例外。

> line 28 防的是「累积技术债的擅动」,非「Base 本身不可演进」。退役钩子族是经审计(#6629)+ 全链路调研 + HITL(本文档)背书的有意收敛,正是 line 28 要拦的反面。

退役必须遵循本 ADR §4 前置条件与 §5 顺序;**任何绕过前置条件的 Base 改动仍违规**。

## 前置条件(不可省,缺一不可)

1. **Mapper 反向入路 + 字段缺口补全** ✅ **方法已就绪**(2026-08-02 实测):11 个 DB Mapper 全有 `entity_to_model`(#6823/ADR-031 落地,经 `__table__` 反射独立于 CRUD)。⏳ **字段缺口待补**:逐域补 `source`/`uuid`/`business_timestamp`/`market` 等(调研已列出每域缺口,§Context 表)。**注意**:方法就绪 ≠ 调用方已切换 ≠ 字段已对齐。
2. **契约测试锁**:每域迁移前先有契约测试锁 Entity↔Model 转换行为,退役前后行为一致方算过。**(逐域就位,§5 顺序 2)**
3. **阻塞域 service 写方法**:`signal_service.add`/`order_service.add` 作为迁移前置先行补建。**(§5 顺序 4 前置)**

## 退役顺序(按域分批,门禁串联,目标全删)

1. ⏳ **补 Mapper 字段缺口**(批量 PR):逐域 `entity_to_model` 补 `source`/`uuid`/`business_timestamp`/`market`(调研缺口表),修 `stockinfo_mapper` market 丢失 / `signal_mapper` uuid 丢失自承 bug。
2. ⏳ **建契约测试**(每域):锁 Entity↔Model 转换字段/枚举/默认值/batch 语义。
3. ⏳ **活域分批迁移**(5 域,每域:迁调用方到 `service 调 mapper.entity_to_model → crud.add(model)` → 删 CRUD override → 跑该域测试门):`bar` → `tick` → `stockinfo` → `trade_day` → `position`。`position` 迁移兼修 `add(entity)` 不触发转换的潜在 bug(改 `add(mapper.entity_to_model(pos))`)。
4. ⏳ **阻塞域迁移**(2 域):先建 `signal_service.add`/`order_service.add` 写方法 → 补 mapper 字段 → 契约 → 迁调用方 → 删 override。`order` 保留 `frozen_volume=int()` 防御(#6087);`order` 双触发条件(`isinstance(Order) or hasattr(portfolio_id)`)语义决策随迁移定。
5. ⏳ **死代码 + 空实现批量删**(16 个):8 空实现 + 8 死代码域 override 直接删,零运行时风险;死代码域写路径统一 `.create()`。
6. ⏳ **factor 特殊处理**:保留 hook 或扩 `FactorMapper` 加 `dict_to_model`(本就不接 Entity,不强制塞范式)。
7. ⏳ **Base mixin 钩子本体删**(`_conversion.py`):全仓零调用方后。
8. ⏳ **验收**:`grep` 钩子族零定义零调用;转换单一走 Mapper。

## Rationale

- **为何全链路替换非分步留 dead code**:32 override 是虚高印象——真活域仅 5+2+1,8 空实现 + 8 死代码可零成本删。原版「留 dead code」是因当时条件未备(ModelList 全删触 Base、Mapper 家族未立、反向入路缺);此后 ADR-025 Mapper 家族覆盖四边界 + Task 4.1/`8b32a25f` 断开外部调用方 + #6823 补齐反向入路并独立于 CRUD + 本次全链路调研摸清 32 override 三分类,**全链路替换条件已成熟**。继续「留 dead code」= 持续维护死活混杂的认知税。
- **为何契约测试非影子运行/灰度开关**:调研证实 mapper 与 override 差异是字段缺失(source/uuid/business_timestamp),非逻辑分歧——契约测试能精确锁住;mixin hook 删后无法影子运行(新旧不能并行);灰度开关引入配置复杂度与双份维护。契约测试是最小代价的最大保障。
- **为何内建 signal/order service 写方法**:此二域 mapper 全有,只缺 service 写方法;不内建则永卡 hook,与「全链路」目标冲突。内建是迁移前置,非范围蔓延。
- **为何需 Mapper 补字段缺口前提**:入库是活域活跃路径,退役入库钩子前必须先有 Mapper 替代且字段对齐,否则断入库或丢字段(呼应 #4652:宁响亮 `raise`,不静默 stub 兜底)。
- **为何经 ADR 背书而非直接改 Base**:ADR-009 line 28 保护 Base,非 Base 不可演进,而是防 AFK 擅动累积债。退役钩子族是经审计 + 全链路调研 + HITL 背书的有意重构,非擅动——正是 line 28 要拦的反面。
- **三条全中**:① 难逆转(转换机制单一化一旦立,回退即重引入死活混杂)② 反直觉(钩子族零外部调用方却不删?因 ADR 保护,非无用)③ 真实取舍(全链路替换 vs 留 dead code / 契约测试 vs 影子运行 / 内建 service vs 留尾巴 / 补 Mapper 反向 vs 断入库)。

## Consequences

- **转换机制单一化**:Entity↔ORM 全走 Mapper,DB 边界转换真相源唯一,消除 32 子类重复 override。
- **入库 bug 顺修**:`add(entity)` 不触发转换的潜在 bug(`position_service:37,176`)随迁移修成 `add(mapper.entity_to_model(pos))`。
- **与 ADR-025 步骤 ⑤ 合流**:本 ADR 是步骤 ⑤(DB Mapper 收尾)的授权前置;步骤 ⑤ 执行 = 本 ADR §4 前提 + §5 顺序 1-8 落地。
- **对 Epic E #6701 的连带**:串成主线 `#6629(审计) → ADR-029(本文档,授权全链路替换) → #6298 + #6117 + #6469(收口迁移)`。
- **对 ADR-010 的标注**:ADR-010 顶部加「§4 钩子处理条款修订见 ADR-029」,其余不变。
- **退役期风险**:每批迁移须跑该 CRUD 测试门(全量测试 OOM,分批 + xdist `-n auto`,CLAUDE.md 铁律);热路径(Bar 大量读)Mapper `entity_to_model` 批量转避免逐条(呼应 ADR-010 §4 热路径)。
- **删除测试(ADR-025 同款验收)**:退役后转换集中到 Mapper,删任一 Mapper 即断该 CRUD 转换 = Mapper 在发挥作用,非 pass-through;退役前钩子族同理。
- **表结构边界(维护者约束)**:本 ADR 范围 = Entity↔ORM **转换层**收敛,**不动 ORM Model 表结构**。mapper 补的字段(`source`/`uuid`/`business_timestamp`/`market` 等)**均为 Model 已有列**(override 现状在写),非新增列。若迁移中发现需改 Model 字段(增删改列/改类型),**必须单独与维护者讨论确认**,不在迁移 PR 内擅改(呼应 CLAUDE.md「禁止手动 ALTER TABLE,表由 Model 定义 + `ginkgo init` 自动创建」)。
