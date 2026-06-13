"""OrderMapper — Order Entity ↔ MOrder ORM ↔ OrderSubmissionDTO 转换（ADR-010）。

转换收敛层第一个原型。承接原 Order.to_model / Order.from_model 内嵌逻辑，
并修正 from_model 的 order_id=model.uuid（Order.__init__ 无此形参，被 kwargs 吞掉
导致 uuid 丢失）→ uuid=model.uuid。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.data.models import MOrder
from ginkgo.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class OrderMapper:
    """Order 三态互转。无状态，全部静态方法。"""

    # ------------------------------------------------------------------
    # Entity ↔ ORM
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Order) -> MOrder:
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
    def from_model(model: MOrder) -> Order:
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
    def from_models(models) -> List[Order]:
        return [OrderMapper.from_model(m) for m in models]

    # ------------------------------------------------------------------
    # Entity/ORM ↔ DTO
    #
    # 项目无 order_dto.py；Order Entity 最贴近的 DTO 出口是 OrderSubmissionDTO
    # （ExecutionNode → TradeGatewayAdapter 的订单提交消息）。direction enum→name
    # 字符串、volume int→float、limit_price Decimal→str（DTO 字段定义为 str 以
    # 避免浮点精度丢失）。
    # ------------------------------------------------------------------
    @staticmethod
    def to_dto(entity: Order):
        """Entity → OrderSubmissionDTO。"""
        from ginkgo.interfaces.dtos.order_submission_dto import OrderSubmissionDTO

        price = None
        if entity.limit_price is not None and float(entity.limit_price) != 0:
            price = str(entity.limit_price)

        return OrderSubmissionDTO(
            order_id=entity.uuid,
            portfolio_id=entity.portfolio_id,
            code=entity.code,
            direction=entity.direction.name,
            volume=float(entity.volume),
            price=price,
            timestamp=entity.timestamp.isoformat() if entity.timestamp else None,
        )

    @staticmethod
    def from_dto(dto) -> Order:
        """OrderSubmissionDTO → Entity。direction name→enum；price/volume 还原。"""
        from ginkgo.interfaces.dtos.order_submission_dto import OrderSubmissionDTO

        if not isinstance(dto, OrderSubmissionDTO):
            raise TypeError(f"Expected OrderSubmissionDTO, got {type(dto).__name__}")

        direction = DIRECTION_TYPES[dto.direction]

        limit_price = 0
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
    def model_to_dto(model: MOrder):
        """ORM → DTO 直转（路径①，跳过 Entity）。"""
        from ginkgo.interfaces.dtos.order_submission_dto import OrderSubmissionDTO

        price = None
        if model.limit_price is not None and float(model.limit_price) != 0:
            price = str(model.limit_price)

        direction = DIRECTION_TYPES(model.direction).name

        timestamp = None
        if model.timestamp is not None:
            timestamp = model.timestamp.isoformat() if hasattr(model.timestamp, "isoformat") else str(model.timestamp)

        return OrderSubmissionDTO(
            order_id=model.uuid,
            portfolio_id=model.portfolio_id,
            code=model.code,
            direction=direction,
            volume=float(model.volume),
            price=price,
            timestamp=timestamp,
        )
