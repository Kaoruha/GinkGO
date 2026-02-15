import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.underwater_time import UnderwaterTime
from ginkgo.enums import RECORDSTAGE_TYPES


class TestUnderwaterTime(unittest.TestCase):
    """
    测试水下时间分析器
    """

    def setUp(self):
        """初始化测试用的UnderwaterTime实例"""
        self.analyzer = UnderwaterTime("test_underwater_time")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.on_time_goes_by(self.test_time)
        self.analyzer.set_analyzer_id("test_underwater_time_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试UnderwaterTime初始化"""
        analyzer = UnderwaterTime()
        
        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "underwater_time")
        self.assertIsNone(analyzer._peak_worth)
        self.assertEqual(analyzer._underwater_start_date, None)
        self.assertEqual(analyzer._current_underwater_days, 0)
        self.assertEqual(analyzer._max_underwater_days, 0)
        self.assertEqual(analyzer._total_underwater_days, 0)
        self.assertEqual(analyzer._underwater_periods, 0)
        
        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.ENDDAY, analyzer.active_stage)
        
        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_initial_calculation(self):
        """测试初始计算"""
        portfolio_info = {"worth": 10000}
        
        # 第一天，设置peak值，不应该有水下时间
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 0)
        self.assertEqual(self.analyzer._peak_worth, 10000)
        self.assertFalse(self.analyzer.is_underwater)

    def test_no_drawdown_scenario(self):
        """测试无回撤场景（持续上涨）"""
        base_worth = 10000
        
        # 10天持续上涨
        for i in range(10):
            worth = base_worth * (1 + 0.01 * (i + 1))  # 累计收益
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 无回撤，应该没有水下时间
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 0)
        self.assertEqual(self.analyzer.total_underwater_days, 0)
        self.assertEqual(self.analyzer.underwater_periods, 0)
        self.assertFalse(self.analyzer.is_underwater)

    def test_simple_drawdown_scenario(self):
        """测试简单回撤场景"""
        worth_sequence = [10000, 11000, 12000, 11000, 10500, 11500, 13000]  # 回撤后恢复
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 从12000回撤到10500，然后恢复到创新高
        # 水下时间应该是从第3天到第5天（2天）
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 2)
        self.assertEqual(self.analyzer.total_underwater_days, 2)
        self.assertEqual(self.analyzer.underwater_periods, 1)
        self.assertFalse(self.analyzer.is_underwater)

    def test_extended_drawdown_scenario(self):
        """测试长期回撤场景"""
        worth_sequence = [10000, 12000, 11000, 10000, 9500, 9000, 8500, 9000, 8800, 10500, 12500]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 从12000回撤，经历长期水下时间，最终恢复并创新高
        # 水下时间应该是从第2天到第9天（7天）
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 7)
        self.assertEqual(self.analyzer.total_underwater_days, 7)
        self.assertEqual(self.analyzer.underwater_periods, 1)
        self.assertFalse(self.analyzer.is_underwater)

    def test_multiple_drawdown_periods(self):
        """测试多个回撤周期"""
        worth_sequence = [10000, 11000, 10500, 11500, 12000, 11000, 10000, 11000, 13000, 12000, 11500, 13500]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 应该有两个回撤周期
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertGreater(self.analyzer.max_underwater_days, 0)
        self.assertGreater(self.analyzer.total_underwater_days, 0)
        self.assertEqual(self.analyzer.underwater_periods, 2)
        self.assertFalse(self.analyzer.is_underwater)

    def test_current_underwater_scenario(self):
        """测试当前仍在水下的场景"""
        worth_sequence = [10000, 12000, 11000, 10000, 9500, 9000, 8500, 9000, 8800, 9200]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 最后仍在水下（9200 < 12000）
        self.assertGreater(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, self.analyzer.current_underwater_days)
        self.assertEqual(self.analyzer.total_underwater_days, self.analyzer.current_underwater_days)
        self.assertEqual(self.analyzer.underwater_periods, 1)
        self.assertTrue(self.analyzer.is_underwater)

    def test_properties(self):
        """测试各种属性"""
        worth_sequence = [10000, 11000, 10500, 11500, 10000, 9500, 11000, 12000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
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
        periods = self.analyzer.underwater_periods
        self.assertIsInstance(periods, int)
        self.assertGreaterEqual(periods, 0)
        
        # 测试是否在水下
        is_underwater = self.analyzer.is_underwater
        self.assertIsInstance(is_underwater, bool)

    def test_zero_worth_handling(self):
        """测试零净值处理"""
        # 先设置正常值
        portfolio_info = {"worth": 10000}
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 然后设置零值
        portfolio_info = {"worth": 0}
        day_time = self.test_time + timedelta(days=1)
        self.analyzer.on_time_goes_by(day_time)
        self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 零值应该被视为水下
        self.assertTrue(self.analyzer.is_underwater)
        self.assertEqual(self.analyzer.current_underwater_days, 1)

    def test_recording_functionality(self):
        """测试记录功能"""
        worth_sequence = [10000, 11000, 10500, 11500, 10000, 9500, 11000, 12000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
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
        
        # 单日无回撤
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 0)
        self.assertFalse(self.analyzer.is_underwater)

    def test_peak_worth_tracking(self):
        """测试峰值跟踪"""
        worth_sequence = [10000, 15000, 12000, 18000, 14000, 20000, 16000]
        
        expected_peaks = [10000, 15000, 15000, 18000, 18000, 20000, 20000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
            
            # 检查峰值是否正确更新
            self.assertEqual(self.analyzer._peak_worth, expected_peaks[i])

    def test_underwater_period_counting(self):
        """测试水下周期计数"""
        # 创建三个独立的回撤周期
        worth_sequence = [10000, 12000, 11000, 13000, 12000, 14000, 13000, 15000, 14000, 16000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 应该有3个水下周期
        self.assertEqual(self.analyzer.underwater_periods, 3)
        self.assertEqual(self.analyzer.total_underwater_days, 3)
        self.assertEqual(self.analyzer.max_underwater_days, 1)

    def test_long_recovery_scenario(self):
        """测试长期恢复场景"""
        worth_sequence = [10000, 15000, 12000, 11000, 10000, 9000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 从15000回撤，经历长期水下时间，最终恢复并创新高
        # 水下时间应该是从第2天到第13天（11天）
        self.assertEqual(self.analyzer.current_underwater_days, 0)  # 已恢复
        self.assertEqual(self.analyzer.max_underwater_days, 11)
        self.assertEqual(self.analyzer.total_underwater_days, 11)
        self.assertEqual(self.analyzer.underwater_periods, 1)
        self.assertFalse(self.analyzer.is_underwater)

    def test_exact_peak_recovery(self):
        """测试精确峰值恢复"""
        worth_sequence = [10000, 12000, 11000, 10000, 9000, 10000, 11000, 12000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 恢复到峰值后应该结束水下状态
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertFalse(self.analyzer.is_underwater)

    def test_immediate_new_high(self):
        """测试立即创新高"""
        worth_sequence = [10000, 12000, 11000, 15000]
        
        for i, worth in enumerate(worth_sequence):
            portfolio_info = {"worth": worth}
            
            day_time = self.test_time + timedelta(days=i)
            self.analyzer.on_time_goes_by(day_time)
            self.analyzer.activate(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 创新高后应该立即结束水下状态
        self.assertEqual(self.analyzer.current_underwater_days, 0)
        self.assertEqual(self.analyzer.max_underwater_days, 1)
        self.assertEqual(self.analyzer.total_underwater_days, 1)
        self.assertFalse(self.analyzer.is_underwater)


if __name__ == '__main__':
    unittest.main()