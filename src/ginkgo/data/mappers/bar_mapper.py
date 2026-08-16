"""BarMapper — Bar Entity ↔ MBar ORM ↔ BarDTO 转换（ADR-010）。

承接原 Bar.to_model / Bar.from_model 内嵌逻辑（entities/bar.py:254-311），
及 BarDTO.from_bar 的 DTO 映射逻辑（interfaces/dtos/bar_dto.py，本 Task 删除该方法）。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MBar
from ginkgo.entities import Bar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from ginkgo.interfaces.dtos.bar_dto import BarDTO


class BarMapper:
    """Bar 三态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def entity_to_model(entity: Bar) -> MBar:
        """Entity → ORM。code 作为 singledispatch update 的第一个位置参数。

        source/uuid 直传：source 经 update(source=...) 走 SOURCE_TYPES.validate_input
        归一为 int；uuid 不在 update 形参表（MBar.update 只接 OHLCV+code+freq+ts+source），
        直接赋属性。对齐 bar_crud._convert_input_item:81-106 override 字段集（ADR-029 Task 1）。
        """
        model = MBar()
        model.update(
            # code 归一 upper:数据源(tushare ts_code)返回小写 .sz/.sh,而删除
            # 键/查重/预检均按上层大写形态——双态并存曾致 sync_range 的
            # remove(大写)清空旧库 + add_batch(小写)写入残缺(2026-08-16 实例:
            # 000001.SZ 大写日线全灭,仅剩免费权限拉回的小写 2021 段)
            entity.code.upper() if isinstance(entity.code, str) else entity.code,
            open=entity.open,
            high=entity.high,
            low=entity.low,
            close=entity.close,
            volume=entity.volume,
            amount=entity.amount,
            frequency=entity.frequency,
            timestamp=entity.timestamp,
            source=entity.source,
        )
        model.uuid = entity.uuid
        return model

    @staticmethod
    def model_to_entity(model: MBar) -> Bar:
        """ORM → Entity。frequency/source int→enum；uuid 还原。

        frequency 三态：正常值往返；-1（validate_input 未设频哨兵）经 from_int→VOID
        （语义=未知，不伪造为 DAY）；None（DB NULL）兜底 DAY 防 None.frequency 下游
        崩溃。

        source 三态：正常值往返；None/异常→VOID（与 Base 默认一致，from_int(None)→None
        时兜底 VOID 防 None.source 下游崩溃）。

        uuid 还原（ADR-029 Task 1 修复）：旧版以"Bar 业务键为 code+timestamp+frequency，
        uuid 装饰性"为由不还原，但 entity_to_model 已写入；roundtrip 应双向保真，
        与 OrderMapper 同款处理。
        """
        if not isinstance(model, MBar):
            raise TypeError(f"Expected MBar, got {type(model).__name__}")
        frequency = FREQUENCY_TYPES.from_int(model.frequency) or FREQUENCY_TYPES.DAY
        source = SOURCE_TYPES.from_int(model.source) or SOURCE_TYPES.VOID
        bar = Bar(
            code=model.code,
            open=model.open,
            high=model.high,
            low=model.low,
            close=model.close,
            volume=model.volume,
            amount=model.amount,
            frequency=frequency,
            timestamp=model.timestamp,
            uuid=model.uuid,
        )
        bar.set_source(source)
        return bar

    @staticmethod
    def models_to_entities(models) -> List[Bar]:
        return [BarMapper.model_to_entity(m) for m in models]

    # ------------------------------------------------------------------
    # Entity/ORM ↔ DTO
    #
    # BarDTO 是 Kafka 出站 K 线载荷。字段与 Bar 实体不同名：DTO 用 symbol（非
    # code）、period（非 frequency）。to_dto 搬运自原 BarDTO.from_bar——不映射
    # frequency（period 默认 "1d"），OHLCV 依赖 pydantic 将 Decimal 强转 float。
    # amount/turnover/change/change_pct 用 getattr 兜底：Bar 实体仅有 amount，其余
    # 恒 None（保留 from_bar 原样，并为 ORM 直读路径预留兼容）。
    # Bar 无 from_dto（BarDTO 出站单向，YAGNI）。
    # ------------------------------------------------------------------
    @staticmethod
    def entity_to_dto(entity: Bar) -> BarDTO:
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
        """ORM → DTO（经 Entity 组合；Bar 非热路径，省字段映射重复）。"""
        return BarMapper.entity_to_dto(BarMapper.model_to_entity(model))
