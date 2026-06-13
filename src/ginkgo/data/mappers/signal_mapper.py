"""SignalMapper — Signal Entity ↔ MSignal ORM 转换（ADR-010）。

承接原 Signal.to_model / Signal.from_model 内嵌逻辑
（entities/signal.py:371-431）。无 SignalDTO（项目未定义），故只提供
to_model / from_model / from_models 三方法。

to_model 忠实原码：update() 3 位置参数（portfolio_id/engine_id/task_id），
update 后 model.uuid = entity.uuid（给 ORM 赋 entity uuid，原码行为保留）。
from_model 还原 direction/source（int→enum），**未传 uuid**（原码即如此——
与 Order 的丢失 bug 同形，但 plan 要求忠实搬运，不加修正；修复留 Task 1.6
删内嵌方法时一并评估）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
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
