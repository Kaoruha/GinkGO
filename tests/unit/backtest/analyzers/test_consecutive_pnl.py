"""
性能: 271MB RSS, 2.36s, 25 tests [PASS]
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.consecutive_pnl import ConsecutivePnL
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestConsecutivePnL(unittest.TestCase):
    """
    测试连续盈亏分析器
    """

    def setUp(self):
        """初始化测试用的ConsecutivePnL实例"""
        self.analyzer = ConsecutivePnL("test_consecutive_pnl")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_consecutive_pnl_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def _init_and_advance(self, analyzer, day_index):
        """Advance time to a specific day."""
        day_time = self.test_time + timedelta(days=day_index)
        analyzer.advance_time(day_time)

    def test_init(self):
        """测试ConsecutivePnL初始化"""
        analyzer = ConsecutivePnL()

        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "consecutive_pnl")
        self.assertIsNone(analyzer._current_streak_type)
        self.assertEqual(analyzer._max_win_streak, 0)
        self.assertEqual(analyzer._max_loss_streak, 0)
        self.assertEqual(analyzer._current_win_streak, 0)
        self.assertEqual(analyzer._current_loss_streak, 0)

        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)

        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}

        # 第一天，没有历史数据，连续数应为0
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.max_consecutive_wins, 0)
        self.assertEqual(self.analyzer.max_consecutive_losses, 0)
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_consecutive_wins_scenario(self):
        """测试连续盈利场景"""
        base_worth = 10000
        daily_changes = [100, 150, 200, 75, 125]  # 5连胜

        current_worth = base_worth
        # Day 0: init
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 5连胜（days 1-5, each day change > 0）
        self.assertEqual(self.analyzer.max_consecutive_wins, 5)
        self.assertEqual(self.analyzer.current_consecutive_wins, 5)
        self.assertEqual(self.analyzer.max_consecutive_losses, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_consecutive_losses_scenario(self):
        """测试连续亏损场景"""
        base_worth = 10000
        daily_changes = [-100, -150, -200, -75, -125]  # 5连败

        current_worth = base_worth
        # Day 0: init
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 5连败
        self.assertEqual(self.analyzer.max_consecutive_losses, 5)
        self.assertEqual(self.analyzer.current_consecutive_losses, 5)
        self.assertEqual(self.analyzer.max_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)

    def test_mixed_scenario_with_streaks(self):
        """测试混合场景包含连胜连败"""
        base_worth = 10000
        daily_changes = [100, 150, 200, -50, -75, -100, 80, 120, 90, -30]  # 3胜3败2胜1败

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 最大连胜应该是3，最大连败应该是3
        self.assertEqual(self.analyzer.max_consecutive_wins, 3)
        self.assertEqual(self.analyzer.max_consecutive_losses, 3)
        # 当前应该是1连败
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 1)

    def test_alternating_scenario(self):
        """测试交替盈亏场景"""
        base_worth = 10000
        daily_changes = [100, -50, 150, -75, 200, -100, 80, -40]  # 交替盈亏

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 最大连胜和连败都应该是1
        self.assertEqual(self.analyzer.max_consecutive_wins, 1)
        self.assertEqual(self.analyzer.max_consecutive_losses, 1)
        # 当前应该是1连败
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 1)

    def test_zero_change_ignored(self):
        """测试零变化被忽略"""
        base_worth = 10000
        daily_changes = [100, 0, 150, 0, -50, 0, -75]  # 包含零变化

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 零变化应该被忽略，连胜2，连败2
        self.assertEqual(self.analyzer.max_consecutive_wins, 2)
        self.assertEqual(self.analyzer.max_consecutive_losses, 2)
        # 当前应该是2连败
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 2)

    def test_long_winning_streak(self):
        """测试长连胜"""
        base_worth = 10000
        daily_changes = [100] * 10 + [-50] + [50] * 5  # 10连胜，1败，5连胜

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 最大连胜应该是10
        self.assertEqual(self.analyzer.max_consecutive_wins, 10)
        self.assertEqual(self.analyzer.max_consecutive_losses, 1)
        # 当前应该是5连胜
        self.assertEqual(self.analyzer.current_consecutive_wins, 5)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_long_losing_streak(self):
        """测试长连败"""
        base_worth = 10000
        daily_changes = [-50] * 8 + [100] + [-25] * 3  # 8连败，1胜，3连败

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 最大连败应该是8
        self.assertEqual(self.analyzer.max_consecutive_losses, 8)
        self.assertEqual(self.analyzer.max_consecutive_wins, 1)
        # 当前应该是3连败
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 3)

    def test_properties(self):
        """测试各种属性"""
        base_worth = 10000
        daily_changes = [100, 150, -50, -75, 200, 80, -30]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 测试最大连胜
        max_wins = self.analyzer.max_consecutive_wins
        self.assertIsInstance(max_wins, int)
        self.assertGreaterEqual(max_wins, 0)

        # 测试最大连败
        max_losses = self.analyzer.max_consecutive_losses
        self.assertIsInstance(max_losses, int)
        self.assertGreaterEqual(max_losses, 0)

        # 测试当前连胜
        current_wins = self.analyzer.current_consecutive_wins
        self.assertIsInstance(current_wins, int)
        self.assertGreaterEqual(current_wins, 0)

        # 测试当前连败
        current_losses = self.analyzer.current_consecutive_losses
        self.assertIsInstance(current_losses, int)
        self.assertGreaterEqual(current_losses, 0)

        # 当前连胜和连败不能同时大于0
        self.assertTrue(current_wins == 0 or current_losses == 0)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        # 先设置正常值
        portfolio_info = {"worth": 10000}
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 然后设置零值（应该视为亏损）
        portfolio_info = {"worth": 0}
        self._init_and_advance(self.analyzer, 1)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 零值应该被视为亏损
        self.assertEqual(self.analyzer.current_consecutive_losses, 1)
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)

    def test_recording_functionality(self):
        """测试记录功能"""
        base_worth = 10000
        daily_changes = [100, 150, -50, -75, 200]

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

        # 单日无法计算连续盈亏（没有前一天数据）
        self.assertEqual(self.analyzer.max_consecutive_wins, 0)
        self.assertEqual(self.analyzer.max_consecutive_losses, 0)
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_streak_reset_after_opposite_result(self):
        """测试连胜连败在相反结果后重置"""
        base_worth = 10000
        daily_changes = [100, 150, 200, -50, 80, 120]  # 3胜1败2胜

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        max_wins_during_process = []
        current_wins_during_process = []

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

            max_wins_during_process.append(self.analyzer.max_consecutive_wins)
            current_wins_during_process.append(self.analyzer.current_consecutive_wins)

        # Day1: win, current=1, _max=0 -> max(0,1)=1
        # Day2: win, current=2, _max=0 -> max(0,2)=2
        # Day3: win, current=3, _max=0 -> max(0,3)=3
        # Day4: loss, ends win streak, _max=3, current=0 -> max(3,0)=3
        # Day5: win, current=1, _max=3 -> max(3,1)=3
        # Day6: win, current=2, _max=3 -> max(3,2)=3
        self.assertEqual(max_wins_during_process, [1, 2, 3, 3, 3, 3])
        self.assertEqual(current_wins_during_process, [1, 2, 3, 0, 1, 2])

    def test_very_small_changes(self):
        """测试非常小的变化"""
        base_worth = 10000
        daily_changes = [0.01, 0.02, -0.005, -0.01, 0.015]  # 非常小的变化

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 应该正确处理小数值: 2 wins, 2 losses, 1 win
        self.assertEqual(self.analyzer.max_consecutive_wins, 2)
        self.assertEqual(self.analyzer.max_consecutive_losses, 2)
        self.assertEqual(self.analyzer.current_consecutive_wins, 1)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_streak_type_tracking(self):
        """测试连胜连败类型跟踪"""
        base_worth = 10000
        daily_changes = [100, 150, -50, -75]  # 2胜2败

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        streak_types = []

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})
            streak_types.append(self.analyzer._current_streak_type)

        # 验证连胜连败类型的变化
        self.assertEqual(streak_types, ["win", "win", "loss", "loss"])

    def test_recovery_after_long_losing_streak(self):
        """测试长连败后的恢复"""
        base_worth = 10000
        daily_changes = [-50] * 15 + [100] * 8  # 15连败，8连胜

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 应该正确记录最大连败和当前连胜
        self.assertEqual(self.analyzer.max_consecutive_losses, 15)
        self.assertEqual(self.analyzer.max_consecutive_wins, 8)
        self.assertEqual(self.analyzer.current_consecutive_wins, 8)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_multiple_equal_streaks(self):
        """测试多个相等长度的连胜连败"""
        base_worth = 10000
        daily_changes = [100] * 5 + [-50] * 3 + [80] * 5 + [-40] * 3  # 5胜3败5胜3败

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 最大连胜和连败应该正确记录
        self.assertEqual(self.analyzer.max_consecutive_wins, 5)
        self.assertEqual(self.analyzer.max_consecutive_losses, 3)
        self.assertEqual(self.analyzer.current_consecutive_wins, 0)
        self.assertEqual(self.analyzer.current_consecutive_losses, 3)


class TestConsecutivePnLNumericalCorrectness(unittest.TestCase):
    """数值正确性验证 - 使用已知数据验证计算结果"""

    def setUp(self):
        self.analyzer = ConsecutivePnL("test_consecutive_num")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_consecutive_num_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def _init_and_advance(self, analyzer, day_index):
        day_time = self.test_time + timedelta(days=day_index)
        analyzer.advance_time(day_time)

    def test_known_streak_exact_values(self):
        """验证连续盈亏的精确天数"""
        base_worth = 10000
        # 2胜3败1胜
        daily_changes = [100, 200, -50, -100, -150, 80]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertEqual(self.analyzer.max_consecutive_wins, 2)
        self.assertEqual(self.analyzer.max_consecutive_losses, 3)
        self.assertEqual(self.analyzer.current_consecutive_wins, 1)
        self.assertEqual(self.analyzer.current_consecutive_losses, 0)

    def test_known_max_win_amount(self):
        """验证最大连续盈利金额"""
        base_worth = 10000
        # 第一段连胜: +100+200=300, 第二段连胜: +50=50
        daily_changes = [100, 200, -100, 50]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertAlmostEqual(self.analyzer.max_win_amount, 300.0, places=2)

    def test_known_max_loss_amount(self):
        """验证最大连续亏损金额"""
        base_worth = 10000
        # 第一段连败: 50+100=150, 第二段连败: 20=20
        daily_changes = [-50, -100, 200, -20]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertAlmostEqual(self.analyzer.max_loss_amount, 150.0, places=2)

    def test_known_streak_ratio(self):
        """验证连续盈亏比率"""
        base_worth = 10000
        # 3连胜, 2连败
        daily_changes = [100, 200, 150, -50, -100]

        current_worth = base_worth
        self._init_and_advance(self.analyzer, 0)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        for i, change in enumerate(daily_changes):
            current_worth += change
            self._init_and_advance(self.analyzer, i + 1)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # streak_ratio = max_wins / max_losses = 3 / 2 = 1.5
        self.assertAlmostEqual(self.analyzer.streak_ratio, 1.5, places=2)


class TestConsecutivePnLBoundaryConditions(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def _init_and_advance(self, analyzer, day_index):
        day_time = self.test_time + timedelta(days=day_index)
        analyzer.advance_time(day_time)

    def test_empty_data(self):
        """从未调用activate，验证默认值"""
        analyzer = ConsecutivePnL("test_consecutive_empty")
        self.assertEqual(analyzer.max_consecutive_wins, 0)
        self.assertEqual(analyzer.max_consecutive_losses, 0)
        self.assertEqual(analyzer.current_consecutive_wins, 0)
        self.assertEqual(analyzer.current_consecutive_losses, 0)

    def test_single_bar(self):
        """只传1条bar数据"""
        analyzer = ConsecutivePnL("test_consecutive_single")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_single_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        # 单日无前一天数据，所有值为0
        self.assertEqual(analyzer.max_consecutive_wins, 0)
        self.assertEqual(analyzer.max_consecutive_losses, 0)

    def test_all_zero_values(self):
        """所有bar的worth=0"""
        analyzer = ConsecutivePnL("test_consecutive_zeros")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_zeros_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        # Day0: init worth=0
        self._init_and_advance(analyzer, 0)
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})

        # Day1: worth=0 (0-0=0, daily_pnl=0, not >0 and not <0, so streak unchanged)
        self._init_and_advance(analyzer, 1)
        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})

        # 零变化不应影响连胜连败
        self.assertEqual(analyzer.max_consecutive_wins, 0)
        self.assertEqual(analyzer.max_consecutive_losses, 0)


if __name__ == '__main__':
    unittest.main()
