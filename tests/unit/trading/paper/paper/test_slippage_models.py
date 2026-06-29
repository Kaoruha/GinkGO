# Upstream: ginkgo.trading.paper.slippage_models
# Downstream: pytest
# Role: 滑点模型测试

"""
滑点模型测试

TDD Red 阶段: 测试用例定义，预期失败
"""

import pytest
from decimal import Decimal


@pytest.mark.financial
class TestFixedSlippage:
    """固定滑点测试"""

    def test_buy_with_slippage(self):
        """测试买入加滑点"""
        from ginkgo.trading.paper.slippage_models import FixedSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = FixedSlippage(slippage=Decimal("0.02"))
        result = model.apply(Decimal("10.00"), DIRECTION_TYPES.LONG)
        assert result == Decimal("10.02")

    def test_sell_with_slippage(self):
        """测试卖出入滑点"""
        from ginkgo.trading.paper.slippage_models import FixedSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = FixedSlippage(slippage=Decimal("0.02"))
        result = model.apply(Decimal("10.00"), DIRECTION_TYPES.SHORT)
        assert result == Decimal("9.98")

    def test_zero_slippage(self):
        """测试零滑点"""
        from ginkgo.trading.paper.slippage_models import FixedSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = FixedSlippage(slippage=Decimal("0"))
        assert model.apply(Decimal("10.00"), DIRECTION_TYPES.LONG) == Decimal("10.00")
        assert model.apply(Decimal("10.00"), DIRECTION_TYPES.SHORT) == Decimal("10.00")

    def test_negative_slippage_raises(self):
        """测试负滑点抛出异常"""
        from ginkgo.trading.paper.slippage_models import FixedSlippage

        with pytest.raises(ValueError):
            FixedSlippage(slippage=Decimal("-0.01"))

    def test_sell_low_price_clamps_to_minimum(self):
        """#5497: 低价股卖出（price < slippage）不应产生负成交价，clamp 到 0.01。

        根因: apply() 卖出分支 `price - slippage`，price=0.03 slippage=0.05 时
        得 -0.02，负成交价污染 cash 余额。
        """
        from ginkgo.trading.paper.slippage_models import FixedSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = FixedSlippage(slippage=Decimal("0.05"))
        result = model.apply(Decimal("0.03"), DIRECTION_TYPES.SHORT)
        assert result == Decimal("0.01"), f"低价股卖出应 clamp 到 0.01，实际 {result}"
        assert result > 0, "成交价必须为正"

    def test_sell_price_above_slippage_not_clamped(self):
        """#5497 回归保护: price > slippage 的正常低价股不触发 clamp。"""
        from ginkgo.trading.paper.slippage_models import FixedSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = FixedSlippage(slippage=Decimal("0.01"))
        # price=0.05 > slippage=0.01，正常计算 0.04，不应 clamp
        result = model.apply(Decimal("0.05"), DIRECTION_TYPES.SHORT)
        assert result == Decimal("0.04")


@pytest.mark.financial
class TestPercentageSlippage:
    """百分比滑点测试"""

    def test_buy_percentage(self):
        """测试买入百分比滑点"""
        from ginkgo.trading.paper.slippage_models import PercentageSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = PercentageSlippage(percentage=Decimal("0.001"))  # 0.1%
        result = model.apply(Decimal("10.00"), DIRECTION_TYPES.LONG)
        assert result == Decimal("10.01")

    def test_sell_percentage(self):
        """测试卖出百分比滑点"""
        from ginkgo.trading.paper.slippage_models import PercentageSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = PercentageSlippage(percentage=Decimal("0.001"))  # 0.1%
        result = model.apply(Decimal("10.00"), DIRECTION_TYPES.SHORT)
        assert result == Decimal("9.99")

    def test_large_price(self):
        """测试大额价格"""
        from ginkgo.trading.paper.slippage_models import PercentageSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = PercentageSlippage(percentage=Decimal("0.01"))  # 1%
        result = model.apply(Decimal("1000.00"), DIRECTION_TYPES.LONG)
        assert result == Decimal("1010.00")


@pytest.mark.financial
class TestNoSlippage:
    """无滑点测试"""

    def test_no_slippage_buy(self):
        """测试无滑点买入"""
        from ginkgo.trading.paper.slippage_models import NoSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = NoSlippage()
        assert model.apply(Decimal("10.00"), DIRECTION_TYPES.LONG) == Decimal("10.00")

    def test_no_slippage_sell(self):
        """测试无滑点卖出"""
        from ginkgo.trading.paper.slippage_models import NoSlippage
        from ginkgo.enums import DIRECTION_TYPES

        model = NoSlippage()
        assert model.apply(Decimal("10.00"), DIRECTION_TYPES.SHORT) == Decimal("10.00")
