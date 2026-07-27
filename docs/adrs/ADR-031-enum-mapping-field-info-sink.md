# ADR-031: enum 映射真值下沉 model 字段 info（字段→Enum 映射单源归位）

**Status:** Accepted
**Date:** 2026-07-28
**关联:** ADR-025（Mapper 独立于 CRUD；本文让 Mapper 经 model 反射即可得 enum 映射，无需 import CRUD）· ADR-022（抽象层收敛 / 单一接缝）· CLAUDE.md「禁改 Base」护栏 · `_conversion._get_enum_mappings`

## Context

CRUD 层散落 `_get_enum_mappings` override（全仓 grep 约 34 处），逐个手声明「字段名 → enum 类」映射：

```python
# signal_crud.py（改造前）
def _get_enum_mappings(self):
    return {'direction': DIRECTION_TYPES, 'source': SOURCE_TYPES}
# order_crud.py（改造前）
def _get_enum_mappings(self):
    return {'direction': DIRECTION_TYPES, 'order_type': ORDER_TYPES,
            'status': ORDERSTATUS_TYPES, 'source': SOURCE_TYPES}
```

**澄清「双源」**：enum *类*本身单源（`ginkgo.enums`）；真正散落的是**「哪个字段对应哪个 enum 类」这条映射知识**——它写在 CRUD 层，与 model 字段定义分离。model 侧字段是 `Mapped[int]`（`Int8`/`TINYINT`），无 enum 元数据可反射，映射无法从 model 推出，必须显式声明。于是 CRUD 成为这条知识的**唯一副本持有者**——model 改字段名、增删枚举字段时，CRUD override 易遗漏（典型 drift 温床）。

**与 Mapper 独立性冲突**：ADR-025 把 Mapper 定为「独立于 CRUD」。但 Mapper 收敛 DataFrame 时需要 enum 映射做 `_safe_enum_convert` 还原——若 Mapper import CRUD 取映射，就沾染进程内 DB 耦合，违背独立性。Mapper 既不能 import CRUD，又需要这条知识，说明**知识放错了层**。

**字段是映射知识的自然所有者**：字段知道自己的 enum 语义维度（`direction` 天然是 `DIRECTION_TYPES`）。CRUD override 是知识**错位**到 CRUD——字段定义才该持有它。

## Decision

### 原则 1 · 真值下沉：`mapped_column(..., info={'enum': XxxTypes})`

字段→Enum 映射声明在 model 字段定义处，用 SQLAlchemy 官方元数据字典 `Column.info`：

```python
# model_signal.py
direction: Mapped[int] = mapped_column(types.Int8, default=-1, info={"enum": DIRECTION_TYPES})
# model_clickbase.py（CH 公共基类，惠及整个 CH 家族）
source: Mapped[int] = mapped_column(types.Int8, default=-1, info={"enum": SOURCE_TYPES})
# model_mysqlbase.py（MySQL 公共基类，惠及整个 MySQL 家族）
source: Mapped[int] = mapped_column(TINYINT, default=-1, info={"enum": SOURCE_TYPES})
# model_order.py（MySQL）
direction: Mapped[int] = mapped_column(TINYINT, default=-1, info={"enum": DIRECTION_TYPES})
order_type: Mapped[int] = mapped_column(TINYINT, default=-1, info={"enum": ORDER_TYPES})
status: Mapped[int] = mapped_column(TINYINT, default=-1, info={"enum": ORDERSTATUS_TYPES})
```

`Column.info` 是 SA 官方「per-column arbitrary metadata dict」（非 hack）；`mapped_column(info={...})` 是标准、非侵入用法。真值归位字段定义——单源。

### 原则 2 · Base 钩子反射 + 渐进迁移（子类 override 向后兼容）

`_conversion._get_enum_mappings` 默认实现从 `return {}` 改为反射 `model_class.__table__.columns`，读每列 `col.info.get('enum')`：

```python
def _get_enum_mappings(self) -> Dict[str, Any]:
    model_cls = getattr(self, "model_class", None)
    if model_cls is None or not hasattr(model_cls, "__table__"):
        return {}
    mappings: Dict[str, Any] = {}
    for col in model_cls.__table__.columns:
        enum_cls = (col.info or {}).get("enum")
        if enum_cls is not None:
            mappings[col.name] = enum_cls
    return mappings
```

