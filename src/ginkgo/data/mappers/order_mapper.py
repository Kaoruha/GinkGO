"""OrderMapper — Order Entity ↔ MOrder ORM ↔ OrderSubmissionDTO 转换（ADR-010）。

转换收敛层第一个原型。承接原 Order.to_model / Order.from_model 内嵌逻辑，
并修正 from_model 的 order_id=model.uuid（Order.__init__ 无此形参，被 kwargs 吞掉
导致 uuid 丢失）→ uuid=model.uuid。

铁律：不 import CRUD。``to_dataframe`` 为 DF 下沉试点（ADR-025；enum 映射经
``__table__`` 反射 ADR-031 c1），输出与 CRUD ``_convert_models_to_dataframe``
等价（对照实证 test_signal_order_df_mapper_parity）。
"""
import pandas as pd
from typing import List, Optional

from ginkgo.data.models import MOrder
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.interfaces.dtos.order_submission_dto import OrderSubmissionDTO


class OrderMapper:
    """Order 三态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # 共享转换 helper（Entity 与 ORM 路径共用，避免 to_dto/model_to_dto DRY）
    # ------------------------------------------------------------------
    @staticmethod
    def _price_to_dto(price) -> Optional[str]:
        """limit_price → DTO price。None 或 0 → None（市价单无价哨兵）；否则 Decimal/float → str。"""
        if price is not None and float(price) != 0:
            return str(price)
        return None

    @staticmethod
    def _ts_to_iso(ts) -> Optional[str]:
        """timestamp → ISO 字符串。datetime 走 isoformat，其余（原始行 str 等）走 str()。"""
        if ts is None:
            return None
        return ts.isoformat() if hasattr(ts, "isoformat") else str(ts)

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def entity_to_model(entity: Order) -> MOrder:
        """Entity → ORM。直构 MOrder（update() 是 singledispatch，全 kwargs 调用会失败）。"""
        return MOrder(
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

    @staticmethod
    def model_to_entity(model: MOrder) -> Order:
        """ORM → Entity。修正：uuid=model.uuid（旧版 order_id= 被丢弃）。"""
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
            uuid=model.uuid,  # 修正：旧 Order.from_model 传 order_id=（无此形参）
            portfolio_id=model.portfolio_id,
            engine_id=model.engine_id,
            task_id=model.task_id,
        )

    @staticmethod
    def models_to_entities(models) -> List[Order]:
        return [OrderMapper.model_to_entity(m) for m in models]

    # ------------------------------------------------------------------
    # ORM → DataFrame（DF 下沉试点，ADR-025；enum 映射经 __table__ 反射，ADR-031）
    # ------------------------------------------------------------------
    @staticmethod
    def models_to_dataframe(models) -> pd.DataFrame:
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

    # ------------------------------------------------------------------
    # Entity/ORM ↔ DTO
    #
    # 项目无 order_dto.py；Order Entity 最贴近的 DTO 出口是 OrderSubmissionDTO
    # （ExecutionNode → TradeGatewayAdapter 的订单提交消息）。direction enum→name
    # 字符串、volume int→float、limit_price Decimal→str（DTO 字段定义为 str 以
    # 避免浮点精度丢失）。
    # ------------------------------------------------------------------
    @staticmethod
    def entity_to_dto(entity: Order) -> OrderSubmissionDTO:
        """Entity → OrderSubmissionDTO。"""
        return OrderSubmissionDTO(
            order_id=entity.uuid,
            portfolio_id=entity.portfolio_id,
            code=entity.code,
            direction=entity.direction.name,
            volume=float(entity.volume),
            price=OrderMapper._price_to_dto(entity.limit_price),
            timestamp=OrderMapper._ts_to_iso(entity.timestamp),
        )

    @staticmethod
    def dto_to_entity(dto) -> Order:
        """OrderSubmissionDTO → Entity。direction name→enum；price/volume 还原。"""
        if not isinstance(dto, OrderSubmissionDTO):
            raise TypeError(f"Expected OrderSubmissionDTO, got {type(dto).__name__}")

        direction = DIRECTION_TYPES[dto.direction]

        limit_price = 0  # 市价单哨兵：DTO 无 price（None/""）时回退 0
        if dto.price is not None and dto.price != "":
            limit_price = float(dto.price)

        return Order(
            portfolio_id=dto.portfolio_id,
            code=dto.code,
            direction=direction,
            volume=int(dto.volume),
            limit_price=limit_price,
            uuid=dto.order_id,
            timestamp=dto.timestamp,
        )

    @staticmethod
    def model_to_dto(model: MOrder) -> OrderSubmissionDTO:
        """ORM → DTO 直转（路径①，跳过 Entity）。"""
        return OrderSubmissionDTO(
            order_id=model.uuid,
            portfolio_id=model.portfolio_id,
            code=model.code,
            direction=DIRECTION_TYPES(model.direction).name,
            volume=float(model.volume),
            price=OrderMapper._price_to_dto(model.limit_price),
            timestamp=OrderMapper._ts_to_iso(model.timestamp),
        )
