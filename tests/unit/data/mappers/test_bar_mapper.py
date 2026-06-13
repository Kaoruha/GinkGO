"""BarMapper 单测（ADR-010 Task 1.3）。

覆盖：
- to_model/from_model roundtrip，close 保真（Decimal）
- from_model 拒绝非 MBar
- to_dto smoke（symbol=code 映射、对接 BarDTO）
- model_to_dto 直转
"""
from decimal import Decimal

import pytest

from ginkgo.enums import FREQUENCY_TYPES
from ginkgo.entities import Bar
from ginkgo.data.mappers.bar_mapper import BarMapper


def _make_bar():
    return Bar(
        code="000001.SZ",
        open=10,
        high=11,
        low=9,
        close=10.5,
        volume=1000,
        amount=10500,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp="2025-01-02",
    )


def test_bar_roundtrip():
    """to_model → from_model，close Decimal 保真。"""
    bar = _make_bar()
    model = BarMapper.to_model(bar)
    assert model.code == "000001.SZ"
    back = BarMapper.from_model(model)
    assert back.code == "000001.SZ"
    assert back.close == Decimal("10.5")


def test_from_model_rejects_wrong_type():
    with pytest.raises(TypeError):
        BarMapper.from_model(object())


def test_from_models_batch():
    bars = [_make_bar(), _make_bar()]
    models = [BarMapper.to_model(b) for b in bars]
    restored = BarMapper.from_models(models)
    assert len(restored) == 2
    assert all(b.code == "000001.SZ" for b in restored)


def test_to_dto_smoke():
    """to_dto：symbol=code 映射，OHLCV 经 pydantic 转 float。"""
    bar = _make_bar()
    dto = BarMapper.to_dto(bar)
    assert dto.symbol == "000001.SZ"
    assert dto.close == 10.5
    assert dto.volume == 1000.0


def test_model_to_dto_smoke():
    """ORM→DTO 直转（路径①，经 Entity）。"""
    bar = _make_bar()
    model = BarMapper.to_model(bar)
    dto = BarMapper.model_to_dto(model)
    assert dto.symbol == "000001.SZ"
    assert dto.close == 10.5
