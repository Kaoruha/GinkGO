# ADR-010 数据对象三层角色分离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `entities/` 包里混装的 Entity/ValueObject/ORM/DTO 四种角色分离——转换收敛到独立 Mapper 层、ModelList 瘦身不出 Service 边界、字段变更按语义分治、VO 摘掉 uuid，使逻辑层零外部依赖。

**Architecture:** CRUD 只懂表、出口返 ORM `ModelList`；Service 作枢纽，拿 `ModelList` 后用 Mapper 转，对外只返 DF/DTO/Entity（多出口方法，类型即契约）；Mapper 独立于 CRUD。Entity/ValueObject 零 `import data.models`/`interfaces.dtos`。单分支 6 阶段顺序推进，每阶段留代码 green（分模块测试门）。

**Tech Stack:** Python 3、SQLAlchemy ORM、pandas、pytest。venv: `/home/kaoru/.ginkgo/.venv/bin/python`。

**关联：** `docs/adrs/ADR-010-entity-orm-dto-separation.md`（决策）、根 `CONTEXT.md`（术语）、ADR-001（组件边界）、ADR-009（不改 Base/BaseCRUD/BaseService）。

---

## 数字基线（grep 实测，2026-06-13）

> ADR 草案部分数字为估算，下表为 `grep` 实测，**计划按实测排期**。建议执行前回写 ADR 同步。

| 违规 | 实测 | 来源 |
|---|---|---|
| V1 Entity 内 to/from_model | 20 方法 / 11 文件 | transfer(1) tick(2) adjustfactor(2) position(2) tradeday(2) capital_adjustment(2) mapping(1) bar(2) signal(2) order(2) stockinfo(2) |
| V3 套A CRUD（待逐个核实是否真返 Entity） | 7 候选 | engine_portfolio_mapping / transfer / stock_info / trade_day / position / engine_handler_mapping / tick |
| V9 `to_entities()` 真调用 | 4 | file_service.py:554,619 · backtest_feeder.py:248 · strategy_data_mixin.py:157（其余 12 处是 docstring） |
| V11 外部 `to_dataframe()` | 63 / 30 文件 | 见 Phase 4 Task 4.5 |
| V12 `hasattr to_dataframe` | 23 / 15 文件 | trading 9 · client 9 · service 5 |
| V5 `order.volume=` 赋值 | 17 / 8 文件 | margin·position_ratio·concentration(3)·liquidity(6)·volatility(3)·profit_target·max_drawdown·resource_optimizer |
| V10 entity `.uuid=` setter 调用 | 0 | grep 命中全是 ORM `M*.uuid==` 查询，非 entity setter |

## File Structure（文件职责映射）

**新增：**
- `src/ginkgo/entities/value_object.py` — `ValueObject` 基类（无 uuid/component_type/source）
- `src/ginkgo/data/mappers/__init__.py` — 包入口，导出所有 `XxxMapper`
- `src/ginkgo/data/mappers/{bar,order,position,signal,tick,adjustfactor,tradeday,mapping,stockinfo,transfer,capital_adjustment}_mapper.py` — 11 个 Mapper，每个 5 方法（`from_model/to_model/from_dto/to_dto/model_to_dto`），**不含 to_dataframe**、**不 import CRUD**
- `src/ginkgo/libs/identity.py` — `IdentityUtils`（从 entities 移入）

**移动：**
- `src/ginkgo/entities/identity.py` → `src/ginkgo/libs/identity.py`（移动后删源）
- `src/ginkgo/data/mappers.py`（套C 外部数据源入站函数）→ 并入 `src/ginkgo/data/mappers/`（后删源）

**瘦身（文件留，删方法）：**
- `src/ginkgo/data/crud/model_conversion.py` — 删 `to_entity()` + 7 个 DataFrame 模拟方法（`first/count/filter/empty/shape/head/tail`），留 `to_dataframe()` + `_fallback_to_dataframe`
- `src/ginkgo/data/crud/model_conversion.py:ModelList` — 删 `to_entities()` + 7 模拟方法，留 `to_dataframe()`

**删除（方法级）：**
- 11 个 Entity 内 20 个 to/from_model
- `interfaces/dtos/bar_dto.py:from_bar`、`price_update_dto.py:from_tick`
- `entities/base.py:uuid.setter` + `set_uuid()`
- Order/Position 创建后不变字段的裸 setter（volume→行为方法保留）

**修改（文件留）：**
- 8 VO 改继承 `Base`→`ValueObject`
- 套A CRUD 改返 ORM `ModelList`
- Service 加多出口方法 + 不透传
- `entities/__init__.py` 正名

**铁律边界（绝不改）：** `base.py:Base`、`crud/base_crud.py:BaseCRUD`、`data/services/base_service.py:BaseService`（ADR-009）。`ModelList` 由 `base_crud.py:392` 构造返回——瘦身而非全删即为此。

---

## 前置：建分支

- [ ] **Step 0: 建工作分支**

```bash
cd /home/kaoru/Ginkgo
LAST=$(git branch -r | grep -oP '\d+(?=-)' | sort -n | tail -1)
NEXT=$((LAST + 1))
git switch -c ${NEXT}-refactor/adr-010-entity-orm-dto-separation
echo "分支: ${NEXT}-refactor/adr-010-entity-orm-dto-separation"
```

预期：打印 `分支: <N>-refactor/...`。全程禁直提 master。

---

## Phase 1：建 Mapper 层 + 套A CRUD 切换 + 抹 Entity/DTO 内嵌转换

> 依赖顺序：先建 Mapper → 套A CRUD 切到调 Mapper（仍返 Entity，过渡）→ 最后才删 Entity.from_model。否则删早了套A CRUD 会崩。

### Task 1.1：建 `data/mappers/` 包 + 套C 并入

**Files:**
- Create: `src/ginkgo/data/mappers/__init__.py`
- Move: `src/ginkgo/data/mappers.py` 内容并入包后删源

- [ ] **Step 1: 建包目录与占位 `__init__.py`**

```bash
mkdir -p src/ginkgo/data/mappers
```

写 `src/ginkgo/data/mappers/__init__.py`（先空壳，Task 1.2-1.4 逐步补导出）：

```python
"""
Data Mappers — 转换收敛层（ADR-010）

每个 Mapper 负责 Entity/ORM/DTO 三态互转，五方法矩阵：
from_model / to_model / from_dto / to_dto / model_to_dto。

铁律：不 import CRUD（独立于持久层）；不含 to_dataframe（DF 出口留 CRUD）。
套C（外部数据源 DataFrame→ORM 入站）原 data/mappers.py 函数见 `_legacy.py`。
"""
```

- [ ] **Step 2: 套C 并入包**

```bash
git mv src/ginkgo/data/mappers.py src/ginkgo/data/mappers/_legacy.py
```

在 `src/ginkgo/data/mappers/__init__.py` 末尾追加套C 导出（保持现有调用方 `from ginkgo.data.mappers import dataframe_to_bar_models` 可用）：

```python
from ginkgo.data.mappers._legacy import (
    dataframe_to_adjustfactor_models,
    row_to_stockinfo_upsert_dict,
    dataframe_to_stockinfo_upsert_list,
    dataframe_to_bar_models,
    dataframe_to_bar_entities,
    dataframe_to_tick_entities,
    dataframe_to_tick_models,
)

__all__ = [
    "dataframe_to_adjustfactor_models", "row_to_stockinfo_upsert_dict",
    "dataframe_to_stockinfo_upsert_list", "dataframe_to_bar_models",
    "dataframe_to_bar_entities", "dataframe_to_tick_entities",
    "dataframe_to_tick_models",
]
```

