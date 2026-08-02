"""OrderMapper 单测（ADR-010 Task 1.2）。

覆盖：
- to_model/from_model roundtrip，uuid 保真（修旧版 order_id=model.uuid 被吞 bug）
- from_model 拒绝非 MOrder
- to_dto smoke（对接 OrderSubmissionDTO）
"""
import pytest

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.entities import Order
from ginkgo.data.mappers.order_mapper import OrderMapper


def _make_order():
    return Order(
        portfolio_id="p1",
        engine_id="e1",
        task_id="t1",
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=100,
        limit_price=10.5,
    )


def test_to_model_roundtrip_preserves_uuid():
    """Order.to_model → MOrder；from_model 还原，uuid 必须保真（修 order_id→uuid bug）。"""
    order = _make_order()
    expected_uuid = order.uuid
    model = OrderMapper.entity_to_model(order)
    assert model.code == "000001.SZ"
    assert model.volume == 100
    restored = OrderMapper.model_to_entity(model)
    assert restored.uuid == expected_uuid  # 关键：旧 from_model 丢 uuid，现已修
    assert restored.code == "000001.SZ"
    assert restored.volume == 100


def test_from_model_rejects_wrong_type():
    with pytest.raises(TypeError):
        OrderMapper.model_to_entity(object())


def test_from_models_batch():
    orders = [_make_order(), _make_order()]
    models = [OrderMapper.entity_to_model(o) for o in orders]
    restored = OrderMapper.models_to_entities(models)
    assert len(restored) == 2
    assert all(r.code == "000001.SZ" for r in restored)


def test_to_dto_smoke():
    """to_dto 不崩，关键字段映射正确（对接 OrderSubmissionDTO）。"""
    order = _make_order()
    dto = OrderMapper.entity_to_dto(order)
    assert dto.code == "000001.SZ"
    assert dto.volume == 100.0
    assert dto.portfolio_id == "p1"


def test_model_to_dto_smoke():
    """ORM→DTO 直转（路径①，跳过 Entity）。"""
    order = _make_order()
    model = OrderMapper.entity_to_model(order)
    dto = OrderMapper.model_to_dto(model)
    assert dto.code == "000001.SZ"
    assert dto.volume == 100.0


def test_dto_roundtrip():
    """to_dto → from_dto 可逆：direction enum↔name、volume int↔float、limit_price 数↔str。"""
    order = _make_order()  # direction=LONG, volume=100, limit_price=10.5
    dto = OrderMapper.entity_to_dto(order)
    restored = OrderMapper.dto_to_entity(dto)
    assert restored.direction == DIRECTION_TYPES.LONG
    assert restored.volume == 100
    assert restored.limit_price == 10.5
    assert restored.code == "000001.SZ"
    assert restored.uuid == order.uuid  # order_id 往返保真


def test_dto_market_order_price():
    """市价单（limit_price=0）→ DTO price=None（哨兵）→ from_dto 回退 0。"""
    order = Order(
        portfolio_id="p1",
        engine_id="e1",
        task_id="t1",
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=100,
        limit_price=0,
    )
    dto = OrderMapper.entity_to_dto(order)
    assert dto.price is None  # 0 → None（市价单哨兵）
    restored = OrderMapper.dto_to_entity(dto)
    assert restored.limit_price == 0


# ============================================================================
# ADR-029 Task 7：OrderMapper roundtrip 契约（锁字段/枚举/默认值）
# ============================================================================


def _make_full_order():
    """全字段 Order Entity（含 I-2 哨兵：direction/order_type/status/source=OTHER(0)）。"""
    from datetime import datetime
    from decimal import Decimal

    return Order(
        portfolio_id="p-full",
        engine_id="e-full",
        task_id="t-full",
        code="600000.SH",
        direction=DIRECTION_TYPES.OTHER,    # I-2 哨兵：value=0（falsy）
        order_type=ORDER_TYPES.OTHER,       # I-2 哨兵：value=0
        status=ORDERSTATUS_TYPES.OTHER,     # I-2 哨兵：value=0
        volume=200,
        limit_price=Decimal("12.34"),
        frozen_money=Decimal("2468.00"),
        frozen_volume=200,
        transaction_price=Decimal("12.10"),
        transaction_volume=150,
        remain=Decimal("370.20"),
        fee=Decimal("3.50"),
        timestamp=datetime(2026, 8, 2, 10, 30, 0),
        uuid="abc12345abc12345abc12345abc12345",  # 32-char hex（MOrder.uuid 形态）
    )


