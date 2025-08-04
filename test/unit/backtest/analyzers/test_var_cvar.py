import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from ginkgo.backtest.analysis.analyzers.var_cvar import VarCVar
from ginkgo.enums import RECORDSTAGE_TYPES


class TestVarCVar(unittest.TestCase):
    """
    测试VaR/CVaR分析器
    """

    def setUp(self):
        """初始化测试用的VarCVar实例"""
        self.analyzer = VarCVar("test_var_cvar", confidence_level=0.95)
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.on_time_goes_by(self.test_time)
        self.analyzer.set_analyzer_id("test_var_cvar_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试VarCVar初始化"""
        analyzer = VarCVar()
        
        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "var_cvar")
        self.assertEqual(analyzer._confidence_level, 0.95)  # 默认95%置信度
        self.assertEqual(len(analyzer._returns), 0)
        
        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)
        
        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_custom_confidence_level(self):
        """测试自定义置信度"""
        analyzer = VarCVar(confidence_level=0.99)
        self.assertEqual(analyzer._confidence_level, 0.99)
        
        analyzer = VarCVar(confidence_level=0.90)
        self.assertEqual(analyzer._confidence_level, 0.90)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}
        
        # 第一天，没有历史数据，VaR和CVaR应为0
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_var, 0.0)
        self.assertEqual(self.analyzer.current_cvar, 0.0)

    def test_insufficient_data(self):
        """测试数据不足时的处理"""
        base_worth = 10000
        
        # 前9天的数据（少于30个数据点）
        for i in range(9):
            worth = base_worth * (1 + 0.01 * (i + 1))
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
            
            # 数据不足，VaR和CVaR应为0
            self.assertEqual(self.analyzer.current_var, 0.0)
            self.assertEqual(self.analyzer.current_cvar, 0.0)

    def test_normal_returns_scenario(self):
        """测试正态分布收益场景"""
        base_worth = 10000
        np.random.seed(42)  # 固定随机种子
        
        # 生成40天的正态分布收益
        returns = np.random.normal(0.001, 0.02, 40)  # 均值0.1%，标准差2%
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 应该有VaR和CVaR值
        var = self.analyzer.current_var
        cvar = self.analyzer.current_cvar
        
        self.assertLess(var, 0)  # VaR应该是负值（损失）
        self.assertLess(cvar, 0)  # CVaR应该是负值（损失）
        self.assertLess(cvar, var)  # CVaR应该比VaR更极端（绝对值更大）

    def test_high_volatility_scenario(self):
        """测试高波动率场景"""
        base_worth = 10000
        # 高波动率收益序列
        returns = [0.05, -0.08, 0.06, -0.04, 0.07, -0.09, 0.03, -0.05, 0.08, -0.06,
                  0.04, -0.07, 0.05, -0.03, 0.06, -0.08, 0.02, -0.04, 0.07, -0.05,
                  0.03, -0.06, 0.04, -0.02, 0.05, -0.07, 0.01, -0.03, 0.06, -0.04,
                  0.02, -0.05, 0.03, -0.01, 0.04, -0.06, 0.01, -0.02, 0.05, -0.03]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 高波动率应该导致更大的VaR和CVaR（绝对值）
        var = self.analyzer.current_var
        cvar = self.analyzer.current_cvar
        
        self.assertLess(var, -0.03)  # 应该有较大的VaR
        self.assertLess(cvar, var)   # CVaR应该更极端

    def test_mostly_negative_returns(self):
        """测试主要负收益场景"""
        base_worth = 10000
        returns = [-0.01, -0.02, 0.005, -0.015, -0.01, -0.008, 0.003, -0.012, -0.018, -0.005,
                  -0.01, -0.02, 0.002, -0.015, -0.01, -0.008, 0.004, -0.012, -0.018, -0.005,
                  -0.01, -0.02, 0.001, -0.015, -0.01, -0.008, 0.003, -0.012, -0.018, -0.005,
                  -0.01, -0.02, 0.002, -0.015, -0.01, -0.008, 0.004, -0.012, -0.018, -0.005]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 主要负收益应该导致相对较大的VaR和CVaR
        var = self.analyzer.current_var
        cvar = self.analyzer.current_cvar
        
        self.assertLess(var, -0.01)  # 应该有显著的VaR
        self.assertLess(cvar, var)   # CVaR应该更极端

    def test_different_confidence_levels(self):
        """测试不同置信度的影响"""
        base_worth = 10000
        returns = [0.02, -0.03, 0.01, -0.04, 0.015, -0.02, 0.005, -0.05, 0.01, -0.015,
                  0.02, -0.03, 0.01, -0.04, 0.015, -0.02, 0.005, -0.05, 0.01, -0.015,
                  0.02, -0.03, 0.01, -0.04, 0.015, -0.02, 0.005, -0.05, 0.01, -0.015,
                  0.02, -0.03, 0.01, -0.04, 0.015, -0.02, 0.005, -0.05, 0.01, -0.015]
        
        analyzers = {
            0.90: VarCVar(confidence_level=0.90),
            0.95: VarCVar(confidence_level=0.95),
            0.99: VarCVar(confidence_level=0.99)
        }
        
        for confidence, analyzer in analyzers.items():
            current_worth = base_worth
            for i, ret in enumerate(returns):
                current_worth = current_worth * (1 + ret)
                portfolio_info = {"worth": current_worth}
                
                day_time = self.test_time + timedelta(days=i)
                analyzer.on_time_goes_by(day_time)
                analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 更高置信度应该导致更极端的VaR和CVaR
        var_90 = analyzers[0.90].current_var
        var_95 = analyzers[0.95].current_var
        var_99 = analyzers[0.99].current_var
        
        self.assertGreaterEqual(var_90, var_95)  # 90% VaR应该不比95% VaR更极端
        self.assertGreaterEqual(var_95, var_99)  # 95% VaR应该不比99% VaR更极端

    def test_properties(self):
        """测试各种属性"""
        base_worth = 10000
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02, -0.015, 0.01, -0.005,
                  0.015, -0.02, 0.01, -0.015, 0.005, -0.01, 0.02, -0.005, 0.015, -0.01,
                  0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02, -0.015, 0.01, -0.005,
                  0.015, -0.02, 0.01, -0.015, 0.005, -0.01, 0.02, -0.005, 0.015, -0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 测试当前VaR
        var = self.analyzer.current_var
        self.assertIsInstance(var, float)
        self.assertLessEqual(var, 0)  # VaR应该是非正数
        
        # 测试当前CVaR
        cvar = self.analyzer.current_cvar
        self.assertIsInstance(cvar, float)
        self.assertLessEqual(cvar, 0)  # CVaR应该是非正数
        self.assertLessEqual(cvar, var)  # CVaR应该不大于VaR
        
        # 测试年化VaR
        annual_var = self.analyzer.annualized_var
        self.assertIsInstance(annual_var, float)
        
        # 测试年化CVaR
        annual_cvar = self.analyzer.annualized_cvar
        self.assertIsInstance(annual_cvar, float)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        portfolio_info = {"worth": 0}
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_var, 0.0)
        self.assertEqual(self.analyzer.current_cvar, 0.0)

    def test_recording_functionality(self):
        """测试记录功能"""
        base_worth = 10000
        returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02, -0.015, 0.01, -0.005,
                  0.015, -0.02, 0.01, -0.015, 0.005, -0.01, 0.02, -0.005, 0.015, -0.01,
                  0.01, -0.02, 0.015, -0.01, 0.005, -0.025, 0.02, -0.015, 0.01, -0.005,
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
        
        # 单日无法计算VaR和CVaR
        self.assertEqual(self.analyzer.current_var, 0.0)
        self.assertEqual(self.analyzer.current_cvar, 0.0)

    def test_stable_returns_scenario(self):
        """测试稳定收益场景"""
        base_worth = 10000
        daily_return = 0.001  # 每天0.1%的稳定收益
        
        # 40天稳定收益
        for i in range(40):
            worth = base_worth * ((1 + daily_return) ** (i + 1))
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 稳定收益的VaR和CVaR应该相对较小
        var = self.analyzer.current_var
        cvar = self.analyzer.current_cvar
        
        self.assertGreater(var, -0.01)  # VaR应该相对较小
        self.assertGreater(cvar, -0.01)  # CVaR应该相对较小

    def test_extreme_negative_scenario(self):
        """测试极端负收益场景"""
        base_worth = 10000
        returns = [-0.02, -0.05, -0.03, -0.08, -0.04, -0.06, -0.01, -0.09, -0.02, -0.07,
                  -0.03, -0.04, -0.01, -0.05, -0.02, -0.06, -0.01, -0.08, -0.03, -0.04,
                  -0.02, -0.05, -0.01, -0.07, -0.03, -0.04, -0.02, -0.06, -0.01, -0.05,
                  -0.02, -0.08, -0.03, -0.04, -0.01, -0.06, -0.02, -0.05, -0.03, -0.07]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 极端负收益应该导致很大的VaR和CVaR
        var = self.analyzer.current_var
        cvar = self.analyzer.current_cvar
        
        self.assertLess(var, -0.05)  # 应该有很大的VaR
        self.assertLess(cvar, -0.06)  # 应该有很大的CVaR

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

    def test_cvar_calculation_consistency(self):
        """测试CVaR计算的一致性"""
        base_worth = 10000
        # 创建一个有明确分布的收益序列
        returns = [-0.05, -0.04, -0.03, -0.02, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05] * 4
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # CVaR应该是VaR以下收益的平均值
        var = self.analyzer.current_var
        cvar = self.analyzer.current_cvar
        
        self.assertLess(cvar, var)  # CVaR应该比VaR更极端
        self.assertLess(var, 0)     # VaR应该是负数
        self.assertLess(cvar, 0)    # CVaR应该是负数


if __name__ == '__main__':
    unittest.main()