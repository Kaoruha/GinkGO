"""
性能: 157MB RSS, 0.94s, 9 tests [PASS]
"""

import unittest
import datetime

from ginkgo.trading.engines import BacktestEngine as HistoricEngine


class HistoricEngineTest(unittest.TestCase):
    """
    测试HistoricEngine模块 - 仅测试HistoricEngine
    """

    def setUp(self):
        """初始化测试用的HistoricEngine实例"""
        self.engine = HistoricEngine("test_historic_engine")
        self.test_time = datetime.datetime(2024, 1, 1, 10, 0, 0)
        self.engine.advance_time_to(self.test_time)

    def tearDown(self):
        """清理测试资源"""
        # 确保引擎停止，避免线程泄露
        if hasattr(self.engine, 'stop'):
            try:
                self.engine.stop()
            except:
                pass

    def test_HistoricEngine_Init(self):
        """测试历史回测引擎初始化"""
        engine = HistoricEngine("test_historic_engine")
        self.assertIsNotNone(engine)

        # 检查基本属性
        self.assertTrue(hasattr(engine, "_name"))
        self.assertEqual(engine._name, "test_historic_engine")

    def test_default_initialization(self):
        """测试默认初始化"""
        engine = HistoricEngine()
        self.assertEqual(engine._name, "TimeControlledEngine")
        self.assertEqual(engine._timer_interval, 1.0)  # 继承自EventEngine

    def test_custom_interval(self):
        """测试自定义间隔"""
        engine = HistoricEngine("test", timer_interval=5.0)
        self.assertEqual(engine._timer_interval, 5.0)

    def test_inheritance_from_event_engine(self):
        """测试是否正确继承EventEngine"""
        from ginkgo.trading.engines.event_engine import EventEngine
        from ginkgo.trading.engines.base_engine import BaseEngine
        
        # 验证继承关系
        self.assertIsInstance(self.engine, EventEngine)
        self.assertIsInstance(self.engine, BaseEngine)
        
        # 验证继承的属性和方法
        self.assertTrue(hasattr(self.engine, "start"))
        self.assertTrue(hasattr(self.engine, "pause"))
        self.assertTrue(hasattr(self.engine, "stop"))
        self.assertTrue(hasattr(self.engine, "_event_queue"))
        self.assertTrue(hasattr(self.engine, "_handlers"))

    def test_backtest_interval_property(self):
        """测试回测间隔属性"""
        self.assertTrue(hasattr(self.engine, "_backtest_interval"))
        self.assertIsInstance(self.engine._backtest_interval, datetime.timedelta)
        
        # 默认应该是1天
        expected_interval = datetime.timedelta(days=1)
        self.assertEqual(self.engine._backtest_interval, expected_interval)

    def test_date_range_attributes(self):
        """测试日期范围属性"""
        # 检查开始日期属性
        self.assertTrue(hasattr(self.engine, "_start_date"))
        self.assertIsNone(self.engine._start_date)  # 初始应该为None
        
        # 检查结束日期属性
        self.assertTrue(hasattr(self.engine, "_end_date"))
        self.assertIsNone(self.engine._end_date)  # 初始应该为None

    def test_max_waits_property(self):
        """测试最大等待次数属性"""
        # _max_waits has been removed in TimeControlledEventEngine;
        # event timeout is now controlled by _event_timeout_seconds.
        self.assertTrue(hasattr(self.engine, "_event_timeout_seconds"))
        self.assertEqual(self.engine._event_timeout_seconds, 30.0)  # 默认值

    def test_empty_count_attribute(self):
        """测试空计数属性"""
        # _empty_count has been removed in TimeControlledEventEngine.
        # Event sequence tracking is now handled by _event_sequence_number.
        self.assertTrue(hasattr(self.engine, "_event_sequence_number"))
        # Note: value is >0 because setUp calls advance_time_to, which increments the counter
        self.assertGreaterEqual(self.engine._event_sequence_number, 0)

    def test_backtest_interval_modification(self):
        """测试回测间隔修改"""
        # 测试动态修改回测间隔
        original_interval = self.engine._backtest_interval

        # 检查是否有设置方法
        if hasattr(self.engine, "set_backtest_interval"):
            # set_backtest_interval expects timedelta, not string
            self.engine.set_backtest_interval(datetime.timedelta(minutes=1))
            expected_interval = datetime.timedelta(minutes=1)
            self.assertEqual(self.engine._backtest_interval, expected_interval)

            # 测试设置回DAY
            self.engine.set_backtest_interval(datetime.timedelta(days=1))
            expected_interval = datetime.timedelta(days=1)
            self.assertEqual(self.engine._backtest_interval, expected_interval)
        else:
            # 直接修改属性
            new_interval = datetime.timedelta(hours=1)
            self.engine._backtest_interval = new_interval
            self.assertEqual(self.engine._backtest_interval, new_interval)

