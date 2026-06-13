"""BarMapper — Bar Entity ↔ MBar ORM ↔ BarDTO 转换（ADR-010）。

承接原 Bar.to_model / Bar.from_model 内嵌逻辑（entities/bar.py:254-311），
及 BarDTO.from_bar 的 DTO 映射逻辑（interfaces/dtos/bar_dto.py，本 Task 删除该方法）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MBar
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.interfaces.dtos.bar_dto import BarDTO


class BarMapper:
    """Bar 三态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Bar) -> MBar:
        """Entity → ORM。code 作为 singledispatch update 的第一个位置参数。"""
        model = MBar()
        model.update(
            entity.code,
            open=entity.open,
            high=entity.high,
            low=entity.low,
            close=entity.close,
            volume=entity.volume,
            amount=entity.amount,
            frequency=entity.frequency,
            timestamp=entity.timestamp,
        )
        return model

    @staticmethod
    def from_model(model: MBar) -> Bar:
        """ORM → Entity。frequency int→enum（from_int，兜底 DAY）。"""
        if not isinstance(model, MBar):
            raise TypeError(f"Expected MBar, got {type(model).__name__}")
        frequency = FREQUENCY_TYPES.from_int(model.frequency) or FREQUENCY_TYPES.DAY
        return Bar(
            code=model.code,
            open=model.open,
            high=model.high,
            low=model.low,
            close=model.close,
            volume=model.volume,
            amount=model.amount,
            frequency=frequency,
            timestamp=model.timestamp,
        )

    @staticmethod
    def from_models(models) -> List[Bar]:
        return [BarMapper.from_model(m) for m in models]

    # ------------------------------------------------------------------
    # Entity/ORM ↔ DTO
    #
    # BarDTO 是 Kafka 出站 K 线载荷。字段与 Bar 实体不同名：DTO 用 symbol（非
    # code）、period（非 frequency）。to_dto 搬运自原 BarDTO.from_bar——不映射
    # frequency（period 默认 "1d"），OHLCV 依赖 pydantic 将 Decimal 强转 float。
    # Bar 无 from_dto（BarDTO 出站单向，YAGNI）。
    # ------------------------------------------------------------------
    @staticmethod
    def to_dto(entity: Bar) -> BarDTO:
        """Entity → BarDTO。搬运自 bar_dto.py 原 from_bar 逻辑（本 Task 已删该方法）。"""
        return BarDTO(
            symbol=entity.code,
            timestamp=entity.timestamp,
            open=entity.open,
            high=entity.high,
            low=entity.low,
            close=entity.close,
            volume=entity.volume,
            amount=getattr(entity, "amount", None),
            turnover=getattr(entity, "turnover", None),
            change=getattr(entity, "change", None),
            change_pct=getattr(entity, "change_pct", None),
        )

    @staticmethod
    def model_to_dto(model: MBar) -> BarDTO:
        """ORM → DTO 直转（路径①，经 Entity）。"""
        return BarMapper.to_dto(BarMapper.from_model(model))
