import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from ginkgo.backtest.analysis.analyzers.volatility import Volatility
from ginkgo.enums import RECORDSTAGE_TYPES


class TestVolatility(unittest.TestCase):
    """
    测试波动率分析器
    """

    def setUp(self):
        """初始化测试用的Volatility实例"""
        self.analyzer = Volatility("test_volatility", window_size=20)
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.on_time_goes_by(self.test_time)
        self.analyzer.set_analyzer_id("test_volatility_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试Volatility初始化"""
        analyzer = Volatility()
        
        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "volatility")
        self.assertEqual(analyzer._window_size, 20)  # 默认窗口大小
        self.assertEqual(len(analyzer._returns), 0)
        
        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)
        
        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_custom_window_size(self):
        """测试自定义窗口大小"""
        analyzer = Volatility(window_size=30)
        self.assertEqual(analyzer._window_size, 30)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}
        
        # 第一天，没有历史数据，波动率应为0
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_volatility, 0.0)

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
            
            # 数据不足，波动率应为0
            self.assertEqual(self.analyzer.current_volatility, 0.0)

    def test_stable_returns_scenario(self):
        """测试稳定收益场景（低波动率）"""
        base_worth = 10000
        daily_return = 0.001  # 每天0.1%的稳定收益
        
        # 25天稳定收益
        for i in range(25):
            worth = base_worth * ((1 + daily_return) ** (i + 1))
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 稳定收益的波动率应该非常低
        volatility = self.analyzer.current_volatility
        self.assertGreater(volatility, 0)
        self.assertLess(volatility, 0.05)  # 年化波动率应低于5%

    def test_volatile_returns_scenario(self):
        """测试高波动率场景"""
        base_worth = 10000
        returns = [0.05, -0.03, 0.04, -0.02, 0.06, -0.04, 0.03, -0.05, 0.02, -0.01,
                  0.04, -0.02, 0.05, -0.03, 0.01, -0.02, 0.03, -0.01, 0.02, -0.01,
                  0.05, -0.04, 0.02, -0.03, 0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 高波动收益的波动率应该较高
        volatility = self.analyzer.current_volatility
        self.assertGreater(volatility, 0.2)  # 年化波动率应高于20%
        self.assertLess(volatility, 1.0)     # 但应该在合理范围内

    def test_rolling_window_calculation(self):
        """测试滚动窗口计算"""
        base_worth = 10000
        returns = [0.01, 0.02, -0.01, 0.015, -0.005, 0.02, -0.01, 0.01, 0.005, -0.015,
                  0.02, -0.01, 0.015, -0.005, 0.01, 0.02, -0.01, 0.005, -0.01, 0.015,
                  0.03, -0.02, 0.01, -0.005, 0.02]  # 25天数据
        
        current_worth = base_worth
        volatilities = []
        
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
            
            volatilities.append(self.analyzer.current_volatility)
        
        # 前10天波动率应为0
        for i in range(10):
            self.assertEqual(volatilities[i], 0.0)
        
        # 第11天开始有波动率计算
        for i in range(10, len(volatilities)):
            self.assertGreater(volatilities[i], 0)
        
        # 随着窗口滑动，波动率应该有变化
        window_volatilities = volatilities[10:]
        self.assertGreater(len(set(window_volatilities)), 1)  # 不应该都相同

    def test_window_size_effect(self):
        """测试不同窗口大小的影响"""
        analyzers = {
            10: Volatility(window_size=10),
            30: Volatility(window_size=30)
        }
        
        base_worth = 10000
        returns = [0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005, 0.01, -0.015,
                  0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005, 0.01, -0.015,
                  0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005, 0.01, -0.015,
                  0.02, -0.01, 0.015, -0.008, 0.01]  # 35天数据
        
        for window_size, analyzer in analyzers.items():
            current_worth = base_worth
            for i, ret in enumerate(returns):
                current_worth = current_worth * (1 + ret)
                portfolio_info = {"worth": current_worth}
                
                day_time = self.test_time + timedelta(days=i)
                analyzer.on_time_goes_by(day_time)
                analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 较小窗口的波动率通常更敏感
        vol_10 = analyzers[10].current_volatility
        vol_30 = analyzers[30].current_volatility
        
        self.assertGreater(vol_10, 0)
        self.assertGreater(vol_30, 0)
        # 不一定小窗口波动率更高，取决于数据，但应该都在合理范围内
        self.assertLess(vol_10, 2.0)
        self.assertLess(vol_30, 2.0)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        portfolio_info = {"worth": 0}
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_volatility, 0.0)

    def test_properties(self):
        """测试各种属性"""
        base_worth = 10000
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.015, 
                  0.01, -0.005, 0.02, -0.01, 0.015]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 测试当前波动率
        volatility = self.analyzer.current_volatility
        self.assertIsInstance(volatility, float)
        self.assertGreaterEqual(volatility, 0)
        
        # 测试年化波动率（应该相同）
        annualized_vol = self.analyzer.annualized_volatility
        self.assertEqual(volatility, annualized_vol)

    def test_recording_functionality(self):
        """测试记录功能"""
        base_worth = 10000
        returns = [0.01, -0.005, 0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.015,
                  0.01, -0.005]
        
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
        
        # 验证收益率计算的合理性（考虑复利效应）
        for i, actual_ret in enumerate(self.analyzer._returns):
            self.assertAlmostEqual(actual_ret, expected_returns[i+1], places=3)

    def test_extreme_volatility_scenario(self):
        """测试极端波动率场景"""
        base_worth = 10000
        # 极端波动：大涨大跌
        returns = [0.1, -0.08, 0.12, -0.1, 0.15, -0.12, 0.08, -0.06, 0.1, -0.09,
                  0.11, -0.08, 0.13, -0.1, 0.09]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 极端波动的年化波动率应该很高
        volatility = self.analyzer.current_volatility
        self.assertGreater(volatility, 1.0)  # 年化波动率应高于100%

    def test_single_day_scenario(self):
        """测试单日场景"""
        portfolio_info = {"worth": 10000}
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 单日无法计算波动率
        self.assertEqual(self.analyzer.current_volatility, 0.0)

    def test_two_day_scenario(self):
        """测试两日场景"""
        portfolio_info_day1 = {"worth": 10000}
        portfolio_info_day2 = {"worth": 10100}
        
        # 第一天
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info_day1)
        self.assertEqual(self.analyzer.current_volatility, 0.0)
        
        # 第二天
        day2_time = self.test_time + timedelta(days=1)
        self.analyzer.on_time_goes_by(day2_time)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info_day2)
        
        # 两天仍然无法计算波动率（需要至少10个数据点）
        self.assertEqual(self.analyzer.current_volatility, 0.0)


if __name__ == '__main__':
    unittest.main()