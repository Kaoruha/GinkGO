# Upstream: 缩放型风控(VolatilityRisk 等)/Sizer 等需对齐最小交易单位的组件
# Downstream: 无外部依赖纯 Mixin 功能
# Role: LotAlignableMixin 提供 lot_size 配置与 align_to_lot 对齐能力,支持不同市场最小交易单位




"""
最小交易单位(lot)对齐 Mixin

为缩放型风控/Sizer 等组件提供成交量向下取整对齐到 lot_size 整数倍的能力。
A 股默认 100 股/手;参数化以支持港股/美股/期货等不同最小交易单位(#6038)。

混入此 Mixin 的组件需在 __init__ 中设置 self._lot_size(建议默认 100,A 股)。
"""


class LotAlignableMixin:
    """最小交易单位(lot)对齐 Mixin。

    为缩放型风控/Sizer 等组件提供 lot 对齐能力。组件需在 __init__ 中
    设置 self._lot_size(建议默认 100,保持 A 股现状)。
    """

    @property
    def lot_size(self) -> int:
        """最小交易单位(手)。"""
        return self._lot_size

    def align_to_lot(self, volume: int) -> int:
        """将成交量向下取整对齐到 lot_size 的整数倍。

        Args:
            volume: 原始成交量

        Returns:
            int: 对齐后的成交量(不足 1 手时返回 0,调用方据此拒单)
        """
        return (int(volume) // self._lot_size) * self._lot_size
