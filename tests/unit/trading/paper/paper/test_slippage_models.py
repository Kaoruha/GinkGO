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
