"""TickMapper — Tick Entity ↔ MTick ORM 转换（ADR-010）。

承接原 Tick.to_model / Tick.from_model 内嵌逻辑（entities/tick.py:131-185）。

VO 动态表特例：ORM 是动态 tick model（见 crud.tick_crud.get_tick_model，按
频率/市场选表）。to_model 保留 model_class 形参——调用方传动态子类
（get_tick_model 返回值），Mapper **不调 get_tick_model**（CRUD 职责，铁律：
不 import CRUD）。MTick.__abstract__=True，默认值 MTick 仅签名占位，
实际构造由调用方传具体子类。

DTO 决策：未实现 to_dto。PriceUpdateDTO.from_tick 接收的是 EventPriceUpdate
事件对象（含 bid_price/ask_price 等 Tick entity 没有的字段），不是 Tick entity；
且 from_tick 全仓零调用方（data_manager.py 直接 PriceUpdateDTO(...) 构造）。
语义错位 + 无调用方 → from_tick 留 Task 1.6 直接删除。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MTick
from ginkgo.entities import Tick
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class TickMapper:
    """Tick 双态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Tick, model_class=MTick) -> MTick:
        """Entity → ORM。model_class 形参保留（VO 动态表选择）。

        忠实原码（tick.py:131-149）：model = model_class() + model.update(
        code, price, volume, direction, timestamp, source)。update 内部做
        enum→int validate_input。
        """
        model = model_class()
        model.update(
            entity.code,  # code 作为第一个位置参数
            price=entity.price,
            volume=entity.volume,
            direction=entity.direction,
            timestamp=entity.timestamp,
            source=entity.source,
        )
        return model

    @staticmethod
    def from_model(model: MTick) -> Tick:
        """ORM → Entity。direction/source 用 from_int 转回 enum（忠实原码 tick.py:173-176）。

        isinstance 守卫保留（动态子类仍是 MTick 子类，守卫成立）。
        """
        if not isinstance(model, MTick):
            raise TypeError(f"Expected MTick instance, got {type(model).__name__}")

        # direction/source 从 int 转回 enum（忠实原码）
        direction = TICKDIRECTION_TYPES.from_int(model.direction) or TICKDIRECTION_TYPES.VOID
        source = SOURCE_TYPES.from_int(model.source) or SOURCE_TYPES.OTHER

        return Tick(
            code=model.code,
            price=model.price,
            volume=model.volume,
            direction=direction,
            timestamp=model.timestamp,
            source=source,
        )

    @staticmethod
    def from_models(models) -> List[Tick]:
        return [TickMapper.from_model(m) for m in models]