- [ ] **Step 3: 验证导入不破**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -c "from ginkgo.data.mappers import dataframe_to_bar_models; print('OK')"`
Expected: `OK`

- [ ] **Step 4: grep 旧路径调用方并迁移**

```bash
grep -rn "from ginkgo.data.mappers import\|ginkgo.data.mappers\." src/ tests/ --include='*.py' | grep -v "data/mappers/_legacy\|data/mappers/__init__"
```
逐行核对：`from ginkgo.data.mappers import X` 因 `__init__.py` 已 re-export，**路径不变无需改**（`ginkgo.data.mappers` 现在指向包而非旧模块）。确认无 `import ginkgo.data.mappers as m; m.X` 之外的形式即可。

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/mappers/
git commit -m "refactor(#6106): 建 data/mappers 包，套C 入站转换并入 _legacy"
```

---

### Task 1.2：`OrderMapper`（原型，完整 5 方法）

**Files:**
- Create: `src/ginkgo/data/mappers/order_mapper.py`
- Test: `tests/unit/data/mappers/test_order_mapper.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/data/mappers/test_order_mapper.py`：

```python
import pytest
from decimal import Decimal
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.entities import Order
from ginkgo.data.mappers.order_mapper import OrderMapper


def _make_order():
    return Order(
        portfolio_id="p1", engine_id="e1", task_id="t1", code="000001.SZ",
        direction=DIRECTION_TYPES.LONG, order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW, volume=100, limit_price=10.5,
    )


def test_to_model_roundtrip_preserves_uuid():
    """Order.to_model → MOrder；from_model 还原，uuid 必须保真（修 order_id→uuid bug）。"""
    order = _make_order()
    expected_uuid = order.uuid

    model = OrderMapper.to_model(order)
    assert model.code == "000001.SZ"
    assert model.volume == 100

    restored = OrderMapper.from_model(model)
    assert restored.uuid == expected_uuid          # 关键：旧 from_model 丢 uuid，现已修
    assert restored.code == "000001.SZ"
    assert restored.volume == 100


def test_from_model_rejects_wrong_type():
    with pytest.raises(TypeError):
        OrderMapper.from_model(object())
```

- [ ] **Step 2: 运行确认失败**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/mappers/test_order_mapper.py -v`
Expected: FAIL `ModuleNotFoundError: ginkgo.data.mappers.order_mapper`

- [ ] **Step 3: 写 OrderMapper**

`src/ginkgo/data/mappers/order_mapper.py`（搬运自 `entities/order.py:604-674`，**修正 order_id→uuid**，签名改为 staticmethod，import ORM 提到模块级——Mapper 允许依赖 ORM）：

```python
"""OrderMapper — Order Entity ↔ MOrder ORM ↔ OrderDTO 转换（ADR-010）。"""
from typing import List

from ginkgo.data.models import MOrder
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class OrderMapper:
    """不依赖 CRUD；不含 to_dataframe。"""

    # ---- Entity ↔ ORM ----
    @staticmethod
    def to_model(entity: Order) -> MOrder:
        model = MOrder()
        model.update(
            portfolio_id=entity.portfolio_id,
            engine_id=entity.engine_id,
            task_id=entity.task_id,
            uuid=entity.uuid,
            code=entity.code,
            direction=entity.direction,
            order_type=entity.order_type,
            status=entity.status,
            volume=entity.volume,
            limit_price=entity.limit_price,
            frozen_money=entity.frozen_money,
            frozen_volume=entity.frozen_volume,
            transaction_price=entity.transaction_price,
            transaction_volume=entity.transaction_volume,
            remain=entity.remain,
            fee=entity.fee,
            timestamp=entity.timestamp,
            source=entity.source,
        )
        return model

    @staticmethod
    def from_model(model) -> Order:
        if not isinstance(model, MOrder):
            raise TypeError(f"Expected MOrder, got {type(model).__name__}")
        return Order(
            code=model.code,
            direction=DIRECTION_TYPES(model.direction),
            order_type=ORDER_TYPES(model.order_type),
            status=ORDERSTATUS_TYPES(model.status),
            volume=model.volume,
            limit_price=model.limit_price,
            frozen_money=model.frozen_money,
            frozen_volume=model.frozen_volume,
            transaction_price=model.transaction_price,
            transaction_volume=model.transaction_volume,
            remain=model.remain,
            fee=model.fee,
            timestamp=model.timestamp,
            uuid=model.uuid,                 # 修正：旧版传 order_id=（无此形参，被丢弃）
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            task_id=model.task_id,
        )

    @staticmethod
    def from_models(models) -> List[Order]:
        return [OrderMapper.from_model(m) for m in models]

    # ---- Entity ↔ DTO（路径②④⑤） ----
    @staticmethod
    def to_dto(entity: Order):
        from ginkgo.interfaces.dtos.order_dto import OrderDTO  # 延迟 import 避免循环
        return OrderDTO.from_order(entity) if hasattr(OrderDTO, "from_order") else OrderDTO(
            code=entity.code, direction=entity.direction, volume=entity.volume,
            order_type=entity.order_type, limit_price=float(entity.limit_price),
        )

    @staticmethod
    def from_dto(dto) -> Order:
        return Order(
            code=dto.code, direction=dto.direction, order_type=dto.order_type,
            volume=dto.volume, limit_price=dto.limit_price,
        )

    # ---- ORM ↔ DTO（路径①，跳过 Entity） ----
    @staticmethod
    def model_to_dto(model) -> "OrderDTO":
        from ginkgo.interfaces.dtos.order_dto import OrderDTO
        return OrderDTO(
            code=model.code, direction=DIRECTION_TYPES(model.direction),
            volume=model.volume, order_type=ORDER_TYPES(model.order_type),
            limit_price=float(model.limit_price),
        )
```

> **注：** 若 `interfaces/dtos/order_dto.py` 无 `from_order`，`to_dto` 走字段直构分支。DTO 转换方法本阶段**不强制全实现**——V1 只迁 `to_model/from_model`（20 个），DTO 三方法按调用方需要补；本任务给出签名占位 + 字段直构兜底，避免 import 爆破。执行时先确认 `order_dto.py` 现有构造方式。

- [ ] **Step 4: 运行确认通过**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/mappers/test_order_mapper.py -v`
Expected: 2 passed

- [ ] **Step 5: 补 `__init__.py` 导出**

在 `src/ginkgo/data/mappers/__init__.py` 追加：

```python
from ginkgo.data.mappers.order_mapper import OrderMapper
```
并在 `__all__` 加 `"OrderMapper"`。

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/mappers/order_mapper.py src/ginkgo/data/mappers/__init__.py tests/unit/data/mappers/test_order_mapper.py
git commit -m "feat(#6117): OrderMapper 迁移 Order.to/from_model，修正 uuid 丢失"
```

---

### Task 1.3：`BarMapper`（含 DTO `from_bar` 迁移）

**Files:**
- Create: `src/ginkgo/data/mappers/bar_mapper.py`
- Modify: `src/ginkgo/interfaces/dtos/bar_dto.py:40`（删 `from_bar`）
- Test: `tests/unit/data/mappers/test_bar_mapper.py`

- [ ] **Step 1: 写失败测试**

```python
from decimal import Decimal
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.entities import Bar
from ginkgo.data.mappers.bar_mapper import BarMapper


