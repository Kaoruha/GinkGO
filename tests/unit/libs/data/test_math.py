"""math.py 数学工具模块单元测试
性能: 156MB RSS, 0.86s, 18 tests [PASS]

覆盖范围:
- cal_fee(): 佣金计算，含最低佣金、印花税、过户费
- 买入(LONG)和卖出(SHORT)方向差异
- 边界条件（低价、零税率、大额交易）
"""

import sys
from decimal import Decimal
from pathlib import Path

import pytest

_path = str(Path(__file__).parent.parent.parent)
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs.data.math import cal_fee


# ---------------------------------------------------------------------------
# 佣金计算 — 买入方向
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCalFeeLong:
    """买入(LONG)方向佣金计算"""

    def test_basic_long_fee(self):
        """基本买入费用计算

        佣金 = price * tax_rate (不低于5)
        印花税 = price * 0.001
        买入无过户费
        """
        result = cal_fee(DIRECTION_TYPES.LONG, 10000, 0.0003)
        # 佣金 = 10000 * 0.0003 = 3 → 最低佣金5
        # 印花税 = 10000 * 0.001 = 10
        # 合计 = 5 + 10 = 15
        assert result == Decimal("15")

    def test_large_price_long(self):
        """大额交易买入费用

        佣金 = 1000000 * 0.0003 = 300 (>5，按实际)
        印花税 = 1000000 * 0.001 = 1000
        合计 = 300 + 1000 = 1300
        """
        result = cal_fee(DIRECTION_TYPES.LONG, 1000000, 0.0003)
        assert result == Decimal("1300")

    def test_zero_tax_rate_long(self):
        """零税率买入费用

        佣金 = 10000 * 0 = 0 → 最低5
        印花税 = 10000 * 0.001 = 10
        合计 = 5 + 10 = 15
        """
        result = cal_fee(DIRECTION_TYPES.LONG, 10000, 0)
        assert result == Decimal("15")

    def test_high_tax_rate_long(self):
        """高税率买入费用

        佣金 = 10000 * 0.01 = 100 (>5)
        印花税 = 10000 * 0.001 = 10
        合计 = 100 + 10 = 110
        """
        result = cal_fee(DIRECTION_TYPES.LONG, 10000, 0.01)
        assert result == Decimal("110")

    def test_minimum_commission_long(self):
        """低价触发最低佣金（5元）"""
        # 佣金 = 1000 * 0.0001 = 0.1 → 最低5
        # 印花税 = 1000 * 0.001 = 1
        result = cal_fee(DIRECTION_TYPES.LONG, 1000, 0.0001)
        assert result == Decimal("6")

    def test_exact_five_commission_long(self):
        """佣金恰好等于5元时不变"""
        # 佣金 = 50000 * 0.0001 = 5 (=5，不变)
        # 印花税 = 50000 * 0.001 = 50
        result = cal_fee(DIRECTION_TYPES.LONG, 50000, 0.0001)
        assert result == Decimal("55")

    def test_decimal_input_long(self):
        """Decimal 类型输入"""
        result = cal_fee(DIRECTION_TYPES.LONG, Decimal("10000"), Decimal("0.0003"))
        assert result == Decimal("15")

    def test_float_input_long(self):
        """float 类型输入"""
        result = cal_fee(DIRECTION_TYPES.LONG, 10000.0, 0.0003)
        assert result == Decimal("15")


# ---------------------------------------------------------------------------
# 佣金计算 — 卖出方向
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCalFeeShort:
    """卖出(SHORT)方向佣金计算"""

    def test_basic_short_fee(self):
        """基本卖出费用计算

        佣金 = 10000 * 0.0003 = 3 → 最低5
        印花税 = 10000 * 0.001 = 10
        过户费 = 10000 * 0.00002 = 0.2
        合计 = 5 + 10 + 0.2 = 15.2
        """
        result = cal_fee(DIRECTION_TYPES.SHORT, 10000, 0.0003)
        assert result == Decimal("15.2")

    def test_large_price_short(self):
        """大额交易卖出费用

        佣金 = 1000000 * 0.0003 = 300
        印花税 = 1000000 * 0.001 = 1000
        过户费 = 1000000 * 0.00002 = 20
        合计 = 300 + 1000 + 20 = 1320
        """
        result = cal_fee(DIRECTION_TYPES.SHORT, 1000000, 0.0003)
        assert result == Decimal("1320")

    def test_zero_tax_rate_short(self):
        """零税率卖出费用"""
        result = cal_fee(DIRECTION_TYPES.SHORT, 10000, 0)
        # 佣金 = 0 → 5, 印花税 = 10, 过户费 = 0.2
        assert result == Decimal("15.2")

    def test_minimum_commission_short(self):
        """低价触发最低佣金（5元）"""
        # 佣金 = 1000 * 0.0001 = 0.1 → 5
        # 印花税 = 1000 * 0.001 = 1
        # 过户费 = 1000 * 0.00002 = 0.02
        result = cal_fee(DIRECTION_TYPES.SHORT, 1000, 0.0001)
        assert result == Decimal("6.02")

    def test_decimal_input_short(self):
        """Decimal 类型输入"""
        result = cal_fee(DIRECTION_TYPES.SHORT, Decimal("10000"), Decimal("0.0003"))
        assert result == Decimal("15.2")

    def test_float_input_short(self):
        """float 类型输入"""
        result = cal_fee(DIRECTION_TYPES.SHORT, 10000.0, 0.0003)
        assert result == Decimal("15.2")


# ---------------------------------------------------------------------------
# 方向对比
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCalFeeDirectionComparison:
    """买入 vs 卖出费用对比"""

    def test_short_more_expensive_than_long(self):
        """同一条件下卖出费用应高于买入（含过户费）"""
        price = 100000
        tax_rate = 0.0003
        long_fee = cal_fee(DIRECTION_TYPES.LONG, price, tax_rate)
        short_fee = cal_fee(DIRECTION_TYPES.SHORT, price, tax_rate)
        assert short_fee > long_fee

    def test_difference_is_transfer_fee(self):
        """买卖费用差应恰好等于过户费"""
        price = Decimal("100000")
        tax_rate = Decimal("0.0003")
        long_fee = cal_fee(DIRECTION_TYPES.LONG, price, tax_rate)
        short_fee = cal_fee(DIRECTION_TYPES.SHORT, price, tax_rate)
        transfer_fee = price * Decimal("0.00002")
        assert short_fee - long_fee == transfer_fee


# ---------------------------------------------------------------------------
# 边界条件
# ---------------------------------------------------------------------------
@pytest.mark.unit
class TestCalFeeEdgeCases:
    """边界条件测试"""

    def test_very_small_price(self):
        """极小价格"""
        result = cal_fee(DIRECTION_TYPES.LONG, 1, 0.0003)
        # 佣金 = 1 * 0.0003 = 0.0003 → 5
        # 印花税 = 1 * 0.001 = 0.001
        assert result == Decimal("5.001")

    def test_negative_price(self):
        """负价格（非法但测试函数行为）"""
        # 佣金 = -100 * 0.0003 = -0.03 → -0.03 < 5, 所以 fee = 5
        # 印花税 = -100 * 0.001 = -0.1
        result = cal_fee(DIRECTION_TYPES.LONG, -100, 0.0003)
        assert result == Decimal("4.9")
