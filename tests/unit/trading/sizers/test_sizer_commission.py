"""
Sizer 佣金费率修复单元测试 (#5493)

FixedSizer / RatioSizer 原硬编码 Decimal("1.003")（0.3% 佣金估计），
与 SimBroker 实际费率 max(成交额×0.0003, 5) 不符。验证改为可配置的
真实 broker 费率计算。

Related: #5493
"""

import sys
_path = "/home/kaoru/Ginkgo/src"
if _path not in sys.path:
    sys.path.insert(0, _path)

from decimal import Decimal

from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.sizers.ratio_sizer import RatioSizer


class TestFixedSizerCommission:
    """#5493: FixedSizer 佣金计算"""

    def test_small_order_uses_commission_min(self):
        """小单（成交额×费率 < min 5）佣金按 min 5 计，非 0.3% 估计"""
        s = FixedSizer(volume="100")
        # 100 股 @ 10 = 成交额 1000; 0.0003×1000=0.3 < min 5 → 佣金 5
        # 旧: 100×10×1.003 = 1003; 新: 1000 + 5 = 1005
        size, cost = s.calculate_order_size(100, Decimal("10"), Decimal("100000"))
        assert size == 100
        assert cost == Decimal("1005")

    def test_large_order_uses_commission_rate(self):
        """大单按 commission_rate 计（0.0003），远低于旧 0.3% 估计"""
        s = FixedSizer(volume="1000")
        # 1000 @ 100 = 100000; 0.0003×100000=30 > min 5 → 佣金 30
        # 旧: 1000×100×1.003 = 100300; 新: 100000 + 30 = 100030
        size, cost = s.calculate_order_size(1000, Decimal("100"), Decimal("1000000"))
        assert size == 1000
        assert cost == Decimal("100030")

    def test_defaults_match_simbroker(self):
        """默认费率对齐 SimBroker（commission_rate=0.0003, min=5, stamp=0.001）"""
        s = FixedSizer()
        assert s._commission_rate == Decimal("0.0003")
        assert s._commission_min == Decimal("5")
        assert s._stamp_tax == Decimal("0.001")

    def test_custom_commission_params(self):
        """自定义费率参数生效"""
        s = FixedSizer(commission_rate=0.001, commission_min=1)
        # 100 @ 10 = 1000; 0.001×1000=1 >= min 1 → 佣金 1; 成本 1001
        size, cost = s.calculate_order_size(100, Decimal("10"), Decimal("100000"))
        assert size == 100
        assert cost == Decimal("1001")

    def test_reduces_size_when_cash_insufficient(self):
        """资金不足时按 100 股递减至可负担"""
        s = FixedSizer(volume="300")
        # 300 @ 10 = 3000+5=3005 > cash 2005 → 递减；200 @ 10 = 2000+5=2005 == cash
        size, cost = s.calculate_order_size(300, Decimal("10"), Decimal("2005"))
        assert size == 200
        assert cost == Decimal("2005")


class TestRatioSizerCommission:
    """#5493: RatioSizer 佣金计算"""

    def test_small_order_uses_commission_min(self):
        """小单佣金按 min 5 计"""
        s = RatioSizer(ratio="1.0")
        # budget=1005; 100 @ 10 = 1000+5=1005
        size, cost = s.calculate_order_size(1.0, Decimal("10"), Decimal("1005"))
        assert size == 100
        assert cost == Decimal("1005")

    def test_large_order_uses_commission_rate(self):
        """大单按 commission_rate 计"""
        s = RatioSizer(ratio="1.0")
        # budget=100030; 1000 @ 100 = 100000+30=100030
        size, cost = s.calculate_order_size(1.0, Decimal("100"), Decimal("100030"))
        assert size == 1000
        assert cost == Decimal("100030")

    def test_defaults_match_simbroker(self):
        """默认费率对齐 SimBroker"""
        s = RatioSizer()
        assert s._commission_rate == Decimal("0.0003")
        assert s._commission_min == Decimal("5")
        assert s._stamp_tax == Decimal("0.001")
