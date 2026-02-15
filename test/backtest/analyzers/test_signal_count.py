import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.trading.analysis.analyzers.signal_count import SignalCount
from ginkgo.enums import RECORDSTAGE_TYPES


class TestSignalCount(unittest.TestCase):
    """
    测试优化后的SignalCount分析器
    """

    def setUp(self):
        """初始化测试用的SignalCount实例"""
        self.analyzer = SignalCount("test_signal_count")
        self.test_time = datetime(2024, 1, 1, 9, 30, 0)
        self.analyzer.on_time_goes_by(self.test_time)
        self.analyzer.set_analyzer_id("test_signal_count_001")
        self.analyzer.set_portfolio_id("test_portfolio_001")

    def test_init(self):
        """测试SignalCount初始化"""
        analyzer = SignalCount()
        
        # 检查基本属性
        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer._name, "signal_count")
        self.assertEqual(analyzer._daily_count, 0)
        
        # 检查激活阶段配置
        self.assertIn(RECORDSTAGE_TYPES.SIGNALGENERATION, analyzer.active_stage)
        
        # 检查记录阶段配置
        self.assertEqual(analyzer.record_stage, RECORDSTAGE_TYPES.ENDDAY)

    def test_signal_counting(self):
        """测试信号计数功能"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 初始计数应为0
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        # 模拟信号生成，计数应增加
        self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 1)
        
        # 再次信号生成
        self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 2)
        
        # 多次信号生成
        for i in range(3):
            self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 5)

    def test_non_signal_stage_no_counting(self):
        """测试非信号生成阶段不会计数"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 初始计数为0
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        # 在其他阶段激活不应计数（因为active_stage只包含SIGNALGENERATION）
        self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ORDERSEND, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        self.analyzer.activate(RECORDSTAGE_TYPES.ORDERFILLED, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 0)

    def test_data_points_update(self):
        """测试数据点的正确更新"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 生成几个信号
        for expected_count in range(1, 4):
            self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
            
            # 检查内存中的数据点是否更新
            current_value = self.analyzer.get_data(self.test_time)
            self.assertEqual(current_value, Decimal(str(expected_count)))

    def test_end_day_recording_and_reset(self):
        """测试每天结束时的记录和重置功能"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 模拟一天内的信号生成
        for i in range(3):
            self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        
        # 确认计数正确
        self.assertEqual(self.analyzer.current_daily_count, 3)
        
        # 确认数据点存在
        recorded_value = self.analyzer.get_data(self.test_time)
        self.assertEqual(recorded_value, Decimal("3"))
        
        # 模拟一天结束，触发记录
        self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 确认计数器被重置
        self.assertEqual(self.analyzer.current_daily_count, 0)

    def test_zero_signals_day(self):
        """测试无信号生成的日子"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 一天内没有信号生成
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        # 一天结束，记录（应该不会出错）
        self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        
        # 确认计数器仍为0
        self.assertEqual(self.analyzer.current_daily_count, 0)

    def test_multiple_days_scenario(self):
        """测试多天场景"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 第一天：2个信号
        for i in range(2):
            self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        
        self.assertEqual(self.analyzer.current_daily_count, 2)
        first_day_value = self.analyzer.get_data(self.test_time)
        self.assertEqual(first_day_value, Decimal("2"))
        
        # 第一天结束
        self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        # 第二天：5个信号
        second_day_time = self.test_time + timedelta(days=1)
        self.analyzer.on_time_goes_by(second_day_time)
        
        for i in range(5):
            self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        
        self.assertEqual(self.analyzer.current_daily_count, 5)
        second_day_value = self.analyzer.get_data(second_day_time)
        self.assertEqual(second_day_value, Decimal("5"))
        
        # 第二天结束
        self.analyzer.record(RECORDSTAGE_TYPES.ENDDAY, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        # 验证两天的数据都被正确保存
        self.assertEqual(self.analyzer.get_data(self.test_time), Decimal("2"))
        self.assertEqual(self.analyzer.get_data(second_day_time), Decimal("5"))

    def test_current_daily_count_property(self):
        """测试current_daily_count属性"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 初始值
        self.assertEqual(self.analyzer.current_daily_count, 0)
        
        # 生成信号后
        self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.current_daily_count, 1)
        
        # 属性应该是只读的，返回内部计数
        self.assertEqual(self.analyzer.current_daily_count, self.analyzer._daily_count)

    def test_custom_name_initialization(self):
        """测试自定义名称初始化"""
        custom_analyzer = SignalCount("my_custom_signal_count")
        self.assertEqual(custom_analyzer._name, "my_custom_signal_count")
        self.assertEqual(custom_analyzer._daily_count, 0)

    def test_data_persistence_across_signals(self):
        """测试同一天内多个信号的数据点覆盖行为"""
        portfolio_info = {
            "cash": 10000,
            "positions": {},
            "worth": 10000
        }
        
        # 第一个信号
        self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.get_data(self.test_time), Decimal("1"))
        
        # 第二个信号（同一时间点，应该覆盖）
        self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.get_data(self.test_time), Decimal("2"))
        
        # 第三个信号（同一时间点，再次覆盖）
        self.analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)
        self.assertEqual(self.analyzer.get_data(self.test_time), Decimal("3"))
        
        # 数据框中应该只有一行数据
        self.assertEqual(len(self.analyzer.data), 1)


if __name__ == '__main__':
    unittest.main()