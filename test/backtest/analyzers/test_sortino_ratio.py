import unittest
from datetime import datetime, timedelta
from decimal import Decimal
import numpy as np

from ginkgo.trading.analysis.analyzers.sortino_ratio import SortinoRatio
from ginkgo.enums import RECORDSTAGE_TYPES


class TestSortinoRatio(unittest.TestCase):
    """
    测试索提诺比率分析器
    """

    def setUp(self):
        """初始化测试用的SortinoRatio实例"""
        self.analyzer = SortinoRatio("test_sortino", risk_free_rate=0.03)
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.on_time_goes_by(self.test_time)
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
            self.analyzer.on_time_goes_by(day_time)
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
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 全为正收益时，索提诺比率应该很高（下行风险接近0）
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertGreater(sortino_ratio, 0)
        self.assertGreater(sortino_ratio, 10)  # 应该相对较高

    def test_mixed_returns_scenario(self):
        """测试混合收益场景"""
        base_worth = 10000
        returns = [0.02, -0.01, 0.015, -0.008, 0.01, -0.012, 0.018, -0.005, 0.01, -0.015, 0.02, -0.01]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
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
            self.analyzer.on_time_goes_by(day_time)
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
            self.analyzer.on_time_goes_by(day_time)
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
            self.analyzer.on_time_goes_by(day_time)
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
            self.analyzer.on_time_goes_by(day_time)
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
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 在这种情况下（小的负收益），索提诺比率应该相对较高
        # 因为下行风险很小
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertGreater(sortino_ratio, 0)
        
        # 下行波动率应该比总波动率小
        downside_vol = self.analyzer.downside_volatility
        total_vol = np.std(self.analyzer._returns) * np.sqrt(252)
        self.assertLess(downside_vol, total_vol)

    def test_no_negative_returns(self):
        """测试没有负收益时的处理"""
        base_worth = 10000
        returns = [0.01, 0.02, 0.005, 0.015, 0.01, 0.008, 0.02, 0.012, 0.018, 0.005, 0.01, 0.015]
        
        current_worth = base_worth
        for i, ret in enumerate(returns):
            current_worth = current_worth * (1 + ret)
            portfolio_info = {"worth": current_worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 没有负收益时，下行波动率应该为0
        downside_vol = self.analyzer.downside_volatility
        self.assertEqual(downside_vol, 0.0)
        
        # 索提诺比率应该很高（下行风险为0.0001）
        sortino_ratio = self.analyzer.current_sortino_ratio
        self.assertGreater(sortino_ratio, 10)


if __name__ == '__main__':
    unittest.main()