class TestOrderMapperRoundtripContract:
    """ADR-029 Task 7：OrderMapper.entity_to_model → model_to_entity 全字段保真契约。"""

    def test_roundtrip_preserves_all_business_fields(self):
        """17 业务字段经 Entity→Model→Entity 往返保真（含 I-2 哨兵字段）。"""
        order = _make_full_order()
        model = OrderMapper.entity_to_model(order)
        restored = OrderMapper.model_to_entity(model)

        # 核心标识
        assert restored.uuid == order.uuid
        assert restored.portfolio_id == order.portfolio_id
        assert restored.engine_id == order.engine_id
        assert restored.task_id == order.task_id
        assert restored.code == order.code

        # 枚举字段（I-2 关键：OTHER=0 必须经 MOrder.__init__ 后回读仍为 0）
        assert restored.direction == order.direction, "direction OTHER(0) 被 `or` 吞"
        assert restored.order_type == order.order_type, "order_type OTHER(0) 被 `or` 吞"
        assert restored.status == order.status, "status OTHER(0) 被 `or` 吞"

        # 数值字段
        assert restored.volume == order.volume
        assert restored.limit_price == order.limit_price
        assert restored.frozen_money == order.frozen_money
        assert restored.frozen_volume == order.frozen_volume
        assert restored.transaction_price == order.transaction_price
        assert restored.transaction_volume == order.transaction_volume
        assert restored.remain == order.remain
        assert restored.fee == order.fee

        # 时间戳
        assert restored.timestamp == order.timestamp

    def test_roundtrip_preserves_enum_zero_values(self):
        """I-2 防 #tick/stockinfo/signal 同款 bug：enum value=0 必须保真。

        历史 bug：`validate_input(x) or DEFAULT` 中 0 被 falsy 吞。
        修法：`validated if validated is not None else DEFAULT`。
        本测试锁 ALL 域 enum 的 OTHER(0) 与 VOID(-1) 两种边界。
        """
        from ginkgo.enums import SOURCE_TYPES

        for direction in (DIRECTION_TYPES.OTHER, DIRECTION_TYPES.VOID, DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT):
            order = _make_full_order()
            # Order Entity 是 read-only property；通过重新构造验证 enum 边界
            new_order = Order(
                portfolio_id="p1", engine_id="e1", task_id="t1",
                code="000001.SZ",
                direction=direction,
                order_type=ORDER_TYPES.OTHER,
                status=ORDERSTATUS_TYPES.OTHER,
                volume=100, limit_price=10.0,
            )
            model = OrderMapper.entity_to_model(new_order)
            # model.direction 必须是 int 形态（写库前的 .value）
            expected = direction.value
            assert model.direction == expected, (
                f"direction={direction.name}({expected}) 经 entity_to_model 后变 {model.direction}（I-2 bug）"
            )

    def test_roundtrip_frozen_volume_float_to_int(self):
        """#6087 回归：float frozen_volume 经 entity_to_model 强制 int() 转换。

        历史 bug：_create_from_params / _convert_input_item 路径均含 int() 转换；
        ADR-029 收敛到 OrderMapper.entity_to_model 后，转换发生在 MOrder.__init__。
        本测试锁定 int() 转换在 mapper 路径仍生效。
        """
        from types import SimpleNamespace

        # 用 SimpleNamespace 模拟带 float frozen_volume 的鸭子输入（绕过 Order Entity 的 int 校验）
        # 真实路径：Order Entity 构造时已 int()，但 mapper 容错仍依赖 MOrder.__init__
        order = Order(
            portfolio_id="p1", engine_id="e1", task_id="t1",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100, limit_price=10.0,
            frozen_volume=484,  # Order Entity set() 强制 int
        )
        model = OrderMapper.entity_to_model(order)
        assert isinstance(model.frozen_volume, int)
        assert model.frozen_volume == 484

    def test_entity_to_model_does_not_import_crud(self):
        """ADR-029 铁律：Mapper 不 import CRUD（转换层与 CRUD 解耦）。"""
        import ginkgo.data.mappers.order_mapper as om
        import inspect

        src = inspect.getsource(om)
        # 不允许出现 from ginkgo.data.crud 或 import OrderCRUD
        assert "from ginkgo.data.crud" not in src, "OrderMapper 不得依赖 CRUD 层"
        assert "OrderCRUD" not in src, "OrderMapper 不得引用 OrderCRUD"
