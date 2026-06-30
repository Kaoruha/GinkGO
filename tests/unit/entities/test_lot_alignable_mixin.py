# Upstream: tests/unit/entities (实体层测试)
# Downstream: ginkgo.entities.mixins.LotAlignableMixin
# Role: 验证最小交易单位(lot)对齐 Mixin 的对齐能力,覆盖默认 A 股 100 与自定义 lot_size

"""
LotAlignableMixin 最小交易单位对齐能力测试

框架设计不限于 A 股(100 股/手)。Mixin 提供 lot_size 配置与 align_to_lot
对齐能力,支持港股/美股/期货等不同最小交易单位(#6038)。
"""

import pytest

from ginkgo.entities.mixins import LotAlignableMixin


class _Alignable(LotAlignableMixin):
    """测试用宿主:Mixin 依赖 self._lot_size,由宿主 __init__ 负责初始化。"""

    def __init__(self, lot_size: int = 100):
        self._lot_size = lot_size


@pytest.mark.tdd
class TestLotAlignableMixin:
    def test_lot_size_property_exposes_configured_value(self):
        obj = _Alignable(lot_size=100)
        assert obj.lot_size == 100

    def test_align_to_default_lot_100_ashare(self):
        """A 股默认 100 股/手:625 向下对齐到 600。"""
        obj = _Alignable(lot_size=100)
        assert obj.align_to_lot(625) == 600

    def test_align_to_custom_lot_size(self):
        """自定义 lot_size:lot_size=80 时 625 对齐到 560(非 600)。

        证明 Mixin 不依赖硬编码 100,可适配不同市场最小交易单位。"""
        obj = _Alignable(lot_size=80)
        assert obj.align_to_lot(625) == 560

    def test_below_one_lot_returns_zero(self):
        """不足 1 手:62 对齐到 0(调用方据此拒单)。"""
        obj = _Alignable(lot_size=100)
        assert obj.align_to_lot(62) == 0

    def test_exact_multiple_unchanged(self):
        """已是 lot 整数倍时不变:600 → 600。"""
        obj = _Alignable(lot_size=100)
        assert obj.align_to_lot(600) == 600

    def test_us_market_one_share_unit(self):
        """美股 1 股起:lot_size=1 时任意整数不变(625 → 625)。"""
        obj = _Alignable(lot_size=1)
        assert obj.align_to_lot(625) == 625
