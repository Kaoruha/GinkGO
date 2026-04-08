"""
性能: 269MB RSS, 2.53s, 20 tests [PASS]
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.calmar_ratio import CalmarRatio
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestCalmarRatio(unittest.TestCase):
    """
    测试卡尔马比率分析器
    """

    def setUp(self):
        """初始化测试用的CalmarRatio实例"""
        self.analyzer = CalmarRatio("test_calmar")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.advance_time(self.test_time)
        from datetime import datetime as dt
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(dt(2024, 1, 1, 9, 30, 0))
        self.analyzer.set_analyzer_id("test_calmar_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试CalmarRatio初始化"""
        analyzer = CalmarRatio()

        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "calmar_ratio")
        self.assertIsNone(analyzer._initial_worth)
        self.assertIsNone(analyzer._max_worth)
        self.assertEqual(analyzer._max_drawdown, 0.0)
        self.assertEqual(analyzer._trading_days, 0)

        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)

        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}

        # 第一天，卡尔马比率应为0
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_calmar_ratio, 0.0)
        self.assertEqual(self.analyzer._initial_worth, 10000)
        self.assertEqual(self.analyzer._max_worth, 10000)

    def test_no_drawdown_scenario(self):
        """测试无回撤场景（持续上涨）"""
        base_worth = 10000

        # 20天持续上涨
        for i in range(20):
            worth = base_worth * (1 + 0.01 * (i + 1))  # 累计收益
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 无回撤时，卡尔马比率应该很高（使用0.001作为分母）
        calmar_ratio = self.analyzer.current_calmar_ratio
        self.assertGreater(calmar_ratio, 10)

        # 最大回撤应为0
        self.assertEqual(self.analyzer.max_drawdown_ratio, 0.0)

    def test_with_drawdown_scenario(self):
        """测试有回撤场景"""
        worth_sequence = [10000, 11000, 12000, 10500, 9500, 11500, 13000, 12000, 14000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 检查最大回撤计算
        # 最高点是14000（最后一天），最低点在最高点之前是9500
        # 但max_worth跟踪的是历史最高，从12000到9500的回撤 = (12000-9500)/12000 = 0.208333
        # 后面到14000创了新高，之前的回撤是历史最大
        max_drawdown = self.analyzer.max_drawdown_ratio
        self.assertGreater(max_drawdown, 0)
        self.assertAlmostEqual(max_drawdown, 0.2083, places=3)

        # 卡尔马比率应该是合理值
        calmar_ratio = self.analyzer.current_calmar_ratio
        self.assertIsInstance(calmar_ratio, float)

    def test_negative_performance(self):
        """测试负收益表现"""
        worth_sequence = [10000, 9500, 9000, 8500, 8000, 7500, 9000, 8200]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 总体是盈利的（10000 -> 8200是亏损，但max_worth从10000降到9000...）
        # 初始10000，max_worth=10000，最低9500 (dd=0.05), 然后9000 (dd=0.1), ...
        # 最终8200 < 10000，所以总收益为负
        # _trading_days = 7
        # total_return = (8200-10000)/10000 = -0.18
        # annualized_return = (1-0.18)^(252/7) - 1 = 很负
        # calmar = annualized / max_drawdown
        annual_return = self.analyzer.annualized_return
        self.assertLess(annual_return, 0)

    def test_annualized_return_calculation(self):
        """测试年化收益率计算"""
        # 模拟252个交易日的数据（1年）
        base_worth = 10000
        final_worth = 12000  # 20%年收益

        # 简化：直线增长
        for i in range(252):
            worth = base_worth + (final_worth - base_worth) * (i + 1) / 252
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 年化收益率应该接近20%
        annual_return = self.analyzer.annualized_return
        self.assertAlmostEqual(annual_return, 0.2, places=2)

    def test_max_drawdown_tracking(self):
        """测试最大回撤跟踪"""
        # 创建有多个回撤的序列
        worth_sequence = [10000, 12000, 11000, 13000, 10000, 14000, 12000, 15000]

        expected_max_drawdowns = [0, 0, 0.0833, 0, 0.2308, 0, 0.1429, 0]  # 近似值

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

            # 检查最大回撤是否正确更新
            if i >= 2:  # 从第三天开始有回撤
                max_dd = self.analyzer.max_drawdown_ratio
                self.assertGreaterEqual(max_dd, expected_max_drawdowns[i] - 0.01)

    def test_properties(self):
        """测试各种属性"""
        worth_sequence = [10000, 11000, 10500, 12000, 11000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 测试当前卡尔马比率
        calmar = self.analyzer.current_calmar_ratio
        self.assertIsInstance(calmar, float)

        # 测试年化收益率
        annual_ret = self.analyzer.annualized_return
        self.assertIsInstance(annual_ret, float)

        # 测试最大回撤比例
        max_dd = self.analyzer.max_drawdown_ratio
        self.assertIsInstance(max_dd, float)
        self.assertGreaterEqual(max_dd, 0)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        portfolio_info = {"worth": 0}

        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_calmar_ratio, 0.0)

    def test_recording_functionality(self):
        """测试记录功能"""
        worth_sequence = [10000, 11000, 10500, 12000, 11500]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

            # 测试记录功能
            self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 确保有数据记录
        self.assertGreater(len(self.analyzer.data), 0)

    def test_single_day_scenario(self):
        """测试单日场景"""
        portfolio_info = {"worth": 10000}

        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 单日无法计算有意义的卡尔马比率
        self.assertEqual(self.analyzer.current_calmar_ratio, 0.0)
        self.assertEqual(self.analyzer._trading_days, 0)

    def test_extreme_drawdown(self):
        """测试极端回撤场景"""
        worth_sequence = [10000, 15000, 5000, 12000]  # 66.7%回撤

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 极端回撤应该被正确记录
        max_drawdown = self.analyzer.max_drawdown_ratio
        self.assertAlmostEqual(max_drawdown, 0.6667, places=3)

        # 卡尔马比率应该是合理值
        calmar_ratio = self.analyzer.current_calmar_ratio
        self.assertIsInstance(calmar_ratio, float)

    def test_recovery_scenario(self):
        """测试恢复场景"""
        worth_sequence = [10000, 8000, 6000, 8000, 10000, 12000]  # 回撤后恢复并创新高

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 最大回撤应该记录历史最大值
        # 从10000跌到6000: max_worth=10000, dd=(10000-6000)/10000=0.4
        # 后面8000 < 10000: dd=0.2 (not max)
        # 10000 == 10000: dd=0, new high? no (not greater), but max stays at 0.4
        # 12000 > 10000: new max=12000, no new drawdown
        max_drawdown = self.analyzer.max_drawdown_ratio
        self.assertAlmostEqual(max_drawdown, 0.4, places=2)  # 从10000到6000的40%回撤

        # 最终创新高后的卡尔马比率
        calmar_ratio = self.analyzer.current_calmar_ratio
        self.assertGreater(calmar_ratio, 0)


class TestCalmarRatioNumericalCorrectness(unittest.TestCase):
    """数值正确性验证 - 使用已知数据验证计算结果"""

    def setUp(self):
        self.analyzer = CalmarRatio("test_calmar_numerical")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_calmar_num_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_known_drawdown_calculation(self):
        """使用已知净值序列验证最大回撤计算"""
        # 序列: 10000 -> 12000 -> 10000 -> 13000
        # Day0: init, _initial_worth=10000, _max_worth=10000
        # Day1: worth=12000 > max=10000 -> new max=12000, no drawdown
        # Day2: worth=10000 < max=12000 -> dd=(12000-10000)/12000=0.166667, max_dd=0.166667
        # Day3: worth=13000 > max=12000 -> new max=13000, no new dd
        worth_sequence = [10000, 12000, 10000, 13000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 最大回撤应为 (12000-10000)/12000 = 1/6
        self.assertAlmostEqual(self.analyzer.max_drawdown_ratio, 1.0 / 6.0, places=4)

    def test_known_annualized_return(self):
        """使用已知序列验证年化收益率计算"""
        # 252个交易日，净值从10000涨到11000 (10%总收益)
        # annualized_return = (1 + 0.10)^(252/252) - 1 = 0.10
        worth_sequence = [10000 + (1000 * (i + 1) / 252) for i in range(253)]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        self.assertAlmostEqual(self.analyzer.annualized_return, 0.10, places=2)

    def test_known_calmar_ratio(self):
        """使用已知数据验证卡尔马比率"""
        # 简化序列: 10000 -> 12000 -> 9000 -> 10000
        # Day0: init, _initial_worth=10000
        # Day1: worth=12000 > max=10000 -> new max=12000, _trading_days=1
        # Day2: worth=9000 < max=12000 -> dd=(12000-9000)/12000=0.25, max_dd=0.25, _trading_days=2
        # Day3: worth=10000 < max=12000 -> dd=(12000-10000)/12000=0.1667, _trading_days=3
        # total_return = (10000-10000)/10000 = 0
        # annualized = (1+0)^(252/3) - 1 = 0
        # calmar = 0 / 0.25 = 0
        worth_sequence = [10000, 12000, 9000, 10000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        self.assertAlmostEqual(self.analyzer.max_drawdown_ratio, 0.25, places=4)
        # 总收益=0, 年化=0, calmar=0
        self.assertEqual(self.analyzer.current_calmar_ratio, 0.0)

    def test_known_calmar_ratio_positive_return(self):
        """验证正收益场景的卡尔马比率"""
        # 10天序列: 10000 -> 11000 -> 8000 -> 12000 -> 8000 -> 12000 -> ... -> 15000
        # 通过交替高低值产生回撤
        # Day0: init, _initial_worth=10000
        # Day1: 11000 > 10000 -> max=11000, td=1
        # Day2: 8000 < 11000 -> dd=(11000-8000)/11000=0.2727, max_dd=0.2727, td=2
        # Day3: 12000 > 11000 -> max=12000, td=3
        # Day4: 8000 < 12000 -> dd=(12000-8000)/12000=0.3333, max_dd=0.3333, td=4
        # Day5: 13000 > 12000 -> max=13000, td=5
        # Day6: 9000 < 13000 -> dd=(13000-9000)/13000=0.3077, td=6
        # Day7: 14000 > 13000 -> max=14000, td=7
        # Day8: 10000 < 14000 -> dd=(14000-10000)/14000=0.2857, td=8
        # Day9: 15000 > 14000 -> max=15000, td=9
        # total_return = (15000-10000)/10000 = 0.5
        # annualized = (1.5)^(252/9) - 1 = 非常大的正数
        # calmar = annualized / 0.3333
        worth_sequence = [10000, 11000, 8000, 12000, 8000, 13000, 9000, 14000, 10000, 15000]

        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        max_dd = self.analyzer.max_drawdown_ratio
        self.assertAlmostEqual(max_dd, 4000.0 / 12000.0, places=4)  # 1/3
        calmar = self.analyzer.current_calmar_ratio
        self.assertGreater(calmar, 0)


class TestCalmarRatioBoundaryConditions(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def test_empty_data(self):
        """传入空数据，验证不崩溃且返回合理值"""
        analyzer = CalmarRatio("test_calmar_empty")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        # 从未调用activate，所有属性应为默认值
        self.assertIsNone(analyzer._initial_worth)
        self.assertEqual(analyzer.current_calmar_ratio, 0.0)
        self.assertEqual(analyzer.annualized_return, 0.0)
        self.assertEqual(analyzer.max_drawdown_ratio, 0.0)

    def test_single_bar(self):
        """只传1条bar数据"""
        analyzer = CalmarRatio("test_calmar_single")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_single_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        # 单日初始化，不应崩溃
        self.assertEqual(analyzer._initial_worth, 10000)
        self.assertEqual(analyzer.current_calmar_ratio, 0.0)
        self.assertEqual(analyzer.annualized_return, 0.0)
        self.assertEqual(analyzer.max_drawdown_ratio, 0.0)

    def test_all_zero_values(self):
        """所有bar的worth=0，验证不会除零崩溃"""
        analyzer = CalmarRatio("test_calmar_zeros")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_zeros_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        for i in range(5):
            portfolio_info = {"worth": 0}
            day_time = self.test_time + timedelta(days=i)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 初始为0，后续净值不变，_initial_worth=0
        # annualized_return中 _initial_worth > 0 不满足，返回0.0
        self.assertEqual(analyzer.current_calmar_ratio, 0.0)
        self.assertEqual(analyzer.annualized_return, 0.0)


if __name__ == '__main__':
    unittest.main()
