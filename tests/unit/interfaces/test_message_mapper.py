# Upstream: ADR-025 第②步 MessageMapper (interfaces/mappers/message_mapper.py)
# Role: 验证 Kafka 入站 DTO↔Event/Entity 转换 + β 运行期构造校验 (model_validate)

"""ADR-025 第②步 MessageMapper 单元测试。

覆盖:
- decode: β 校验 (合法 dict → DTO; 缺字段 / 类型错 → ValueError 响亮 raise)
- price_update_to_event: PriceUpdateDTO → EventPriceUpdate(payload=Bar), OHLC↔price 兜底
- feedback_to_event: OrderFeedbackDTO + Order → EventOrderPartiallyFilled
- submission_to_order: OrderSubmissionDTO → Order (limit_price←price drift 修正,
  direction int value 还原)
"""

import pytest

from ginkgo.interfaces.mappers import MessageMapper
from ginkgo.interfaces.dtos import PriceUpdateDTO, OrderFeedbackDTO, OrderSubmissionDTO
from ginkgo.entities import Order
from ginkgo.enums import (
    DIRECTION_TYPES,
    PRICEINFO_TYPES,
    FREQUENCY_TYPES,
)


class TestDecode:
    def test_decode_valid_price_update(self):
        raw = {"symbol": "600000.SH", "price": 10.5, "volume": 1000,
               "amount": 10500, "timestamp": "2026-07-25T10:00:00"}
        dto = MessageMapper.decode(raw, PriceUpdateDTO)
        assert dto.symbol == "600000.SH"
        assert dto.price == 10.5

    def test_decode_missing_required_raises_valueerror(self):
        # β 校验: symbol required, 缺必响亮 raise (ADR-025 §3 禁吞禁 stub)
        with pytest.raises(ValueError):
            MessageMapper.decode({"price": 10}, PriceUpdateDTO)

    def test_decode_wrong_type_raises_valueerror(self):
        # volume 应 float; "abc" 不可解析 → ValidationError → ValueError
        with pytest.raises(ValueError):
            MessageMapper.decode({"symbol": "X", "volume": "abc"}, PriceUpdateDTO)


class TestPriceUpdateToEvent:
    def test_bar_payload_ohlc_fallback_to_price(self):
        dto = PriceUpdateDTO(symbol="600000.SH", price=10.5, volume=1000, amount=10500)
        ev = MessageMapper.price_update_to_event(dto)
        assert ev.price_type == PRICEINFO_TYPES.BAR
        assert ev.code == "600000.SH"
        assert float(ev.close) == 10.5
        # OHLC 缺失 → or price 兜底 (同 PriceUpdateDTO.to_bar_dict 语义)
        assert float(ev.open) == 10.5
        assert float(ev.high) == 10.5
        assert float(ev.low) == 10.5

    def test_bar_keeps_explicit_ohlc(self):
        # Bar 实体 OHLC 存 Decimal; 非二进制精确值(10.8/9.2)须 float() 归一比对
        dto = PriceUpdateDTO(symbol="X", price=10.0, open_price=9.5,
                             high_price=10.8, low_price=9.2)
        ev = MessageMapper.price_update_to_event(dto)
        assert float(ev.open) == 9.5
        assert float(ev.high) == 10.8
        assert float(ev.low) == 9.2
        assert float(ev.close) == 10.0

    def test_bar_frequency_day_default(self):
        # DTO 未携带 frequency → DAY 兜底 (同 data/mappers/bar_mapper)
        dto = PriceUpdateDTO(symbol="X", price=1.0)
        ev = MessageMapper.price_update_to_event(dto)
        assert ev.payload.frequency == FREQUENCY_TYPES.DAY


class TestSubmissionToOrder:
    def test_limit_price_from_price_field(self):
        # drift 修正: DTO 无 limit_price, 旧代码 order_data['limit_price'] 必 KeyError;
        # 正解 limit_price 取 dto.price (字符串 → float)
        dto = OrderSubmissionDTO(order_id="abc", portfolio_id="p1", code="X",
                                 direction="1", volume=100, price="10.5")
        order = MessageMapper.submission_to_order(dto)
        assert order.limit_price == 10.5
        assert order.code == "X"
        assert order.volume == 100

    def test_direction_int_value_restored(self):
        # listener_thread 发 event.direction.value (int); DTO str 强转; int() 还原
        dto = OrderSubmissionDTO(order_id="a", portfolio_id="p", code="X",
                                 direction="2", volume=1, price="1")  # SHORT=2
        order = MessageMapper.submission_to_order(dto)
        assert order.direction == DIRECTION_TYPES.SHORT

    def test_price_none_defaults_zero(self):
        dto = OrderSubmissionDTO(order_id="a", portfolio_id="p", code="X",
                                 direction="1", volume=1)  # price None
        order = MessageMapper.submission_to_order(dto)
        assert order.limit_price == 0.0


class TestFeedbackToEvent:
    def test_event_from_dto_and_order(self):
        src = Order(portfolio_id="p", code="X", direction=DIRECTION_TYPES.LONG,
                    volume=100, limit_price=10.0)
        dto = OrderFeedbackDTO(order_id="abc", portfolio_id="p", engine_id="e",
                               task_id="t", code="X", direction="1",
                               filled_quantity=50, fill_price=10.5,
                               timestamp="2026-07-25T10:01:00")
        ev = MessageMapper.feedback_to_event(dto, src)
        assert ev.filled_quantity == 50
        assert ev.fill_price == 10.5
        assert ev.order is src
        # remaining = volume - transaction_volume - filled = 100 - 0 - 50
        assert ev.remaining_quantity == 50
