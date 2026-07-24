# Upstream: Kafka consumers (node.py / trade_gateway_adapter / data_manager / portfolio_processor)
# Downstream: 领域 Event / Entity (EventPriceUpdate / EventOrderPartiallyFilled / Order)
# Role: ADR-025 四边界 Mapper 家族的 Kafka 入站亚型 —— consumer 唯一转换点

"""
Kafka 入站 MessageMapper (ADR-025 第②步)

四边界 Mapper 家族的 Kafka 亚型。consumer 统一入口::

    raw dict ──decode──▶ DTO (pydantic model_validate) ──xxx_to_event──▶ 领域 Event/Entity

严格模式 (ADR-025 §3 β 运行期构造校验):
    decode 走 pydantic model_validate —— 字段缺失 / 类型错立刻 ValidationError,
    本层转 ValueError 响亮 raise (禁 except 吞 + return stub, #4652 教训)。

消灭的反模式: consumer 拿 raw dict 直接 ``EventXxx(**event_data)`` ——
字段名 drift (symbol↔code / filled_volume↔filled_quantity / limit_price↔price)
与签名 mismatch (EventPriceUpdate 要 payload=Bar 非 code/price/volume) 必崩,
旧代码靠 except 吞 + sleep(1) 静默死路径。
"""

from datetime import datetime
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

from ginkgo.interfaces.dtos import (
    PriceUpdateDTO,
    OrderFeedbackDTO,
    OrderSubmissionDTO,
)
from ginkgo.entities import Order, Bar
from ginkgo.enums import (
    FREQUENCY_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
)
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled


T = TypeVar("T", bound=BaseModel)


class MessageMapper:
    """Kafka 入站消息转换器 (DTO ↔ Event/Entity)。

    唯一转换点: consumer 拿到 raw dict 后必经此类。
    任何 "裸 dict 直构造 Event" 都是 ADR-025 要消灭的反模式。

    不碰 CRUD/DB: feedback_to_event 所需的 Order 由 consumer 从内存注册表
    (ExecutionNode._pending_orders) 注入, Mapper 只做纯转换。
    """

    # ------------------------------------------------------------------
    # decode: raw dict → DTO (β 运行期构造校验)
    # ------------------------------------------------------------------
    @staticmethod
    def decode(raw: dict, dto_cls: Type[T]) -> T:
        """pydantic model_validate 校验, 失败响亮 raise (不吞不 stub)。

        Args:
            raw: Kafka ``message.value`` (json.loads 后的 dict)。
            dto_cls: 目标 DTO 类。

        Returns:
            校验通过的 DTO 实例。

        Raises:
            ValueError: 字段缺失 / 类型错 (内含 ValidationError 细节)。
        """
        try:
            return dto_cls.model_validate(raw)
        except ValidationError as e:
            raise ValueError(
                f"MessageMapper.decode({dto_cls.__name__}) validation failed: {e}"
            ) from e

    # ------------------------------------------------------------------
    # PriceUpdateDTO → EventPriceUpdate
    # ------------------------------------------------------------------
    @staticmethod
    def price_update_to_event(dto: PriceUpdateDTO) -> EventPriceUpdate:
        """PriceUpdateDTO → EventPriceUpdate(payload=Bar)。

        生产端 (data_manager) 发 PriceUpdateDTO (symbol / price / OHLC / volume / amount);
        消费端构造 Bar 当 payload (沿用 PriceUpdateDTO.to_bar_dict 的 OHLC↔price 兜底)。

        frequency: DTO 未携带 → DAY (当日累计 K 线语义, 同 data/mappers/bar_mapper 兜底)。
        修正旧 drift: 旧代码 ``EventPriceUpdate(code=.., price=.., volume=..)`` 既读错字段
        (生产端发 symbol 非 code), 又传错签名 (EventPriceUpdate 要 payload=Bar)。
        """
        price = dto.price
        ts = dto.timestamp
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        bar = Bar(
            code=dto.symbol,
            open=dto.open_price or price or 0.0,
            high=dto.high_price or price or 0.0,
            low=dto.low_price or price or 0.0,
            close=price or 0.0,
            volume=dto.volume or 0.0,
            amount=dto.amount or 0.0,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=ts,
        )
        return EventPriceUpdate(payload=bar)

    # ------------------------------------------------------------------
    # OrderFeedbackDTO + Order → EventOrderPartiallyFilled
    # ------------------------------------------------------------------
    @staticmethod
    def feedback_to_event(
        dto: OrderFeedbackDTO,
        order: Order,
    ) -> EventOrderPartiallyFilled:
        """OrderFeedbackDTO + 原 Order → EventOrderPartiallyFilled。

        Order 由 consumer 从 _pending_orders 注册表取出注入 (Mapper 不碰 CRUD/DB)。
        修正旧 drift: filled_volume→filled_quantity, filled_price→fill_price,
        且签名要 (order, filled_quantity, fill_price) 非 (order_id, code, direction, ...)。
        """
        ts = dto.timestamp
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        return EventOrderPartiallyFilled(
            order=order,
            filled_quantity=dto.filled_quantity,
            fill_price=dto.fill_price,
            timestamp=ts,
            portfolio_id=dto.portfolio_id,
            engine_id=dto.engine_id,
            task_id=dto.task_id,
        )

    # ------------------------------------------------------------------
    # OrderSubmissionDTO → Order (骨架, 供 gateway 重建)
    # ------------------------------------------------------------------
    @staticmethod
    def submission_to_order(dto: OrderSubmissionDTO) -> Order:
        """OrderSubmissionDTO → 骨架 Order (gateway 重建用)。

        修正旧 drift: DTO 无 limit_price 字段, 旧代码 ``order_data['limit_price']`` 必 KeyError;
        正解 limit_price 取 dto.price (字符串格式, 需 float 转换)。
        engine_id / task_id DTO 未携带 → 沿用 gateway 旧默认 (live_engine / live_run)。
        direction: listener_thread 发 ``event.direction.value`` (int), DTO str 字段强转为 str,
        此处 ``int(dto.direction)`` 还原回 enum value (与 order_mapper DIRECTION_TYPES(int) 一致)。
        """
        return Order(
            portfolio_id=dto.portfolio_id,
            engine_id="live_engine",
            task_id="live_run",
            code=dto.code,
            direction=DIRECTION_TYPES(int(dto.direction)),
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=dto.volume,
            limit_price=float(dto.price) if dto.price is not None else 0.0,
        )
