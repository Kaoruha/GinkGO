import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.underwater_time import UnderwaterTime
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestUnderwaterTime(unittest.TestCase):
    """
    测试水下时间分析器
    """

    def setUp(self):
        """初始化测试用的UnderwaterTime实例"""
        self.analyzer = UnderwaterTime("test_underwater_time")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.advance_time(self.test_time)
        from datetime import datetime as dt
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(dt(2024, 1, 1, 9, 30, 0))
        self.analyzer.set_analyzer_id("test_underwater_time_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试UnderwaterTime初始化"""
        analyzer = UnderwaterTime()

        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "underwater_time")
        self.assertIsNone(analyzer._max_worth)
        self.assertEqual(analyzer._underwater_days, 0)
        self.assertEqual(analyzer._max_underwater_days, 0)
        self.assertEqual(analyzer._total_underwater_days, 0)
        self.assertEqual(analyzer._underwater_periods, 0)

        # 检查激活阶段配置 - 使用NEWDAY
        self.assertIn(RECORDSTAGE_TYPES.NEWDAY, analyzer.active_stage)

        # 检查记录阶段配置 - 使用NEWDAY
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.NEWDAY)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}

        # 第一天，设置max_worth值，不应该有水下时间
        self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 0)
        self.assertEqual(self.analyzer._max_worth, 10000)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_no_drawdown_scenario(self):
        """测试无回撤场景（持续上涨）"""
        base_worth = 10000

        # 10天持续上涨
        for i in range(10):
            worth = base_worth * (1 + 0.01 * (i + 1))  # 累计收益
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 无回撤，应该没有水下时间
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 0)
        self.assertEqual(self.analyzer.total_underwater_days, 0)
        self.assertEqual(self.analyzer.underwater_periods_count, 0)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_simple_drawdown_scenario(self):
        """测试简单回撤场景"""
        worth_sequence = [10000, 11000, 12000, 11000, 10500, 11500, 13000]  # 回撤后恢复

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 从12000回撤到10500，然后恢复到创新高
        # Day0: 10000 -> max_worth=10000, underwater=0
        # Day1: 11000 > 10000 -> new high, underwater=0
        # Day2: 12000 > 11000 -> new high, underwater=0
        # Day3: 11000 < 12000 -> underwater=1
        # Day4: 10500 < 12000 -> underwater=2
        # Day5: 11500 < 12000 -> underwater=3
        # Day6: 13000 > 12000 -> new high, period ends. max_underwater=3, total=3
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 3)
        self.assertEqual(self.analyzer.total_underwater_days, 3)
        self.assertEqual(self.analyzer.underwater_periods_count, 1)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_extended_drawdown_scenario(self):
        """测试长期回撤场景"""
        worth_sequence = [10000, 12000, 11000, 10000, 9500, 9000, 8500, 9000, 8800, 10500, 12500]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 从12000回撤，经历长期水下时间，最终恢复并创新高12500
        # Day0: 10000 -> max=10000
        # Day1: 12000 > 10000 -> new high, max=12000
        # Day2-9: all < 12000, underwater 1-8 days
        # Day10: 12500 > 12000 -> new high, period ends. underwater was 8 days
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 8)
        self.assertEqual(self.analyzer.total_underwater_days, 8)
        self.assertEqual(self.analyzer.underwater_periods_count, 1)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_multiple_drawdown_periods(self):
        """测试多个回撤周期"""
        worth_sequence = [10000, 11000, 10500, 11500, 12000, 11000, 10000, 11000, 13000, 12000, 11500, 13500]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 应该有三个回撤周期：
        # Period1: Day2 (10500<11000) underwater=1, Day3: 11500>11000 new high, period=1
        # Period2: Day5 (11000<12000), Day6 (10000<12000) underwater=2, Day7: 11000<12000 underwater=3, Day8: 13000>12000 new high, period done. max=3
        # Period3: Day9 (12000<13000), Day10 (11500<13000), Day11: 13500>13000 new high, period done. max=2
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 3)
        self.assertEqual(self.analyzer.underwater_periods_count, 3)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_current_underwater_scenario(self):
        """测试当前仍在水下的场景"""
        worth_sequence = [10000, 12000, 11000, 10000, 9500, 9000, 8500, 9000, 8800, 9200]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 最后仍在水下（9200 < 12000）
        # Day0: max=10000
        # Day1: 12000 > 10000 -> max=12000
        # Day2-9: all < 12000, underwater 1-8 days
        # total_underwater_days property = _total_underwater_days + _underwater_days
        # After 8 underwater days: _total=8, _underwater=8 -> total=16
        self.assertGreater(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, self.analyzer.current_underwater_days)
        self.assertEqual(self.analyzer.total_underwater_days, 16)  # 8 accumulated + 8 current
        self.assertEqual(self.analyzer.underwater_periods_count, 1)
        self.assertTrue(self.analyzer.is_currently_underwater)

    def test_properties(self):
        """测试各种属性"""
        worth_sequence = [10000, 11000, 10500, 11500, 10000, 9500, 11000, 12000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 测试当前水下天数
        underwater_days = self.analyzer.current_underwater_days
        self.assertIsInstance(underwater_days, int)
        self.assertGreaterEqual(underwater_days, 0)

        # 测试最大水下天数
        max_underwater = self.analyzer.max_underwater_days
        self.assertIsInstance(max_underwater, int)
        self.assertGreaterEqual(max_underwater, 0)

        # 测试总水下天数
        total_underwater = self.analyzer.total_underwater_days
        self.assertIsInstance(total_underwater, int)
        self.assertGreaterEqual(total_underwater, 0)

        # 测试水下周期数
        periods = self.analyzer.underwater_periods_count
        self.assertIsInstance(periods, int)
        self.assertGreaterEqual(periods, 0)

        # 测试是否在水下
        is_underwater = self.analyzer.is_currently_underwater
        self.assertIsInstance(is_underwater, bool)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        # 先设置正常值
        portfolio_info = {"worth": 10000}
        self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 然后设置零值
        portfolio_info = {"worth": 0}
        day_time = self.test_time + timedelta(days=1)
        self.analyzer.advance_time(day_time)
        self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 零值应该被视为水下
        self.assertTrue(self.analyzer.is_currently_underwater)
        self.assertEqual(self.analyzer.current_underwater_days, 1)

    def test_recording_functionality(self):
        """测试记录功能"""
        worth_sequence = [10000, 11000, 10500, 11500, 10000, 9500, 11000, 12000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

            # 测试记录功能
            self.analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 确保有数据记录
        self.assertGreater(len(self.analyzer.data), 0)

    def test_single_day_scenario(self):
        """测试单日场景"""
        portfolio_info = {"worth": 10000}

        self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 单日无回撤
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 0)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_peak_worth_tracking(self):
        """测试峰值跟踪"""
        worth_sequence = [10000, 15000, 12000, 18000, 14000, 20000, 16000]

        expected_peaks = [10000, 15000, 15000, 18000, 18000, 20000, 20000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

            # 检查峰值是否正确更新
            self.assertEqual(self.analyzer._max_worth, expected_peaks[i])

    def test_underwater_period_counting(self):
        """测试水下周期计数"""
        # 创建三个独立的回撤周期
        worth_sequence = [10000, 12000, 11000, 13000, 12000, 14000, 13000, 15000, 14000, 16000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # Period1: Day2 (11000<12000) uw=1, Day3: 13000>12000 new high
        # Period2: Day4 (12000<13000) uw=1, Day5: 14000>13000 new high
        # Period3: Day6 (13000<14000) uw=1, Day7: 15000>14000 new high
        # Period4: Day8 (14000<15000) uw=1, Day9: 16000>15000 new high
        self.assertEqual(self.analyzer.underwater_periods_count, 4)
        self.assertEqual(self.analyzer.total_underwater_days, 4)
        self.assertEqual(self.analyzer.max_underwater_days, 1)

    def test_long_recovery_scenario(self):
        """测试长期恢复场景"""
        worth_sequence = [10000, 15000, 12000, 11000, 10000, 9000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # Day0: max=10000
        # Day1: 15000>10000 -> max=15000
        # Day2-13: all < 15000, underwater days 1-12
        # Day14: 16000 > 15000 -> new high, period ends. max_underwater=12
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 12)
        self.assertEqual(self.analyzer.total_underwater_days, 12)
        self.assertEqual(self.analyzer.underwater_periods_count, 1)
        self.assertFalse(self.analyzer.is_currently_underwater)

    def test_exact_peak_recovery(self):
        """测试精确峰值恢复 - 使用 > 比较，等于不触发"""
        worth_sequence = [10000, 12000, 11000, 10000, 9000, 10000, 11000, 12000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 源码使用严格大于(>)比较：current_worth > _max_worth
        # Day0: _max_worth=10000
        # Day1: 12000 > 10000 -> new high, _max_worth=12000, underwater=0
        # Day2: 11000 < 12000 -> underwater=1
        # Day3: 10000 < 12000 -> underwater=2
        # Day4: 9000 < 12000 -> underwater=3
        # Day5: 10000 < 12000 -> underwater=4
        # Day6: 11000 < 12000 -> underwater=5
        # Day7: 12000 == 12000, NOT > 12000 -> underwater=6 (still underwater!)
        self.assertEqual(self.analyzer.current_underwater_days, 6)
        self.assertTrue(self.analyzer.is_currently_underwater)

    def test_immediate_new_high(self):
        """测试立即创新高"""
        worth_sequence = [10000, 12000, 11000, 15000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # Day0: max=10000
        # Day1: 12000>10000 -> max=12000
        # Day2: 11000<12000 -> underwater=1
        # Day3: 15000>12000 -> new high, period ends. max_underwater=1
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 1)
        self.assertEqual(self.analyzer.total_underwater_days, 1)
        self.assertFalse(self.analyzer.is_currently_underwater)


if __name__ == '__main__':
    unittest.main()
