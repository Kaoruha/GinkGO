"""
性能: 270MB RSS, 2.34s, 19 tests [PASS]
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from ginkgo.trading.analysis.analyzers.sortino_ratio import SortinoRatio
from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.trading.time.providers import LogicalTimeProvider


class TestSortinoRatio(unittest.TestCase):
    """
    测试索提诺比率分析器
    """

    def setUp(self):
        """初始化测试用的SortinoRatio实例"""
        self.analyzer = SortinoRatio("test_sortino", risk_free_rate=0.03)
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.advance_time(self.test_time)
        from datetime import datetime as dt
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(dt(2024, 1, 1, 9, 30, 0))
        self.analyzer.set_analyzer_id("test_sortino_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试SortinoRatio初始化"""
        analyzer = SortinoRatio()

        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "sortino_ratio")
        self.assertEqual(analyzer._risk_free_rate, 0.03 / 252)  # 日无风险利率
        self.assertEqual(len(analyzer._returns), 0)

        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)

        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_custom_risk_free_rate(self):
        """测试自定义无风险利率"""
        analyzer = SortinoRatio(risk_free_rate=0.05)
        self.assertEqual(analyzer._risk_free_rate, 0.05 / 252)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}

        # 第一天，没有历史数据，索提诺比率应为0
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_sortino_ratio, 0.0)

    def test_insufficient_data(self):
        """测试数据不足时的处理"""
        base_worth = 10000

        # 前9天的数据（少于10个数据点）
        for i in range(9):
            worth = base_worth * (1 + 0.01 * (i + 1))  # 每天1%收益
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

            # 数据不足，索提诺比率应为0
            self.assertEqual(self.analyzer.current_sortino_ratio, 0.0)

    def test_positive_returns_scenario(self):
        """测试全为正收益的场景"""
        base_worth = 10000

        # 15天连续正收益
        for i in range(15):
            worth = base_worth * (1 + 0.01 * (i + 1))  # 累计收益
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 全为正收益时，索提诺比率应该很高（下行风险接近0）
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertGreater(sortino_ratio, 0)

    def test_mixed_returns_scenario(self):
        """测试混合收益场景"""
        base_worth = 10000
        returns = [0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005, 0.01, -0.015, 0.02, -0.01]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 有负收益时，索提诺比率应该是合理的数值
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertIsInstance(sortino_ratio, float)
        self.assertGreater(sortino_ratio, -10)  # 不应该是极端负值
        self.assertLess(sortino_ratio, 10)     # 不应该是极端正值

    def test_mostly_negative_returns(self):
        """测试主要为负收益的场景"""
        base_worth = 10000
        returns = [-0.01, -0.02, 0.005, -0.015, -0.01, -0.008, 0.01, -0.012, -0.018, -0.005, -0.01, -0.02]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 主要为负收益时，索提诺比率应该为负
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertLess(sortino_ratio, 0)

    def test_downside_volatility_property(self):
        """测试下行波动率属性"""
        base_worth = 10000
        returns = [0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 下行波动率应该大于0（有负收益）
        downside_vol = self.analyzer.downside_volatility
        self.assertGreater(downside_vol, 0)
        self.assertIsInstance(downside_vol, float)

    def test_zero_worth_handling(self):
        """测试零净值的处理"""
        portfolio_info = {"worth": 0}

        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_sortino_ratio, 0.0)

    def test_recording_functionality(self):
        """测试记录功能"""
        base_worth = 10000
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.015, 0.01, -0.005]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

            # 测试记录功能
            self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 确保有数据记录
        self.assertGreater(len(self.analyzer.data), 0)

    def test_returns_accumulation(self):
        """测试收益率累积"""
        base_worth = 10000

        # 生成5天的数据
        for i in range(5):
            worth = base_worth * (1 + 0.01 * (i + 1))
            portfolio_info = {"worth": worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 检查收益率是否正确累积
        self.assertEqual(len(self.analyzer._returns), 4)  # 第一天无收益率

        # 验证收益率计算
        expected_returns = [0.01, 0.0099, 0.0098, 0.0097]  # 近似值
        for i, expected in enumerate(expected_returns):
            self.assertAlmostEqual(self.analyzer._returns[i], expected, places=3)

    def test_comparison_with_sharpe_concept(self):
        """测试与夏普比率概念的比较（索提诺应该关注下行风险）"""
        base_worth = 10000
        # 收益序列：包含大的正收益和小的负收益
        returns = [0.03, -0.001, 0.025, -0.002, 0.02, -0.001, 0.035, -0.003, 0.01, -0.001, 0.02, -0.002]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 在这种情况下（小的负收益），索提诺比率应该相对较高
        # 因为下行风险很小
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertGreater(sortino_ratio, 0)

    def test_no_negative_returns(self):
        """测试没有负收益时的处理"""
        base_worth = 10000
        returns = [0.01, 0.02, 0.005, 0.015, 0.01, 0.008, 0.02, 0.012, 0.018, 0.005, 0.01, 0.015]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}

            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)

        # 没有负收益时，但超额收益可能为负（取决于risk_free_rate）
        # 使用risk_free_rate=0.03/252 = 0.000119
        # 所有收益都 > risk_free_rate，所以没有negative excess returns
        # downside_volatility should be 0
        downside_vol = self.analyzer.downside_volatility
        self.assertEqual(downside_vol, 0.0)

        # 索提诺比率应该很高（使用0.0001作为分母）
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertGreater(sortino_ratio, 0)


