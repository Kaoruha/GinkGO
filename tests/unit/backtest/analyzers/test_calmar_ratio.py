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


if __name__ == '__main__':
    unittest.main()
