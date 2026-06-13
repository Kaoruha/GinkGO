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
    model = OrderMapper.to_model(order)
    assert model.code == "000001.SZ"
    assert model.volume == 100
    restored = OrderMapper.from_model(model)
    assert restored.uuid == expected_uuid  # 关键：旧 from_model 丢 uuid，现已修
    assert restored.code == "000001.SZ"
    assert restored.volume == 100


def test_from_model_rejects_wrong_type():
    with pytest.raises(TypeError):
        OrderMapper.from_model(object())


def test_from_models_batch():
    orders = [_make_order(), _make_order()]
    models = [OrderMapper.to_model(o) for o in orders]
    restored = OrderMapper.from_models(models)
    assert len(restored) == 2
    assert all(r.code == "000001.SZ" for r in restored)


def test_to_dto_smoke():
    """to_dto 不崩，关键字段映射正确（对接 OrderSubmissionDTO）。"""
    order = _make_order()
    dto = OrderMapper.to_dto(order)
    assert dto.code == "000001.SZ"
    assert dto.volume == 100.0
    assert dto.portfolio_id == "p1"


def test_model_to_dto_smoke():
    """ORM→DTO 直转（路径①，跳过 Entity）。"""
    order = _make_order()
    model = OrderMapper.to_model(order)
    dto = OrderMapper.model_to_dto(model)
    assert dto.code == "000001.SZ"
    assert dto.volume == 100.0
