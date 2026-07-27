"""SignalMapper — Signal Entity ↔ MSignal ORM 转换（ADR-010）。

承接原 Signal.to_model / Signal.from_model 内嵌逻辑
（entities/signal.py:371-431）。无 SignalDTO（项目未定义），故只提供
to_model / from_model / from_models 三方法。

to_model 忠实原码：update() 3 位置参数（portfolio_id/engine_id/task_id），
update 后 model.uuid = entity.uuid（给 ORM 赋 entity uuid，原码行为保留）。
from_model 还原 direction/source（int→enum），**未传 uuid**（原码即如此——
与 Order 的丢失 bug 同形，但 plan 要求忠实搬运，不加修正；修复留 Task 1.6
删内嵌方法时一并评估）。

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
    def to_model(entity: Signal) -> MSignal:
        """Entity → ORM。3 位置参数 + model.uuid 赋值（原码行为保留）。"""
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
        )
        model.uuid = entity.uuid
        return model

    @staticmethod
    def from_model(model: MSignal) -> Signal:
        """ORM → Entity。direction/source int→enum。

        忠实搬运：原码未传 uuid（与 Order 丢失 bug 同形，此处不加修正，
        留 Task 1.6 抹内嵌方法时统一评估）。
        """
        if not isinstance(model, MSignal):
            raise TypeError(f"Expected MSignal instance, got {type(model).__name__}")

        return Signal(
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
        )

    @staticmethod
    def from_models(models) -> List[Signal]:
        return [SignalMapper.from_model(m) for m in models]

    # ------------------------------------------------------------------
    # ORM → DataFrame（DF 下沉试点，ADR-025；enum 映射经 __table__ 反射，ADR-031）
    # ------------------------------------------------------------------
    @staticmethod
    def to_dataframe(models) -> pd.DataFrame:
        """ORM 列表 → DataFrame。enum 字段 int→enum 实例（经 ``__table__`` 反射）。

        无副作用纯转换（不改 model）；输出与 CRUD ``_convert_models_to_dataframe``
        等价（对照实证 ``test_signal_order_df_mapper_parity``）。DF 出口下沉 mapper
        的试点，落地后 ``ModelList.to_dataframe`` 可委托此处（见 ADR-031 Future Work）。
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
