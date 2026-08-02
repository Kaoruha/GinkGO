"""SignalMapper — Signal Entity ↔ MSignal ORM 转换（ADR-010 / ADR-029 Task 6）。

承接原 Signal.to_model / Signal.from_model 内嵌逻辑
（entities/signal.py:371-431）。无 SignalDTO（项目未定义），故只提供
to_model / from_model / from_models 三方法。

to_model 忠实原码：update() 3 位置参数（portfolio_id/engine_id/task_id），
update 后 model.uuid = entity.uuid（给 ORM 赋 entity uuid，原码行为保留）。

ADR-029 Task 6 收敛补全（对标原 signal_crud._convert_input_item override 写、
mapper 漏写的字段缺口）：
- ``business_timestamp`` 写入（经 datetime_normalize，原 mapper 漏）
- ``uuid`` 还原（原 mapper 自承丢失 bug，与 Order 同形，本 task 修正）
- ``source``/``direction`` 经 MSignal.update→validate_input→int 双向保真
  （MSignal.update 的 ``or -1`` falsy 吞 0 bug 同步修，见 model_signal.py）

铁律：不 import CRUD。``to_dataframe`` 为 DF 下沉试点（ADR-025；enum 映射经
``__table__`` 反射 ADR-031 c1），输出与 CRUD ``_convert_models_to_dataframe``
等价（对照实证 test_signal_order_df_mapper_parity）。
"""
import pandas as pd
from typing import List

from ginkgo.data.models import MSignal
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class SignalMapper:
    """Signal 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def entity_to_model(entity: Signal) -> MSignal:
        """Entity → ORM。3 位置参数 + model.uuid 赋值 + business_timestamp 写入。

        ADR-029 Task 6:补 business_timestamp(原 signal_crud._convert_input_item
        override 写、mapper 漏写,导致 roundtrip 丢字段)。business_timestamp 经
        MSignal.update→datetime_normalize 存 datetime;source/direction 经
        MSignal.update→validate_input 存 int(0 是合法值,MSignal.update 已修 or-1 bug)。
        """
        model = MSignal()
        model.update(
            entity.portfolio_id,
            entity.engine_id,
            entity.task_id,
            timestamp=entity.timestamp,
            code=entity.code,
            direction=entity.direction,
            reason=entity.reason,
            source=entity.source,
            volume=entity.volume,
            weight=entity.weight,
            strength=entity.strength,
            confidence=entity.confidence,
            business_timestamp=entity.business_timestamp,  # 补:经 datetime_normalize
        )
        model.uuid = entity.uuid
        return model

    @staticmethod
    def model_to_entity(model: MSignal) -> Signal:
        """ORM → Entity。direction/source int→enum + uuid 还原 + business_timestamp 还原。

        ADR-029 Task 6:补 uuid 还原(原 mapper 自承丢失 bug,与 Order 同形) +
        business_timestamp 还原(经 TimeMixin kwarg 消费)。
        """
        if not isinstance(model, MSignal):
            raise TypeError(f"Expected MSignal instance, got {type(model).__name__}")

        entity_kwargs = dict(
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            task_id=model.task_id,
            timestamp=model.timestamp,
            code=model.code,
            direction=DIRECTION_TYPES(model.direction),
            reason=model.reason,
            source=SOURCE_TYPES(model.source),
            volume=model.volume,
            weight=model.weight,
            strength=model.strength,
            confidence=model.confidence,
            uuid=model.uuid,  # 补:原 mapper 自承丢失,与 Order 同形 bug 修正
        )
        # business_timestamp 还原(经 TimeMixin kwarg 消费,None 不传走默认)
        if model.business_timestamp is not None:
            entity_kwargs["business_timestamp"] = model.business_timestamp
        return Signal(**entity_kwargs)

    @staticmethod
    def models_to_entities(models) -> List[Signal]:
        return [SignalMapper.model_to_entity(m) for m in models]

    # ------------------------------------------------------------------
    # ORM → DataFrame（DF 下沉试点，ADR-025；enum 映射经 __table__ 反射，ADR-031）
    # ------------------------------------------------------------------
    @staticmethod
    def models_to_dataframe(models) -> pd.DataFrame:
        """ORM 列表 → DataFrame。enum 字段 int→enum 实例（经 ``__table__`` 反射）。

        无副作用纯转换（不改 model）；输出与 CRUD ``_convert_models_to_dataframe``
        等价（对照实证 ``test_signal_order_df_mapper_parity``）。DF 出口下沉 mapper
        的试点（见 ADR-031 Future Work，ADR-029 §Decision 9 已在 _df.py 落地）。
        """
        if not models:
            return pd.DataFrame()
        mappings = {}
        for col in models[0].__table__.columns:
            enum_cls = (col.info or {}).get("enum")
            if enum_cls is not None:
                mappings[col.name] = enum_cls
        rows = []
        for m in models:
            d = m.__dict__.copy()
            d.pop("_sa_instance_state", None)
            for name, enum_cls in mappings.items():
                v = d.get(name)
                if v is None:
                    continue
                try:
                    d[name] = enum_cls(v)
                except (ValueError, TypeError):
                    pass  # 保留原值（对照 CRUD _safe_enum_convert）
            rows.append(d)
        return pd.DataFrame(rows)
