"""
性能: 272MB RSS, 2.28s, 24 tests [PASS]
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.win_rate import WinRate
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestWinRate(unittest.TestCase):
    """
    测试胜率分析器
    """

    def setUp(self):
        """初始化测试用的WinRate实例"""
        self.analyzer = WinRate("test_win_rate")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_win_rate_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def _init_and_advance(self, analyzer, day_index):
        """Advance time to a specific day."""
        day_time = self.test_time + timedelta(days=day_index)
        analyzer.advance_time(day_time)

    def test_init(self):
        """测试WinRate初始化"""
        analyzer = WinRate()

        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "win_rate")
        self.assertEqual(analyzer.win_count, 0)
        self.assertEqual(analyzer.loss_count, 0)
        self.assertEqual(analyzer._total_profit, 0.0)
        self.assertEqual(analyzer._total_loss, 0.0)

        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)

        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}

        # 第一天，没有交易，胜率应为0
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_win_rate, 0.0)
        self.assertEqual(self.analyzer.profit_loss_ratio, 0.0)

    def test_winning_trades_scenario(self):
        """测试盈利交易场景"""
        base_worth = 10000
        daily_changes = [100, 50, 200, 75, 150]  # 全部盈利

        current_worth = base_worth
        # Day 0: init
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 全部盈利，胜率应为100%
        self.assertEqual(self.analyzer.current_win_rate, 1.0)
        self.assertEqual(self.analyzer.win_count, 5)
        self.assertEqual(self.analyzer.total_trades, 5)
        self.assertGreater(self.analyzer._total_profit, 0)
        self.assertEqual(self.analyzer._total_loss, 0.0)

    def test_losing_trades_scenario(self):
        """测试亏损交易场景"""
        base_worth = 10000
        daily_changes = [-100, -50, -200, -75, -150]  # 全部亏损

        current_worth = base_worth
        # Day 0: init
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 全部亏损，胜率应为0%
        self.assertEqual(self.analyzer.current_win_rate, 0.0)
        self.assertEqual(self.analyzer.win_count, 0)
        self.assertEqual(self.analyzer.total_trades, 5)
        self.assertEqual(self.analyzer._total_profit, 0.0)
        self.assertGreater(self.analyzer._total_loss, 0)

    def test_mixed_trades_scenario(self):
        """测试混合交易场景"""
        base_worth = 10000
        daily_changes = [100, -50, 200, -75, 150, -100, 80, -30]  # 5盈3亏

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 4盈4亏，胜率应为50%
        self.assertAlmostEqual(self.analyzer.current_win_rate, 0.5, places=3)
        self.assertEqual(self.analyzer.win_count, 4)
        self.assertEqual(self.analyzer.total_trades, 8)
        self.assertGreater(self.analyzer._total_profit, 0)
        self.assertGreater(self.analyzer._total_loss, 0)

    def test_profit_loss_ratio_calculation(self):
        """测试盈亏比计算"""
        base_worth = 10000
        daily_changes = [200, -100, 150, -50, 100, -75]  # 平均盈利150，平均亏损75

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 平均盈利 = (200+150+100)/3 = 150
        # 平均亏损 = (100+50+75)/3 = 75
        # 盈亏比 = 150/75 = 2.0
        self.assertAlmostEqual(self.analyzer.profit_loss_ratio, 2.0, places=1)

    def test_zero_change_days_ignored(self):
        """测试零变化日被忽略"""
        base_worth = 10000
        daily_changes = [100, 0, -50, 0, 200, 0, -75]  # 包含零变化

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 应该只计算非零变化的交易：2盈2亏
        self.assertEqual(self.analyzer.total_trades, 4)
        self.assertEqual(self.analyzer.win_count, 2)
        self.assertEqual(self.analyzer.current_win_rate, 0.5)

    def test_properties(self):
        """测试各种属性"""
        base_worth = 10000
        daily_changes = [100, -50, 200, -75, 150]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 测试当前胜率
        win_rate = self.analyzer.current_win_rate
        self.assertIsInstance(win_rate, float)
        self.assertGreaterEqual(win_rate, 0.0)
        self.assertLessEqual(win_rate, 1.0)

        # 测试盈亏比
        pl_ratio = self.analyzer.profit_loss_ratio
        self.assertIsInstance(pl_ratio, float)
        self.assertGreaterEqual(pl_ratio, 0.0)

        # 测试总交易数
        total_trades = self.analyzer.total_trades
        self.assertIsInstance(total_trades, int)
        self.assertGreaterEqual(total_trades, 0)

        # 测试盈利交易数
        winning_trades = self.analyzer.win_count
        self.assertIsInstance(winning_trades, int)
        self.assertGreaterEqual(winning_trades, 0)
        self.assertLessEqual(winning_trades, total_trades)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        portfolio_info = {"worth": 0}

        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_win_rate, 0.0)
        self.assertEqual(self.analyzer.profit_loss_ratio, 0.0)

    def test_recording_functionality(self):
        """测试记录功能"""
        base_worth = 10000
        daily_changes = [100, -50, 200, -75, 150]

        current_worth = base_worth
        for i, change in enumerate(daily_changes):
            if i == 0:
                self._init_and_advance(self.analyzer, 0)
            else:
                self._init_and_advance(self.analyzer, i)
            current_worth += change
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})
            self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 确保有数据记录
        self.assertGreater(len(self.analyzer.data), 0)

    def test_single_day_scenario(self):
        """测试单日场景"""
        portfolio_info = {"worth": 10000}

        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 单日无法计算胜率（没有前一天数据）
        self.assertEqual(self.analyzer.current_win_rate, 0.0)
        self.assertEqual(self.analyzer.total_trades, 0)

    def test_consecutive_wins_and_losses(self):
        """测试连续盈亏"""
        base_worth = 10000
        daily_changes = [100, 150, 200, -50, -75, -100, 80, 120]  # 3连胜，3连败，2连胜

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 5盈3亏，胜率62.5%
        self.assertAlmostEqual(self.analyzer.current_win_rate, 0.625, places=3)
        self.assertEqual(self.analyzer.win_count, 5)
        self.assertEqual(self.analyzer.total_trades, 8)

    def test_large_profit_small_loss_scenario(self):
        """测试大盈利小亏损场景"""
        base_worth = 10000
        daily_changes = [500, -10, 600, -15, 400, -20]  # 大盈利，小亏损

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 胜率50%，但盈亏比很高
        self.assertEqual(self.analyzer.current_win_rate, 0.5)
        self.assertGreater(self.analyzer.profit_loss_ratio, 20)  # 平均盈利500，平均亏损15

    def test_small_profit_large_loss_scenario(self):
        """测试小盈利大亏损场景"""
        base_worth = 10000
        daily_changes = [10, -500, 15, -600, 20, -400]  # 小盈利，大亏损

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 胜率50%，但盈亏比很低
        self.assertEqual(self.analyzer.current_win_rate, 0.5)
        self.assertLess(self.analyzer.profit_loss_ratio, 0.1)  # 平均盈利15，平均亏损500

    def test_no_losses_profit_loss_ratio(self):
        """测试无亏损时的盈亏比"""
        base_worth = 10000
        daily_changes = [100, 150, 200, 75, 125]  # 全部盈利

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 无亏损时，盈亏比应为0（实现中loss_count==0时返回0）
        self.assertEqual(self.analyzer.current_win_rate, 1.0)
        self.assertEqual(self.analyzer.profit_loss_ratio, 0.0)

    def test_no_profits_profit_loss_ratio(self):
        """测试无盈利时的盈亏比"""
        base_worth = 10000
        daily_changes = [-100, -150, -200, -75, -125]  # 全部亏损

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 无盈利时，盈亏比应为0（实现中win_count==0时返回0）
        self.assertEqual(self.analyzer.current_win_rate, 0.0)
        self.assertEqual(self.analyzer.profit_loss_ratio, 0.0)

    def test_very_small_changes(self):
        """测试非常小的变化"""
        base_worth = 10000
        daily_changes = [0.01, -0.005, 0.02, -0.01, 0.015]  # 非常小的变化

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 应该正确处理小数值: 3 wins, 2 losses
        self.assertEqual(self.analyzer.total_trades, 5)
        self.assertEqual(self.analyzer.win_count, 3)
        self.assertEqual(self.analyzer.current_win_rate, 0.6)


class TestWinRateNumericalCorrectness(unittest.TestCase):
    """数值正确性验证 - 使用已知数据验证胜率和盈亏比"""

    def setUp(self):
        self.analyzer = WinRate("test_win_rate_num")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_win_rate_num_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def _init_and_advance(self, analyzer, day_index):
        day_time = self.test_time + timedelta(days=day_index)
        analyzer.advance_time(day_time)

    def test_exact_win_rate_3_of_5(self):
        """验证精确胜率: 3胜2败 = 60%"""
        base_worth = 10000
        daily_changes = [100, -50, 200, -75, 150]  # 3胜2败

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertAlmostEqual(self.analyzer.current_win_rate, 0.6, places=5)
        self.assertEqual(self.analyzer.win_count, 3)
        self.assertEqual(self.analyzer.loss_count, 2)
        self.assertEqual(self.analyzer.total_trades, 5)

    def test_exact_profit_loss_ratio(self):
        """验证精确盈亏比"""
        base_worth = 10000
        # 2胜: +300, +150; 2败: -100, -200
        # avg_profit = (300+150)/2 = 225
        # avg_loss = (100+200)/2 = 150
        # pl_ratio = 225/150 = 1.5
        daily_changes = [300, -100, 150, -200]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertAlmostEqual(self.analyzer.profit_loss_ratio, 1.5, places=5)

    def test_zero_win_rate(self):
        """验证0%胜率"""
        base_worth = 10000
        daily_changes = [-100, -50, -200]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertEqual(self.analyzer.current_win_rate, 0.0)
        self.assertEqual(self.analyzer.win_count, 0)
        self.assertEqual(self.analyzer.total_trades, 3)

    def test_100_percent_win_rate(self):
        """验证100%胜率"""
        base_worth = 10000
        daily_changes = [100, 200, 150]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertEqual(self.analyzer.current_win_rate, 1.0)
        self.assertEqual(self.analyzer.loss_count, 0)
        self.assertEqual(self.analyzer.total_trades, 3)


class TestWinRateBoundaryConditions(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def _init_and_advance(self, analyzer, day_index):
        day_time = self.test_time + timedelta(days=day_index)
        analyzer.advance_time(day_time)

    def test_empty_data(self):
        """从未调用activate，验证默认值"""
        analyzer = WinRate("test_win_empty")
        self.assertEqual(analyzer.current_win_rate, 0.0)
        self.assertEqual(analyzer.win_count, 0)
        self.assertEqual(analyzer.loss_count, 0)
        self.assertEqual(analyzer.total_trades, 0)
        self.assertEqual(analyzer.profit_loss_ratio, 0.0)

    def test_single_bar(self):
        """只传1条bar数据"""
        analyzer = WinRate("test_win_single")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_single_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        self.assertEqual(analyzer.current_win_rate, 0.0)
        self.assertEqual(analyzer.total_trades, 0)

    def test_all_zero_values(self):
        """所有bar的worth=0"""
        analyzer = WinRate("test_win_zeros")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_zeros_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        # Day0: init
        self._init_and_advance(analyzer, 0)
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})

        # Day1: worth=0, _last_worth=0, 0 > 0不满足，win_rate=0.0
        self._init_and_advance(analyzer, 1)
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})

        self.assertEqual(analyzer.current_win_rate, 0.0)
        self.assertEqual(analyzer.total_trades, 0)


if __name__ == '__main__':
    unittest.main()
