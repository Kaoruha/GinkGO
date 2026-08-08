"""
角色: Profit 分析器 characterization test（#6475：日度盈亏 = 当日 worth - 前日 worth）。
覆盖：首次归零、逐日盈/亏/平、Decimal worth 原生口径（get_worth 保留原生 + worth_delta float 化）、
      worth 缺失归零。refactor 前后均应绿（行为等价锚点）。
注：BaseAnalyzer.data 是 DataFrame（columns=['timestamp','value']），取值经 data["value"]。
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.profit import Profit
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestProfit(unittest.TestCase):
    """测试利润分析器（日度盈亏序列）"""

    def setUp(self):
        self.analyzer = Profit("test_profit")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_profit_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def _values(self, worths):
        """喂入 worth 序列（每日 ENDDAY activate），返回 value 列（float 化）。"""
        for i, w in enumerate(worths):
            self.analyzer.advance_time(self.test_time + timedelta(days=i))
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": w})
        return [float(v) for v in self.analyzer.data["value"]]

    def test_init(self):
        """初始化：默认 name、激活 NEWDAY+ENDDAY、record ENDDAY、_last_worth=None"""
        a = Profit()
        self.assertEqual(a._name, "ProfitAna")
        self.assertIn(RECORDSTAGE_TYPES.NEWDAY, a.active_stage)
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, a.active_stage)
        self.assertEqual(a.record_stage, RECORDSTAGE_TYPES.ENDDAY)
        self.assertIsNone(a._last_worth)

    def test_first_call_zero(self):
        """首次无前日，盈亏为 0"""
        self.assertEqual(self._values([10000]), [0.0])

    def test_daily_profit(self):
        """逐日等额盈利：+100, +100"""
        self.assertEqual(self._values([10000, 10100, 10200]), [0.0, 100.0, 100.0])

    def test_daily_loss(self):
        """逐日等额亏损：-100, -100"""
        self.assertEqual(self._values([10000, 9900, 9800]), [0.0, -100.0, -100.0])

    def test_mixed_pnl(self):
        """盈亏交替：+100, -50"""
        self.assertEqual(self._values([10000, 10100, 10050]), [0.0, 100.0, -50.0])

    def test_no_change(self):
        """worth 不变：盈亏 0"""
        self.assertEqual(self._values([10000, 10000]), [0.0, 0.0])

    def test_decimal_worth_native(self):
        """worth 为 Decimal 原生：口径统一后仍正确（#6475 核心）。
        get_worth 保留 Decimal，worth_delta 内部 float 化，结果与 int/float 一致。"""
        data = self._values([Decimal("10000"), Decimal("10100"), Decimal("10050")])
        self.assertEqual(data, [0.0, 100.0, -50.0])

    def test_float_worth_native(self):
        """worth 为 float：与 Decimal/int 等价"""
        data = self._values([10000.0, 10100.5, 10050.25])
        self.assertEqual(len(data), 3)
        self.assertAlmostEqual(data[0], 0.0, places=2)
        self.assertAlmostEqual(data[1], 100.5, places=2)
        self.assertAlmostEqual(data[2], -50.25, places=2)

    def test_missing_worth_treated_as_zero(self):
        """worth 缺失：get_worth 返回 0，盈亏 = 0 - 前日"""
        self.analyzer.advance_time(self.test_time)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        self.analyzer.advance_time(self.test_time + timedelta(days=1))
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {})
        last = float(self.analyzer.data["value"].iloc[-1])
        self.assertAlmostEqual(last, -10000.0, places=2)


if __name__ == '__main__':
    unittest.main()