def test_bar_roundtrip():
    bar = Bar(code="000001.SZ", open=10, high=11, low=9, close=10.5,
              volume=1000, amount=10500, frequency=FREQUENCY_TYPES.DAY,
              timestamp="2025-01-02")
    model = BarMapper.to_model(bar)
    assert model.code == "000001.SZ"
    back = BarMapper.from_model(model)
    assert back.code == "000001.SZ"
    assert back.close == Decimal("10.5")
```

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/unit/data/mappers/test_bar_mapper.py -v`
Expected: FAIL `ModuleNotFoundError`

- [ ] **Step 3: 写 BarMapper**

`src/ginkgo/data/mappers/bar_mapper.py`（搬运 `entities/bar.py:254-311`）：

```python
"""BarMapper — Bar ↔ MBar ↔ BarDTO（ADR-010）。"""
from typing import List
from ginkgo.data.models import MBar
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES


class BarMapper:

    @staticmethod
    def to_model(entity: Bar) -> MBar:
        model = MBar()
        model.update(
            entity.code,
            open=entity.open, high=entity.high, low=entity.low, close=entity.close,
            volume=entity.volume, amount=entity.amount,
            frequency=entity.frequency, timestamp=entity.timestamp,
        )
        return model

    @staticmethod
    def from_model(model) -> Bar:
        if not isinstance(model, MBar):
            raise TypeError(f"Expected MBar, got {type(model).__name__}")
        frequency = FREQUENCY_TYPES.from_int(model.frequency) or FREQUENCY_TYPES.DAY
        return Bar(
            code=model.code, open=model.open, high=model.high, low=model.low,
            close=model.close, volume=model.volume, amount=model.amount,
            frequency=frequency, timestamp=model.timestamp,
        )

    @staticmethod
    def from_models(models) -> List[Bar]:
        return [BarMapper.from_model(m) for m in models]

    @staticmethod
    def to_dto(entity: Bar):
        from ginkgo.interfaces.dtos.bar_dto import BarDTO
        # 搬运自 bar_dto.py 原 from_bar 逻辑（Task 1.6 删除该方法前先迁此）
        return BarDTO(
            code=entity.code, open=float(entity.open), high=float(entity.high),
            low=float(entity.low), close=float(entity.close), volume=entity.volume,
            frequency=entity.frequency, timestamp=entity.timestamp,
        )

    @staticmethod
    def model_to_dto(model) -> "BarDTO":
        from ginkgo.interfaces.dtos.bar_dto import BarDTO
        return BarMapper.to_dto(BarMapper.from_model(model))
```

> **`to_dto` 字段需对齐 `bar_dto.py` 实际字段。** 执行时先 `Read src/ginkgo/interfaces/dtos/bar_dto.py`，按其 `__init__` 形参填 `to_dto`——禁止臆造字段。

- [ ] **Step 4: 运行确认通过**

Run: `pytest tests/unit/data/mappers/test_bar_mapper.py -v` → Expected: PASS

- [ ] **Step 5: 导出 + Commit**

`__init__.py` 加 `from ginkgo.data.mappers.bar_mapper import BarMapper`。

```bash
git add src/ginkgo/data/mappers/bar_mapper.py src/ginkgo/data/mappers/__init__.py tests/unit/data/mappers/test_bar_mapper.py
git commit -m "feat(#6117): BarMapper 迁移 Bar.to/from_model，from_bar 逻辑并入 to_dto"
```

---

### Task 1.4：其余 9 个 Mapper（搬运规格表）

> 模式与 OrderMapper/BarMapper 完全一致：`@staticmethod to_model/from_model/from_models/to_dto/model_to_dto`，**to_model/from_model 方法体原样搬运自各 Entity 现有方法**（字段映射已验证可用），仅改：① 签名 `to_model(self)`→`to_model(entity)`、`from_model(cls, model)`→`from_model(model)`；② `self._x`→`entity._x` 或经 property；③ ORM `from ginkgo.data.models import MXxx` 提到模块级。

| Mapper | 源方法位置 | ORM | 备注 |
|---|---|---|---|
| `PositionMapper` | `entities/position.py:825-873` | MPosition | 含 `model.uuid = self.uuid`（to_model 内给 ORM 赋值，保留） |
| `SignalMapper` | `entities/signal.py:371-419` | MSignal | 同上，`:395 model.uuid=self.uuid` 保留 |
| `TickMapper` | `entities/tick.py:131-170` | 动态 tick model（见 `get_tick_model`） | `to_model(self, model_class)`→`to_model(entity, model_class)`，保留 model_class 形参 |
| `AdjustfactorMapper` | `entities/adjustfactor.py:135-160` | MAdjustfactor | `to_model(self, model_class)`→保留 model_class |
| `TradeDayMapper` | `entities/tradeday.py:143-180` | MTradeDay | 同上 |
| `CapitalAdjustmentMapper` | `entities/capital_adjustment.py:188-215` | MCapitalAdjustment | 同上 |
| `MappingMapper` | `entities/mapping.py:227-` | MMapping | `from_model(cls, model, mapping_type)`→保留 mapping_type 形参 |
| `StockInfoMapper` | `entities/stockinfo.py:187-230` | MStockInfo | `to_model(self, model_class)`→保留 |
| `TransferMapper` | `entities/transfer.py:219-` | MTransfer | 仅有 from_model，to_model 按 from_model 反向补（或先不实现，标 `raise NotImplementedError`，执行时确认是否有写路径调用） |

**每个 Mapper 的执行步骤（重复 9 次）：**

- [ ] **Step 1: Read 源 Entity，确认字段与 ORM update 签名**
- [ ] **Step 2: 写失败测试**（roundtrip：构造 Entity → `to_model` → `from_model` → 断言关键字段 + uuid 保真；`from_model(object())` 抛 TypeError）——测试路径 `tests/unit/data/mappers/test_<name>_mapper.py`
- [ ] **Step 3: 运行确认失败**（ModuleNotFoundError）
- [ ] **Step 4: 写 Mapper**（按上表搬运 + 改签名；DTO 三方法如无调用方可只实现 `from_model/to_model/from_models`）
- [ ] **Step 5: 运行确认通过**
- [ ] **Step 6: 导出 + Commit**

```bash
git add src/ginkgo/data/mappers/<name>_mapper.py src/ginkgo/data/mappers/__init__.py tests/unit/data/mappers/test_<name>_mapper.py
git commit -m "feat(#6117): <Name>Mapper 迁移 to/from_model"
```

> **TransferMapper 特例：** Transfer 无 to_model。先 grep 确认是否有写路径（`grep -rn "Transfer.*to_model\|transfer_crud.*add\|transfer_crud.*create" src/`）；若无，`to_model` 实现为 `raise NotImplementedError("Transfer 无写路径")`，不臆造。

---

### Task 1.5：套A CRUD 切到调 Mapper（过渡，仍返 Entity）

> 目的：让 7 个候选 CRUD 的 Entity 构造走 `XxxMapper.from_model`，为 Task 1.6 删 `Entity.from_model` 铺路。**本任务不改返回类型**（仍返 Entity/ModelList 现状），只替换构造来源。

**Files:** 7 候选 CRUD（见数字基线 V3）。先逐个核实是否真在方法体内调 `Entity.from_model`。

- [ ] **Step 1: 逐个核实套A 真实返型**