**渐进迁移**：子类 override 仍优先（Python MRO），故 34 个 override 可逐个迁移（加 `info=` → 删 override → 验证），共存可回退。全量迁移后 override 应清零，真值单源归位字段定义。迁移期 override 与 `info=` 须人工保证一致——否则 override 优先会**静默遮蔽** `info=`（迁移完即删 override 即消除）。

### 原则 3 · 三库覆盖范围

| 库 | 基类 | ORM | 反射路径 | c1 覆盖 |
|---|---|---|---|---|
| ClickHouse | `MClickBase(Base, MBase)` | SA `DeclarativeBase` | `__table__.columns[].info` | ✅ 通用 |
| MySQL | `MMysqlBase(Base, MBase)` | SA `DeclarativeBase` | 同上 | ✅ 通用 |
| Mongo | `MMongoBase(BaseModel, MBase)` | **Pydantic BaseModel** | `model.model_dump()`（`base_mongo_crud._convert_models_to_dataframe`） | ❌ 独立路径，不经 `_get_enum_mappings` |

CH 与 MySQL 同属 SA `DeclarativeBase`，反射逻辑两库**同一段代码通用**；Mongo 走 Pydantic 独立路径，不经此 hook，不受影响——其 enum 处理如需统一另议（非本 ADR 范围）。

## Rationale

- **删除测试**：删 CRUD override 后复杂度不消失（model 仍须在某处告知 enum）→ 真值应在 model；下沉让 CRUD override 变为**可删的错位副本**。c1 是最精简的治本——知识回到自然所有者，不引入新抽象层（区别于「注册表」方案：单源但与字段分离，仍是知识错位）。
- **Mapper 独立性**：Mapper 经 `model.__table__` 反射即可得映射，**不 import CRUD**——呼应 ADR-025「Mapper 独立于 CRUD」。
- **`source` 跨基类继承**：反射 `__table__.columns` 含继承列，故 `source` 声明在公共基类（`MClickBase`/`MMysqlBase`）一次，惠及整个家族——对称于字段继承本身。

### 破例改 Base（用户明确授权）

CLAUDE.md「禁止擅自修改 Base 类（BaseCRUD/BaseService 等）」是**防 agent 损坏 base 的护栏，非教条**。本次改 `_conversion._get_enum_mappings` 默认实现（`return {}` → 反射），经用户明确授权，理由：

- 改动是「**默认实现增强 + override 向后兼容**」——无 override 的 CRUD 继承新默认，有 override 的仍走 override（MRO），子类无感知、无破坏。
- 真值下沉后，Base 钩子是反射的唯一合理落点（反射须读 `model_class`，而 `model_class` 是 Base 层属性）；放具体 CRUD 反而重复。

## Consequences

**正面**
- 映射知识单源（model 字段定义）；CRUD 的 34 个 override 可逐个删除。
- Mapper 纯净：经 model 反射得映射，不 import CRUD。
- 增删枚举字段只改 model 一处（`info=`），CRUD 自动跟随，消除 drift 温床。

**迁移成本**
- 34 个 override 逐个迁移，本 ADR 仅试点 `signal`(CH) / `order`(MySQL)；其余分批。
- 迁移期 override 与 `info=` 共存，须人工保证一致（override 优先会静默遮蔽 `info=`）；全量迁移后删 override 即消歧。
- Mongo 不受益（独立路径）。

## 试点证据（2026-07-28）

- **signal(CH)**：`tests/unit/data/test_signal_enum_reflection_c1.py` 反射 5 passed；signal CRUD/service 无新回归。
- **MOrder(MySQL)**：`tests/unit/data/test_order_enum_reflection_c1.py` 反射 6 passed（含 `source` 跨 `MMysqlBase` 基类继承）；order CRUD/service/mapper 48 passed 无回归。
- 两库反射同一段 Base 代码，证 SA `info` 反射 CH+MySQL 通用。

## References
- ADR-025（DTO 信使全面复位 / Mapper 独立于 CRUD）
- ADR-022（抽象层收敛 / 单一接缝判定）
- `_conversion._get_enum_mappings`（Base 钩子，本 ADR 授权改动点）
- 试点：`model_clickbase.source` · `model_signal.direction` · `model_mysqlbase.source` · `model_order.direction/order_type/status` · 删 `signal_crud`/`order_crud` override