class TestSortinoRatioNumericalCorrectness(unittest.TestCase):
    """数值正确性验证 - 使用已知数据验证索提诺比率计算"""

    def setUp(self):
        self.analyzer = SortinoRatio("test_sortino_num", risk_free_rate=0.0)  # 用0无风险利率便于计算
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        self.analyzer.advance_time(self.test_time)
        self.analyzer.set_analyzer_id("test_sortino_num_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_all_positive_returns_high_sortino(self):
        """全部正收益时索提诺比率应很高"""
        base_worth = 10000
        returns = [0.02, 0.015, 0.025, 0.01, 0.03, 0.02, 0.015, 0.025, 0.01, 0.02,
                   0.015, 0.025]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 全正收益，下行波动率为0，索提诺比率应非常大
        self.assertGreater(self.analyzer.current_sortino_ratio, 10)

    def test_known_downside_deviation(self):
        """验证下行偏差的手动计算"""
        base_worth = 10000
        # risk_free_rate=0, 12个数据点
        # 负超额收益: -0.02, -0.01, -0.015
        # downside_dev = sqrt(mean([-0.02, -0.01, -0.015]^2))
        # = sqrt((0.0004+0.0001+0.000225)/3) = sqrt(0.000725/3) = sqrt(0.00024167) = 0.01554
        returns = [0.01, 0.02, -0.02, 0.015, -0.01, 0.01, 0.02, 0.015, -0.015, 0.02,
                   0.01, 0.015]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        # 手动计算验证
        import numpy as np
        arr = np.array(returns)
        neg = arr[arr < 0]
        expected_downside = float(np.sqrt(np.mean(neg ** 2)))
        self.assertAlmostEqual(self.analyzer.downside_volatility, expected_downside * np.sqrt(252), places=2)

    def test_negative_mean_returns(self):
        """平均收益为负时索提诺比率为负"""
        base_worth = 10000
        # 需要11次activate: 第1次初始化_last_worth, 后10次产生收益率(>=10阈值)
        returns = [-0.02, -0.015, -0.01, -0.025, -0.02, -0.015, -0.01, -0.025, -0.02, -0.015, -0.01]

        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.advance_time(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": current_worth})

        self.assertLess(self.analyzer.current_sortino_ratio, 0)


class TestSortinoRatioBoundaryConditions(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)

    def test_empty_data(self):
        """从未调用activate，验证默认值"""
        analyzer = SortinoRatio("test_sortino_empty")
        self.assertEqual(analyzer.current_sortino_ratio, 0.0)
        self.assertEqual(analyzer.downside_volatility, 0.0)
        self.assertEqual(len(analyzer._returns), 0)

    def test_single_bar(self):
        """只传1条bar数据"""
        analyzer = SortinoRatio("test_sortino_single")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_single_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 10000})
        self.assertEqual(analyzer.current_sortino_ratio, 0.0)

    def test_all_zero_values(self):
        """所有bar的worth=0"""
        analyzer = SortinoRatio("test_sortino_zeros")
        analyzer.set_time_provider(LogicalTimeProvider(initial_time=self.test_time))
        analyzer.advance_time(self.test_time)
        analyzer.set_analyzer_id("test_zeros_001")
        analyzer.set_portfolio_id("test_portfolio_001")

        for i in range(5):
            day_time = self.test_time + timedelta(days=i)
            analyzer.advance_time(day_time)
            analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, {"worth": 0})

        # _last_worth=0, 不满足 >0, 不添加收益率
        self.assertEqual(analyzer.current_sortino_ratio, 0.0)
        self.assertEqual(len(analyzer._returns), 0)


if __name__ == '__main__':
    unittest.main()