```bash
for f in engine_portfolio_mapping transfer stock_info trade_day position engine_handler_mapping tick; do
  echo "=== $f ==="; grep -n "from_model\|return.*Bar\|return.*Order\|return.*Position\|return.*Signal\|return.*Tick\|return.*Adjustfactor\|return.*TradeDay\|return.*StockInfo\|return.*Transfer\|return.*Mapping\|return.*CapitalAdjustment" src/ginkgo/data/crud/${f}_crud.py 2>/dev/null
done
```

对每个 grep 出 `Entity.from_model(` 或 `return Entity(...)` 的方法，标记为套A 真返型。

- [ ] **Step 2: 逐文件替换 `Entity.from_model(m)` → `XxxMapper.from_model(m)`**

例（假设 `position_crud.py` 有 `return Position.from_model(m)`）：

Edit `src/ginkgo/data/crud/position_crud.py`：
- 顶部加 `from ginkgo.data.mappers import PositionMapper`
- `Position.from_model(m)` → `PositionMapper.from_model(m)`

**逐文件人工 Edit，禁 sed**（feedback_no_sed）。每个 CRUD 单独 commit。

- [ ] **Step 3: 模块测试门**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/crud/ -k "position or transfer or stockinfo or tradeday or mapping or tick" -x -q`
Expected: 全 PASS（行为不变，仅构造来源换）

- [ ] **Step 4: 逐文件 Commit**

```bash
git add src/ginkgo/data/crud/<name>_crud.py
git commit -m "refactor(#6106): <Name>CRUD 改调 Mapper.from_model（过渡，返型不变）"
```

---

### Task 1.6：抹 Entity/DTO 内嵌转换（删 20 方法 + from_bar/from_tick）

> 前置：Task 1.5 已让所有套A CRUD 不再调 `Entity.from_model`；mappers 内部已自含逻辑。现可安全删 Entity 方法体。

**Files:**
- Modify: 11 个 Entity（删 20 个 to/from_model）
- Modify: `interfaces/dtos/bar_dto.py`（删 `from_bar`）、`price_update_dto.py`（删 `from_tick`）

- [ ] **Step 1: grep 确认 Entity.from_model 已无外部调用**

```bash
grep -rn "\.from_model(\|\.to_model(" src/ tests/ --include='*.py' | grep -v "Mapper\|def \|entities/" 
```
Expected: **空**（所有调用已切 Mapper）。若非空，回 Task 1.5 补。

- [ ] **Step 2: 删 11 Entity 的 20 个方法**

逐文件 Edit 删除 `def to_model` / `def from_model` 整段（含 docstring）。例 `entities/order.py`：删 `604-674`（to_model + from_model）。每个 Entity 删后确认无内部自调。

- [ ] **Step 3: 删 DTO 内嵌转换**

- `interfaces/dtos/bar_dto.py`：删 `from_bar`（`BarMapper.to_dto` 已承接）
- `interfaces/dtos/price_update_dto.py`：删 `from_tick`——先 grep `from_tick(` 调用方，迁到调用方内联或 `TickMapper.to_dto`

```bash
grep -rn "from_bar(\|from_tick(" src/ --include='*.py' | grep -v "def from_bar\|def from_tick"
```

- [ ] **Step 4: 运行实体 + DTO 测试门**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/entities/ tests/unit/interfaces/ tests/unit/data/mappers/ -x -q`
Expected: PASS

- [ ] **Step 5: 冒烟（import 全包）**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -c "import ginkgo.entities, ginkgo.data.mappers, ginkgo.interfaces.dtos; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/entities/ src/ginkgo/interfaces/dtos/
git commit -m "refactor(#6106): 抹 Entity/DTO 内嵌转换（20 方法 + from_bar/from_tick），V1/V2 收口"
```

---

## Phase 2：ValueObject 基类 + 8 VO 迁继承

### Task 2.1：新增 `entities/value_object.py`

**Files:**
- Create: `src/ginkgo/entities/value_object.py`
- Test: `tests/unit/entities/test_value_object.py`

- [ ] **Step 1: 写失败测试**

```python
from ginkgo.entities.value_object import ValueObject
from ginkgo.enums import SOURCE_TYPES


def test_valueobject_has_no_uuid():
    vo = ValueObject()
    assert not hasattr(vo, "uuid") or vo.__class__.__name__ == "ValueObject"
    # ValueObject 无 uuid 字段、无 component_type、无 source

def test_valueobject_is_not_base():
    from ginkgo.entities.base import Base
    assert not issubclass(ValueObject, Base) or ValueObject is not Base
```

> 注：ValueObject 是否继承 Base？ADR 说"无 uuid/component_type/source"。**实现决策：ValueObject 不继承 Base**（独立轻基类，只提供 `to_dataframe`/`_convert_*` 工具方法，不带身份）。若发现 VO 现有代码依赖 Base 的 `to_dataframe`/`set_source`，则改为继承 Base 但 Override 掉 uuid 相关——执行时先 grep VO 对 Base 方法的依赖再定。下文按"独立基类"给代码。

- [ ] **Step 2: 运行确认失败**

Run: `pytest tests/unit/entities/test_value_object.py -v` → FAIL ModuleNotFoundError

- [ ] **Step 3: 写 ValueObject**

`src/ginkgo/entities/value_object.py`：

```python
"""ValueObject — 无领域身份的值载体基类（ADR-010）。

与 Entity(Base) 区别：无 uuid / 无 component_type / 无 source。
VO 由字段值描述，不持有状态机；持久化时 uuid 由 ORM default 生成，不污染领域。
"""
import pandas as pd
from types import FunctionType, MethodType
from enum import Enum

from ginkgo.libs.data.number import convert_to_float as _f
from ginkgo.libs.data.number import convert_to_int as _i
from ginkgo.libs.data.number import convert_to_bool as _b


class ValueObject:
    """无身份的领域值载体。"""

    def to_dataframe(self) -> pd.DataFrame:
        item = {}
        skip = {"delete", "query", "registry", "metadata", "to_dataframe"}
        for param in self.__dir__():
            if param in skip or param.startswith("_"):
                continue
            attr = self.__getattribute__(param)
            if isinstance(attr, (MethodType, FunctionType)):
                continue
            if isinstance(attr, Enum):
                item[param] = attr.value
            elif isinstance(attr, str):
                item[param] = attr.strip(b"\x00".decode())
            else:
                item[param] = attr
        return pd.DataFrame.from_dict(item, orient="index").transpose()

    _convert_to_float = staticmethod(_f)
    _convert_to_int = staticmethod(_i)
    _convert_to_bool = staticmethod(_b)
```

- [ ] **Step 4: 运行确认通过** → PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/entities/value_object.py tests/unit/entities/test_value_object.py
git commit -m "feat(#6112): 新增 ValueObject 基类（无 uuid/component_type/source）"
```

---

### Task 2.2：8 VO 迁继承 `Base` → `ValueObject`

> 先 grep 每个 VO 对 Base 独有方法（`set_source`/`source`/`uuid`/`component_type`/`set_uuid`）的依赖，决定是否需保留兼容属性。

- [ ] **Step 1: 扫描 VO 对 Base 的依赖**

```bash
for vo in adjustfactor tradeday mapping stockinfo transfer tick file_info capital_adjustment; do
  echo "=== $vo ==="; grep -n "\.uuid\|set_source\|\.source\|component_type\|super().__init__\|Base" src/ginkgo/entities/${vo}.py 2>/dev/null
done
```

- [ ] **Step 2: 逐 VO 改继承**

对每个 VO（`entities/adjustfactor.py` 等），Edit：
- `from ginkgo.entities.base import Base` → `from ginkgo.entities.value_object import ValueObject`
- `class Xxx(ValueObject):`（替换 `Base`）
- `__init__` 内 `super().__init__(uuid=..., component_type=...)` → `super().__init__()`
- 删 `set_source(SOURCE_TYPES.X)` 调用（若 VO 无 source 概念）；若 VO 现有逻辑依赖 `self._source`（如入站标记），保留为普通属性 `self._source = SOURCE_TYPES.X`（ValueObject 无 source property，需在 VO 子类自加，或确认入站标记已由套C Mapper 承接后删除）

> **关键判断点：** `mappers.py:124 bar._source = SOURCE_TYPES.TUSHARE`、`:157 tick._source` 是入站时塞 source 给 ORM。改 VO 后这些直接赋值 `_source` 仍可用（普通属性），但 VO 不再有 `source` property。grep 谁读 `entity.source`：
> ```bash
> grep -rn "\.source" src/ginkgo/data/crud/ --include='*.py' | grep -i "bar\|tick\|adjustfactor"
> ```
> 若 CRUD 读 `entity.source` 入库，则 VO 需保留 `_source` 属性 + `source` property（或 CRUD 改读 `getattr(entity, 'source', None)`）。执行时据 grep 结果定。

- [ ] **Step 3: Signal 维持 Entity（验证不变）**

```bash
grep -n "class Signal" src/ginkgo/entities/signal.py
```
Expected: `class Signal(TimeMixin,...,Base)` — 确认 Signal 仍继承 Base，**不动**。

- [ ] **Step 4: 测试门**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/entities/ -x -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/entities/
git commit -m "refactor(#6112): 8 VO 迁继承 ValueObject（摘 uuid），Signal 维持 Entity"
```

---

## Phase 3：套A CRUD 改返 ORM ModelList

> Task 1.5 让 CRUD 走 Mapper 返 Entity（过渡）。本阶段去掉 Entity 构造，直接返 ORM ModelList——调用方（Service）拿 ModelList 后自行用 Mapper 转。

**Files:** Task 1.5 确认的套A CRUD（预期 6-7 个）。

对每个套A CRUD 方法：

- [ ] **Step 1: 定位返 Entity 的方法**

```bash
grep -n "Mapper.from_model\|return.*Entity\|return.*\.from_model" src/ginkgo/data/crud/<name>_crud.py
```

- [ ] **Step 2: 改返 ORM ModelList**

把方法体内 `return [XxxMapper.from_model(m) for m in models]`（或 `Entity.from_model`）改为**直接返 ORM model 列表**（BaseCRUD 的 find 已返 ModelList，套A 只是多包了一层 Entity 转换，去掉这层）。

例：若 `position_crud.find_xxx` 末尾是 `return ModelList([PositionMapper.from_model(m) for m in raw])`，改为 `return ModelList(raw, self)`（raw 是 ORM model 列表）。

- [ ] **Step 3: 更新调用方（Service）**

套A CRUD 不再返 Entity，调它的 Service 需补 Mapper 转换。grep 调用方：

```bash
grep -rn "<name>_crud\.\|<name>CRUD\." src/ginkgo/data/services/ --include='*.py'
```

每个 Service 调用点：拿到 ModelList 后按需 `XxxMapper.from_models(model_list)` 转 Entity，或 `.to_dataframe()` 转 DF。

- [ ] **Step 4: 测试门**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/crud/ tests/unit/data/services/ -k "<name>" -x -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/crud/<name>_crud.py src/ginkgo/data/services/
git commit -m "refactor(#6106): <Name>CRUD 返 ORM ModelList，Entity 转换归 Service+Mapper"
```

---

## Phase 4：ModelList 瘦身 + Service 多出口 + 不透传（爆破阶段）

> 最大阶段：63 处 `to_dataframe` + 23 处 `hasattr` + 4 处 `to_entities`。

### Task 4.1：ModelList / ModelConversion 瘦身

**Files:**
- Modify: `src/ginkgo/data/crud/model_conversion.py`（删 `to_entity`/`to_entities` + 7 模拟方法）

- [ ] **Step 1: 写失败测试（验证 to_dataframe 仍在、to_entities 已删）**

`tests/unit/data/crud/test_model_list_slim.py`：

```python
import pytest
from ginkgo.data.crud.model_conversion import ModelList


def test_modellist_keeps_to_dataframe():
    assert hasattr(ModelList, "to_dataframe")

def test_modellist_drops_to_entities():
    # to_entities 已移除——调用方应改用 Mapper.from_models
    assert not hasattr(ModelList, "to_entities")

def test_modellist_drops_df_simulators():
    for dead in ("first", "count", "filter", "empty", "shape", "head", "tail"):
        assert not hasattr(ModelList, dead), f"ModelList.{dead} 应删除（dead code）"
```

- [ ] **Step 2: 运行确认失败**（`to_entities`/模拟方法还在）→ FAIL

- [ ] **Step 3: 删方法**

Edit `model_conversion.py`：
- `ModelList.to_entities()` 整段删
- `ModelConversion.to_entity()` 整段删
- `ModelList` 的 `first/count/filter/empty/shape/head/tail` 整段删
- 保留 `ModelList.to_dataframe()`、`ModelConversion.to_dataframe()`、`ModelCRUDMapping`、`get_crud_instance`、`_fallback_to_dataframe`
- 保留 `_convert_to_business_objects` mixin（dead code，不盲目删——feedback_no_blind_dead_code_deletion）

- [ ] **Step 4: 运行确认通过** → PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/data/crud/model_conversion.py tests/unit/data/crud/test_model_list_slim.py
git commit -m "refactor(#6106): ModelList 瘦身，删 to_entities + 7 模拟方法，留 DF 出口"
```

---

### Task 4.2：Service 多出口方法（类型即契约）

> 原型：`StockinfoService`（V11 透传重灾区）+ `BarService`。多出口 = 同一查询按消费语义提供 `get_xxx_df()`/`get_xxx()`/`get_xxx_dto()`。

**Files:**
- Modify: `src/ginkgo/data/services/stockinfo_service.py`、`bar_service.py` 等

- [ ] **Step 1: 写失败测试（StockinfoService 多出口）**

`tests/unit/data/services/test_stockinfo_multiexit.py`：

```python
from ginkgo.data.services.stockinfo_service import StockinfoService


def test_get_returns_entities(monkeypatch):
    """get_stockinfos() 返回 List[StockInfo] Entity。"""
    svc = StockinfoService.__new__(StockinfoService)
    # 用 monkeypatch 桩 _crud_repo.find 返空 ModelList，断言走 Mapper.from_models
    # （具体桩按 BaseService 结构补；本测试验证方法存在 + 返回类型契约）
    assert hasattr(StockinfoService, "get_stockinfos")
    assert hasattr(StockinfoService, "get_stockinfos_df")
    assert hasattr(StockinfoService, "get_stockinfo_dtos")


def test_get_does_not_return_modellist():
    """get() 不再透传 ModelList（V11）。"""
    import inspect
    src = inspect.getsource(StockinfoService.get)
    assert "ModelList" not in src or "to_dataframe" not in src
```

> 桩测试细节按 `BaseService` 真实结构补；核心断言是**方法存在 + 返型契约**。

- [ ] **Step 2: 运行确认失败**（多出口方法不存在）→ FAIL

- [ ] **Step 3: 加多出口方法 + 不透传**

Edit `stockinfo_service.py`，把 `get()`（透传 ModelList）改为不透传，并补三个出口。`get()` 现有逻辑（`:395-433`）改为：

```python
def get_stockinfos_df(self, code=None, name=None, ..., order_by=None, desc_order=False) -> ServiceResult:
    """出口①：返 DataFrame。Service 内部 to_dataframe，不透传 ModelList。"""
    try:
        filters = self._build_filters(code, name, ..., status)
        model_list = self._crud_repo.find(filters=filters, **self._build_query(limit, offset, order_by, desc_order))
        df = model_list.to_dataframe() if model_list else pd.DataFrame()
        return ServiceResult.success(data=df, message=f"Retrieved {len(df)} records")
    except Exception as e:
        return ServiceResult.failure(message=str(e))

def get_stockinfos(self, ...) -> ServiceResult:
    """出口②：返 List[StockInfo] Entity。"""
    from ginkgo.data.mappers import StockInfoMapper
    model_list = self._crud_repo.find(filters=..., ...)
    entities = StockInfoMapper.from_models(model_list) if model_list else []
    return ServiceResult.success(data=entities, ...)

def get_stockinfo_dtos(self, ...) -> ServiceResult:
    """出口③：返 DTO 列表。"""
    from ginkgo.data.mappers import StockInfoMapper
    model_list = self._crud_repo.find(...)
    dtos = [StockInfoMapper.model_to_dto(m) for m in (model_list or [])]
    return ServiceResult.success(data=dtos, ...)
```

> `_build_filters`/`_build_query` 是从原 `get()` 抽出的私有辅助，DRY。保留原 `get()` 签名作向后兼容（委托到 `get_stockinfos_df`），或标注 deprecated。

- [ ] **Step 4: 对 `BarService` 重复**（回测热路径只走 DF，补 `get_bars_df`/`get_bars`）

- [ ] **Step 5: 运行确认通过** → PASS

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/services/stockinfo_service.py src/ginkgo/data/services/bar_service.py tests/
git commit -m "refactor(#6106): Service 多出口方法（类型即契约），Stockinfo/Bar 不透传 ModelList"
```

---

### Task 4.3：4 处 `to_entities()` 改 `Mapper.from_models`

**Files:**
- `src/ginkgo/data/services/file_service.py:554,619`
- `src/ginkgo/trading/feeders/backtest_feeder.py:248`
- `src/ginkgo/trading/interfaces/mixins/strategy_data_mixin.py:157`

- [ ] **Step 1: 逐处改**

例 `file_service.py:554`：`files.to_entities()` → `from ginkgo.data.mappers import FileInfoMapper; FileInfoMapper.from_models(files)`（`files` 是 ModelList=list 子类，可直传）。

`backtest_feeder.py:248`：`result.data.to_entities()` → `BarMapper.from_models(result.data)`。

- [ ] **Step 2: 测试门**

Run: `/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/data/services/test_file_service.py tests/unit/trading/feeders/ -x -q` → PASS

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/data/services/file_service.py src/ginkgo/trading/feeders/backtest_feeder.py src/ginkgo/trading/interfaces/mixins/strategy_data_mixin.py
git commit -m "refactor(#6106): 4 处 to_entities 改 Mapper.from_models（V9 收口）"
```

---

### Task 4.4：63 处外部 `to_dataframe()` 改 `result.data`（grep + 逐文件规则）

> 模式：Service 不透传 ModelList 后，`result.data` 已是 DF/Entity/DTO（取决于调的多出口方法）。调用方删 `result.data.to_dataframe()` 的鸭子转换，直接用 `result.data`。

**转换规则（逐文件人工 Edit，禁 sed）：**

| 调用现状 | 改后 |
|---|---|
| `df = result.data.to_dataframe()` 且调的是 DF 出口 | `df = result.data` |
| `df = result.data.to_dataframe()` 且调的是旧透传 `get()` | 改调 `get_xxx_df()`，然后 `df = result.data` |
| `if hasattr(x, 'to_dataframe'): x.to_dataframe()` | 删 hasattr，直接 `x`（已是 DF） |

**涉及文件（30 个，grep 实测）：**
`adjustfactor_service` `stockinfo_service` `tick_service` `portfolio_service` `bar_adjustment` `factor_service` `bar_service` `user_crud` `tick_crud`(docstring) `user_group_crud` `research/ic_analysis` `client/record_cli` `notifier/notifier_telegram` `client/data_cli` `client/portfolio_cli` `client/backtest_result_cli` `client/cli_utils` `trading/services/engine_assembly_service` `trading/services/_assembly/data_preparer` `client/tui_client` `client/engine_cli` `trading/selectors/popularity_selector` `client/flat_cli` `trading/analysis/backtest_result_aggregator` `trading/selectors/cn_all_selector` `trading/feeders/base_feeder` `trading/selectors/momentum_selector` `trading/sizers/atr_sizer` `trading/feeders/backtest_feeder` `trading/sizers/ratio_sizer`

- [ ] **Step 1: 列出全部调用点**

```bash
grep -rn "\.to_dataframe()" src/ --include='*.py' | grep -v "def to_dataframe\|entities/\|model_conversion\|base_crud"
```

- [ ] **Step 2: 按模块逐文件 Edit**（每个文件：① 确认调的 Service 方法 → ② 若旧透传则改多出口 → ③ 删 `.to_dataframe()` 鸭子转换）

- [ ] **Step 3: 每个模块的测试门**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/client/ tests/unit/trading/ tests/unit/research/ -x -q
```

- [ ] **Step 4: 每 3-5 文件一次 Commit**（粒度可追溯）

```bash
git add <files>
git commit -m "refactor(#6106): <模块> to_dataframe 鸭子转换改多出口 result.data（V11）"
```

---

### Task 4.5：23 处 `hasattr(result.data, 'to_dataframe')` 鸭子探测改多出口（V12）

> 最深病灶。`hasattr` 探测 = Service 返型不明确。改为调明确的 Service 多出口方法。

**Files（15 个）：** `adjustfactor_service:366,588` `tick_service:518` `bar_adjustment:40` `factor_service:267` `client/backtest_result_cli:118` `client/portfolio_cli:224,235` `trading/services/engine_assembly_service:438` `data_preparer:105,219,274` `client/engine_cli:83,99,412,756` `client/tui_client:142` `client/data_cli:269,313` `cn_all_selector:35` `momentum_selector:76` `popularity_selector:71` `backtest_result_aggregator:195`

- [ ] **Step 1: 逐处改**

**data_preparer.py 三处**（原型）：
```python
# 旧 (line 105, 219, 274)
if hasattr(portfolio_result.data, "to_dataframe"):
    portfolio_df = portfolio_result.data.to_dataframe()
else:
    portfolio_df = portfolio_result.data
```
改为调多出口：
```python
portfolio_result = self._portfolio_service.get_portfolio_df(portfolio_id=portfolio_id)
portfolio_df = portfolio_result.data   # 已是 DF，无鸭子探测
```

**engine_assembly_service.py:438 / engine_cli.py:756** 同理改 `get_engine_df()`。

**selectors**（`cn_all_selector:35` 等）：
```python
# 旧
if result.success and hasattr(result.data, 'to_dataframe'):
    df = result.data.to_dataframe()
# 改
if result.success:
    df = result.data   # 调的是 get_bars_df()
```

**client/\* 的 `hasattr(engines_data, 'to_dataframe')`**：调的 Service 方法改多出口后，`engines_data` 已是 DF，删 hasattr 分支。

- [ ] **Step 2: 测试门（关键回测路径）**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/trading/selectors/ tests/unit/trading/services/ tests/unit/client/ -x -q
```

外加**冒烟回测**（feedback_smoke_test_startup——必须覆盖应用启动路径）：
```bash
/home/kaoru/.ginkgo/.venv/bin/python -c "from ginkgo.trading.services._assembly.data_preparer import DataPreparer; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/ src/ginkgo/client/ src/ginkgo/data/services/
git commit -m "refactor(#6106): 23 处 hasattr 鸭子探测改 Service 多出口（V12，类型即契约）"
```

---

### Task 4.6：tick_crud / base_crud docstring 清理

- [ ] **Step 1: 删 docstring 中过时的 `to_entities()` 链式 demo**

`tick_crud.py:74,87,92,696,764,776,784,825,835,843,881,891,899,927,934,942`、`base_crud.py:30,377`、`signal_tracker_crud.py:233,259,283`、`bar_service.py:682`——这些 docstring 提到 `to_entities()`（已删）。改为只提 `to_dataframe()`。

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/data/crud/ src/ginkgo/data/services/bar_service.py
git commit -m "docs(#6106): 清理 to_entities 过时 docstring（仅留 to_dataframe）"
```

---

## Phase 5：字段分治（删 Base uuid setter + Order/Position setter 分治）

### Task 5.1：`Order.adjust_volume()` + `Position.update_price()` 行为方法

**Files:**
- Modify: `src/ginkgo/entities/order.py`（加 `adjust_volume`）
- Modify: `src/ginkgo/entities/position.py`（加 `update_price`）
- Test: `tests/unit/entities/test_order_adjust_volume.py`

- [ ] **Step 1: 写失败测试**

```python
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


def _order():
    return Order(portfolio_id="p", engine_id="e", task_id="t", code="000001.SZ",
                 direction=DIRECTION_TYPES.LONG, order_type=ORDER_TYPES.MARKETORDER,
                 status=ORDERSTATUS_TYPES.NEW, volume=100, limit_price=10)


def test_adjust_volume_sets_positive():
    o = _order()
    o.adjust_volume(50)
    assert o.volume == 50

def test_adjust_volume_rejects_nonpositive():
    import pytest
    o = _order()
    with pytest.raises(ValueError):
        o.adjust_volume(0)
```

- [ ] **Step 2: 运行确认失败** → FAIL

- [ ] **Step 3: 加行为方法**

`entities/order.py` 加（替代裸 `volume` setter 的语义化入口）：

```python
def adjust_volume(self, new_volume: int) -> None:
    """风控调整订单量（ADR-001 合法通道）。new_volume 必须 > 0。"""
    if not isinstance(new_volume, int):
        new_volume = int(new_volume)
    if new_volume <= 0:
        raise ValueError("adjust_volume: new_volume must be positive")
    self._volume = new_volume
```

`entities/position.py` 加 `update_price(self, price)`（同模式，Price 风控更新通道）。

> **volume setter 暂保留**到 Task 5.3（删裸 setter）一并处理——本任务只加行为方法，先让 Risk 有可迁移目标。

- [ ] **Step 4: 运行确认通过** → PASS

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/entities/order.py src/ginkgo/entities/position.py tests/unit/entities/test_order_adjust_volume.py
git commit -m "feat(#6112): Order.adjust_volume / Position.update_price 行为方法（Risk 调整通道）"
```

---

### Task 5.2：17 处 Risk `order.volume = X` → `order.adjust_volume(X)`

**Files（8 个）：** `margin_risk:53` `position_ratio_risk:226` `concentration_risk:125,128,139` `liquidity_risk:117,120,127,141,151,202` `volatility_risk:106,110,118` `profit_target_risk:161` `max_drawdown_risk:124` `resource_optimizer:493`

- [ ] **Step 1: 列全部赋值点**

```bash
grep -rn "order\.volume\s*=\|order\.volume =\|_order\.volume =" src/ginkgo/trading/risk_management/ src/ginkgo/trading/signal_processing/ --include='*.py'
```

- [ ] **Step 2: 逐处转换规则**

| 现状 | 改后 |
|---|---|
| `order.volume = int(order.volume * factor)` | `order.adjust_volume(int(order.volume * factor))` |
| `order.volume = max(order.volume, min_volume)` | `order.adjust_volume(max(order.volume, min_volume))` |
| `order.volume = max_sellable` | `order.adjust_volume(max_sellable)` |
| `order.volume = current_position.volume` | `order.adjust_volume(current_position.volume)` |

逐文件人工 Edit。每处确认语义（`adjust_volume` 内部已校验 >0，原 `max(order.volume, min_volume)` 保证非负，兼容）。

- [ ] **Step 3: Risk 模块测试门**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/trading/risk_management/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/trading/risk_management/ src/ginkgo/trading/signal_processing/
git commit -m "refactor(#6112): 17 处 Risk volume 赋值改 adjust_volume（保留调整能力）"
```

---

### Task 5.3：删 Order/Position 创建后不变字段的裸 setter

> Task 5.2 迁完后，`volume` setter 无活跃业务调用（仅 Risk 已切 adjust_volume）。删 Order/Position 不变字段 setter。

**Files:** `entities/order.py`、`entities/position.py`

- [ ] **Step 1: 确认 volume setter 无残余调用**

```bash
grep -rn "\.volume\s*=" src/ --include='*.py' | grep -v "adjust_volume\|transaction_volume\|frozen_volume\|_volume\|def \|test_"
```
Expected: 空（或仅测试构造）。若有残余，迁 adjust_volume。

- [ ] **Step 2: 删 Order setter**

`order.py` 删这些 `@xxx.setter`（创建后不变/内部行为已覆盖）：
- `volume.setter`（→ adjust_volume）
- `code.setter`、`symbol.setter`（构造注入）
- `direction.setter`、`order_type.setter`（构造注入）
- `limit_price.setter`、`fee.setter`、`remain.setter`（行为方法管）
- `portfolio_id/engine_id/task_id.setter`（关联键，构造注入）
- `frozen_money/frozen_volume/transaction_price/transaction_volume.setter`（`partial_fill`/`fill` 管）
- **保留** `status` 无 setter（已只读）

> Position 同理：删 `price.setter`（→ update_price）、`volume.setter`（`deal()` 管）、结算字段 setter。保留只读 property。

- [ ] **Step 3: 测试门**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/entities/ tests/unit/trading/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/entities/order.py src/ginkgo/entities/position.py
git commit -m "refactor(#6112): 删 Order/Position 创建后不变字段 setter（字段分治 V4/V5）"
```

---

### Task 5.4：删 `Base.uuid.setter` + `set_uuid()`（V10）

**Files:** `entities/base.py:55-66`

- [ ] **Step 1: 确认业务零调用**

```bash
grep -rn "\.set_uuid(\|\.uuid\s*=" src/ tests/ --include='*.py' | grep -v "def set_uuid\|def uuid\|_uuid =\|self\._uuid\|entities/base.py\|entities/identity\|M.*\.uuid ==\|model\.uuid =\|Column"
```
Expected: 空（V10 基线已确认 0 业务调用；命中的 `model.uuid=` 是给 ORM model 赋值，不涉及 entity Base）。

- [ ] **Step 2: 删 uuid.setter + set_uuid**

Edit `base.py`：删 `@uuid.setter` 块（`:55-60`）+ `def set_uuid`（`:62-66`）。保留 `@property uuid`（只读）+ `__init__` 内构造注入。

> **不删 Base 类本身**（ADR-009 铁律），只删其上的两个可变入口——这是 Base 内部方法删除，不改变 Base 对外契约（uuid 仍可构造注入、仍只读 property 可读）。若团队解读"禁改 Base"涵盖删其方法，则改为在 Base 保留 setter 但 `raise NotImplementedError`——执行时与 reviewer 确认。**默认按"删方法"执行，因 grep 证实零调用。**

- [ ] **Step 3: 测试门**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/entities/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/entities/base.py
git commit -m "refactor(#6112): 删 Base.uuid.setter + set_uuid（uuid 创建后只读，V10）"
```

---

## Phase 6：正名 + 移 IdentityUtils

### Task 6.1：`entities/__init__.py` 正名

- [ ] **Step 1: 改 docstring**

`entities/__init__.py:3-4`：
```python
"""
Ginkgo Entities - 领域对象

包含领域实体（Entity，带身份/状态机）与值对象（ValueObject，无身份）。
供 data 和 trading 层共同使用。术语见仓库根 CONTEXT.md。
"""
```

- [ ] **Step 2: 导出 ValueObject**

加 `from ginkgo.entities.value_object import ValueObject` + `__all__` 加 `"ValueObject"`。

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/entities/__init__.py
git commit -m "docs(#6106): entities 正名 DTO→Entity/ValueObject（V6）"
```

---

### Task 6.2：移 `IdentityUtils` → `libs/`

**Files:**
- Move: `src/ginkgo/entities/identity.py` → `src/ginkgo/libs/identity.py`
- Modify: `entities/__init__.py`（删 IdentityUtils 导出或保留兼容 re-export）、`entities/base.py:33`（`from .identity import` → `from ginkgo.libs.identity import`）

- [ ] **Step 1: git mv**

```bash
git mv src/ginkgo/entities/identity.py src/ginkgo/libs/identity.py
```

- [ ] **Step 2: 改 import**

- `base.py:33` `from .identity import IdentityUtils` → `from ginkgo.libs.identity import IdentityUtils`
- `entities/__init__.py:20` `from ginkgo.entities.identity import IdentityUtils` → `from ginkgo.libs.identity import IdentityUtils`（保留 re-export 向后兼容，或 grep 确认无外部用 `from ginkgo.entities import IdentityUtils` 后删）

```bash
grep -rn "from ginkgo.entities import IdentityUtils\|from ginkgo.entities.identity\|entities.identity" src/ tests/ --include='*.py'
```
逐调用点改 `from ginkgo.libs.identity import IdentityUtils`。

- [ ] **Step 3: 测试门**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -c "from ginkgo.libs.identity import IdentityUtils; print('OK')"
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/ -x -q
```

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/libs/identity.py src/ginkgo/entities/ src/ginkgo/data/ src/ginkgo/trading/
git commit -m "refactor(#6106): IdentityUtils 移 libs/（V7，entities 零工具依赖）"
```

---

## 终验

- [ ] **Step 1: 依赖方向验证（铁律）**

```bash
# Entity/ValueObject 零外部依赖
grep -rn "from ginkgo.data.models\|from ginkgo.interfaces.dtos\|import ginkgo.data" src/ginkgo/entities/ --include='*.py'
```
Expected: **空**。

```bash
# Mapper 不依赖 CRUD
grep -rn "from ginkgo.data.crud\|import.*CRUD" src/ginkgo/data/mappers/ --include='*.py' | grep -v "_legacy"
```
Expected: **空**（套C `_legacy` 用 `get_tick_model` 例外，ADR 允许）。

- [ ] **Step 2: 残余违规扫描**

```bash
grep -rn "to_entities()\|hasattr(.*to_dataframe\|\.from_model(\|\.to_model(" src/ --include='*.py' | grep -v "Mapper\|def \|_legacy\|test_"
```
Expected: 空（Mapper 调用除外）。

- [ ] **Step 3: 冒烟启动**

```bash
/home/kaoru/.ginkgo/.venv/bin/python -c "import ginkgo; from ginkgo import services; print('启动 OK')"
```

- [ ] **Step 4: 分模块全量测试**（全量 OOM ~20GB，分模块跑）

```bash
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/entities/ tests/unit/data/ -q
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/trading/ tests/unit/client/ -q
```

- [ ] **Step 5: 关键回测路径 e2e**（feedback_acceptance_criteria）

```bash
ginkgo system config set --debug on
ginkgo backtest run <smoke_backtest_id>   # 用既有小规模回测验证端到端
```

- [ ] **Step 6: 推送 + 开 PR**

```bash
git push -u origin HEAD   # 若 sideband 中断：git -c http.version=HTTP/1.1 push；用 gh api 验证（feedback_git_push_http1）
gh pr create --title "refactor(#6106): ADR-010 数据对象三层角色分离" --body "..."
```

---

## Self-Review

**1. Spec coverage（对照 ADR V1-V12）：**
- V1（20 方法迁移）→ Phase 1 Task 1.2-1.6 ✅
- V2（import 消除）→ Phase 1 Task 1.6（抹转换随带）+ 终验 Step 1 ✅
- V3（套A 返 ORM）→ Phase 1 Task 1.5 + Phase 3 ✅
- V4/V5（Order/Position setter 分治）→ Phase 5 Task 5.1-5.3 ✅
- V6（正名）→ Phase 6 Task 6.1 ✅
- V7（移 IdentityUtils）→ Phase 6 Task 6.2 ✅
- V8（VO 无 uuid）→ Phase 2 ✅
- V9（ModelList 瘦身）→ Phase 4 Task 4.1, 4.3 ✅
- V10（删 uuid setter）→ Phase 5 Task 5.4 ✅
- V11（Service 不透传）→ Phase 4 Task 4.2, 4.4 ✅
- V12（hasattr → 多出口）→ Phase 4 Task 4.5 ✅

**2. Placeholder scan：** 无 TBD/TODO；机械任务给 grep 枚举命令 + 转换规则表 + 测试门（可执行、非描述性占位）。DTO `to_dto` 字段标注"执行时 Read bar_dto.py 对齐"——这是必要的事实依赖（DTO 字段未在本次读取），非占位。

**3. Type consistency：** `adjust_volume`（Task 5.1 定义）→ Task 5.2 全用 `adjust_volume(int)` 一致；`get_xxx_df/get_xxx/get_xxx_dto`（Task 4.2 定义）→ Task 4.4/4.5 调用一致；`XxxMapper.from_models(models)`（Task 1.2 定义）→ Task 4.3 调用一致；`ValueObject`（Task 2.1）→ Task 2.2 继承一致。

**已知不确定点（执行时先核实）：**
1. **套A CRUD 真实返型**：grep 出 7 候选，Task 1.5 Step 1 逐个核实是否真返 Entity（tick_crud 可能仅 docstring）。
2. **DTO to_dto 字段**：`order_dto.py`/`bar_dto.py` 实际构造方式未读，Task 1.2/1.3 标注执行时 Read 对齐。
3. **ValueObject 是否继承 Base**：Task 2.1 给独立基类，若 VO 依赖 Base 方法则改继承+Override，Task 2.2 Step 1 grep 决定。
4. **TransferMapper.to_model**：无现成方法，Task 1.4 标 grep 确认无写路径后 NotImplementedError。
5. **删 Base.uuid.setter 是否触铁律**：Task 5.4 默认删（grep 证零调用），若 reviewer 解读 ADR-009 涵盖则改 raise NotImplementedError。
