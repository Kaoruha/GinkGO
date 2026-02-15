import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np
from scipy import stats

from ginkgo.trading.analysis.analyzers.skew_kurtosis import SkewKurtosis
from ginkgo.enums import RECORDSTAGE_TYPES


class TestSkewKurtosis(unittest.TestCase):
    """
    测试偏度峰度分析器
    """

    def setUp(self):
        """初始化测试用的SkewKurtosis实例"""
        self.analyzer = SkewKurtosis("test_skew_kurtosis")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.on_time_goes_by(self.test_time)
        self.analyzer.set_analyzer_id("test_skew_kurtosis_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试SkewKurtosis初始化"""
        analyzer = SkewKurtosis()
        
        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "skew_kurtosis")
        self.assertEqual(len(analyzer._returns), 0)
        
        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)
        
        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}
        
        # 第一天，没有历史数据，偏度和峰度应为0
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_skewness, 0.0)
        self.assertEqual(self.analyzer.current_kurtosis, 0.0)

    def test_insufficient_data(self):
        """测试数据不足时的处理"""
        base_worth = 10000
        
        # 前9天的数据（少于10个数据点）
        for i in range(9):
            worth = base_worth * (1 + 0.01 * (i + 1))
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
            
            # 数据不足，偏度和峰度应为0
            self.assertEqual(self.analyzer.current_skewness, 0.0)
            self.assertEqual(self.analyzer.current_kurtosis, 0.0)

    def test_symmetric_distribution(self):
        """测试对称分布（偏度应接近0）"""
        base_worth = 10000
        # 创建对称分布的收益
        returns = [0.02, -0.02, 0.015, -0.015, 0.01, -0.01, 0.025, -0.025, 0.005, -0.005,
                  0.02, -0.02, 0.015, -0.015, 0.01, -0.01, 0.025, -0.025, 0.005, -0.005]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 对称分布的偏度应该接近0
        skewness = self.analyzer.current_skewness
        self.assertAlmostEqual(skewness, 0.0, places=1)

    def test_positive_skew_distribution(self):
        """测试正偏度分布（右偏）"""
        base_worth = 10000
        # 创建正偏度分布：更多小的正收益，少数大的负收益
        returns = [0.01, 0.005, 0.015, 0.01, 0.005, 0.02, 0.01, 0.005, 0.015, 0.01,
                  0.005, 0.02, 0.01, 0.005, 0.015, -0.08, 0.005, 0.01, 0.015, 0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 应该有负偏度（左偏，因为有大的负收益）
        skewness = self.analyzer.current_skewness
        self.assertLess(skewness, 0)

    def test_negative_skew_distribution(self):
        """测试负偏度分布（左偏）"""
        base_worth = 10000
        # 创建负偏度分布：更多小的负收益，少数大的正收益
        returns = [-0.01, -0.005, -0.015, -0.01, -0.005, -0.02, -0.01, -0.005, -0.015, -0.01,
                  -0.005, -0.02, -0.01, -0.005, -0.015, 0.08, -0.005, -0.01, -0.015, -0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 应该有正偏度（右偏，因为有大的正收益）
        skewness = self.analyzer.current_skewness
        self.assertGreater(skewness, 0)

    def test_normal_distribution_kurtosis(self):
        """测试正态分布的峰度"""
        base_worth = 10000
        np.random.seed(42)  # 固定随机种子
        
        # 生成正态分布的收益
        returns = np.random.normal(0.001, 0.02, 50)  # 均值0.1%，标准差2%
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 正态分布的峰度应该接近0（超额峰度）
        kurtosis = self.analyzer.current_kurtosis
        self.assertGreater(kurtosis, -2)  # 不应该是极端负值
        self.assertLess(kurtosis, 5)      # 不应该是极端正值

    def test_high_kurtosis_distribution(self):
        """测试高峰度分布（厚尾）"""
        base_worth = 10000
        # 创建高峰度分布：大多数收益接近0，少数极端收益
        returns = [0.0001, 0.0002, -0.0001, 0.0003, -0.0002, 0.0001, -0.0001, 0.0002, -0.0003, 0.0001,
                  0.0002, -0.0001, 0.0003, -0.0002, 0.0001, -0.0001, 0.0002, -0.0003, 0.0001, 0.0002,
                  -0.0001, 0.0003, -0.0002, 0.0001, -0.0001, 0.0002, -0.0003, 0.0001, 0.0002, -0.0001,
                  0.15, -0.15, 0.12, -0.12, 0.18, -0.18, 0.10, -0.10, 0.20, -0.20]  # 极端值
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 应该有高峰度（厚尾分布）
        kurtosis = self.analyzer.current_kurtosis
        self.assertGreater(kurtosis, 2)  # 应该有明显的正峰度

    def test_uniform_distribution_kurtosis(self):
        """测试均匀分布的峰度"""
        base_worth = 10000
        # 创建接近均匀分布的收益
        returns = [-0.05, -0.04, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05] * 4
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 均匀分布的峰度应该是负的（扁平）
        kurtosis = self.analyzer.current_kurtosis
        self.assertLess(kurtosis, 0)

    def test_properties(self):
        """测试各种属性"""
        base_worth = 10000
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02, -0.015, 0.01, -0.005,
                  0.015, -0.02, 0.01, -0.015, 0.005, -0.01, 0.02, -0.005, 0.015, -0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 测试当前偏度
        skewness = self.analyzer.current_skewness
        self.assertIsInstance(skewness, float)
        
        # 测试当前峰度
        kurtosis = self.analyzer.current_kurtosis
        self.assertIsInstance(kurtosis, float)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        portfolio_info = {"worth": 0}
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_skewness, 0.0)
        self.assertEqual(self.analyzer.current_kurtosis, 0.0)

    def test_recording_functionality(self):
        """测试记录功能"""
        base_worth = 10000
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02, -0.015, 0.01, -0.005,
                  0.015, -0.02, 0.01, -0.015, 0.005, -0.01, 0.02, -0.005, 0.015, -0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
            
            # 测试记录功能
            self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 确保有数据记录
        self.assertGreater(len(self.analyzer.data), 0)

    def test_single_day_scenario(self):
        """测试单日场景"""
        portfolio_info = {"worth": 10000}
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 单日无法计算偏度和峰度
        self.assertEqual(self.analyzer.current_skewness, 0.0)
        self.assertEqual(self.analyzer.current_kurtosis, 0.0)

    def test_identical_returns(self):
        """测试相同收益率"""
        base_worth = 10000
        daily_return = 0.01  # 每天1%的相同收益
        
        # 20天相同收益
        for i in range(20):
            worth = base_worth * ((1 + daily_return) ** (i + 1))
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 相同收益率的偏度和峰度应该为0或接近0
        skewness = self.analyzer.current_skewness
        kurtosis = self.analyzer.current_kurtosis
        
        # 由于除零或数据不足，可能返回0
        self.assertEqual(skewness, 0.0)
        self.assertEqual(kurtosis, 0.0)

    def test_extreme_values_impact(self):
        """测试极端值的影响"""
        base_worth = 10000
        # 大多数正常收益，加上极端值
        returns = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01,
                  0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, -0.5]  # 极端负收益
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 极端值应该导致显著的偏度和峰度
        skewness = self.analyzer.current_skewness
        kurtosis = self.analyzer.current_kurtosis
        
        self.assertLess(skewness, -1)  # 应该有明显的负偏度
        self.assertGreater(kurtosis, 5)  # 应该有高峰度

    def test_returns_accumulation(self):
        """测试收益率累积"""
        base_worth = 10000
        expected_returns = [0.01, 0.02, -0.01, 0.015]
        
        current_worth = base_worth
        for i, expected_ret in enumerate(expected_returns):
            current_worth = current_worth * (1 + expected_ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 检查收益率是否正确累积
        self.assertEqual(len(self.analyzer._returns), 3)  # 第一天无收益率
        
        # 验证收益率计算的合理性
        for i, actual_ret in enumerate(self.analyzer._returns):
            self.assertAlmostEqual(actual_ret, expected_returns[i+1], places=3)

    def test_volatility_clustering_effect(self):
        """测试波动率聚类效应"""
        base_worth = 10000
        # 创建波动率聚类：低波动期和高波动期
        low_vol_returns = [0.001, -0.001, 0.002, -0.002, 0.001, -0.001, 0.002, -0.002, 0.001, -0.001]
        high_vol_returns = [0.05, -0.08, 0.06, -0.04, 0.07, -0.09, 0.03, -0.05, 0.08, -0.06]
        returns = low_vol_returns + high_vol_returns
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 波动率聚类应该导致高峰度
        kurtosis = self.analyzer.current_kurtosis
        self.assertGreater(kurtosis, 1)  # 应该有正峰度

    def test_gradual_trend_scenario(self):
        """测试渐进趋势场景"""
        base_worth = 10000
        # 创建渐进上升趋势
        returns = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05,
                  0.045, 0.04, 0.035, 0.03, 0.025, 0.02, 0.015, 0.01, 0.005, 0.001]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 渐进趋势可能导致轻微的偏度
        skewness = self.analyzer.current_skewness
        kurtosis = self.analyzer.current_kurtosis
        
        self.assertGreater(skewness, -1)  # 偏度不应该太极端
        self.assertLess(skewness, 1)
        self.assertGreater(kurtosis, -2)  # 峰度不应该太极端
        self.assertLess(kurtosis, 2)


if __name__ == '__main__':
    unittest.main()