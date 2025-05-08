import unittest
from unittest.mock import patch
import pandas as pd
import datetime
from decimal import Decimal
from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import GRAPHY_TYPES, RECORDSTAGE_TYPES, SOURCE_TYPES
from ginkgo.data.models import MAnalyzerRecord
from ginkgo.data.drivers import get_table_size


class TestBaseAnalyzer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """初始化 BaseAnalyzer 实例"""
        pass

    def setUp(self):
        """初始化 BaseAnalyzer 实例"""
        self.model = MAnalyzerRecord
        self.analyzer = BaseAnalyzer(name="TestAnalyzer")
        self.now = datetime.datetime(2024, 1, 1)
        self.analyzer.on_time_goes_by(self.now)

    def test_init(self):
        """测试初始化时各个属性是否正确设置"""
        self.assertEqual(self.analyzer._name, "TestAnalyzer")
        self.assertEqual(self.analyzer._active_stage, [])
        self.assertEqual(self.analyzer._record_stage, RECORDSTAGE_TYPES.NEWDAY)
        self.assertEqual(self.analyzer._analyzer_id, "")
        self.assertEqual(self.analyzer._portfolio_id, "")
        self.assertEqual(self.analyzer._data.shape, (0, 2))
        self.assertEqual(self.analyzer._graph_type, GRAPHY_TYPES.OTHER)

    def test_on_time_goes_by(self):
        """测试时间推进方法"""
        new_time = self.now + datetime.timedelta(days=1)
        self.analyzer.on_time_goes_by(new_time)
        self.assertEqual(self.analyzer.now, new_time)

    def test_set_graph_type(self):
        """测试设置图表类型"""
        self.analyzer.set_graph_type(GRAPHY_TYPES.BAR)
        self.assertEqual(self.analyzer._graph_type, GRAPHY_TYPES.BAR)

    def test_analyzer_id_property(self):
        """测试 analyzer_id 属性"""
        self.assertEqual(self.analyzer.analyzer_id, "")
        new_id = "12345"
        self.analyzer.set_analyzer_id(new_id)
        self.assertEqual(self.analyzer.analyzer_id, new_id)

    def test_set_analyzer_id(self):
        """测试设置 analyzer_id 方法"""
        new_id = "67890"
        self.assertEqual(self.analyzer.set_analyzer_id(new_id), new_id)

    def test_portfolio_id_property(self):
        """测试 portfolio_id 属性"""
        self.assertEqual(self.analyzer.portfolio_id, "")
        new_portfolio_id = "portfolio_001"
        self.analyzer.set_portfolio_id(new_portfolio_id)
        self.assertEqual(self.analyzer.portfolio_id, new_portfolio_id)

    def test_active_stage_property(self):
        """测试 active_stage 属性"""
        self.assertEqual(self.analyzer.active_stage, [])
        self.analyzer.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        self.assertIn(RECORDSTAGE_TYPES.SIGNALGENERATION, self.analyzer.active_stage)

    def test_record_stage_property(self):
        """测试 record_stage 属性"""
        self.assertEqual(self.analyzer.record_stage, RECORDSTAGE_TYPES.NEWDAY)
        self.analyzer.set_record_stage(RECORDSTAGE_TYPES.ORDERSEND)
        self.assertEqual(self.analyzer.record_stage, RECORDSTAGE_TYPES.ORDERSEND)

    def test_add_active_stage(self):
        """测试 add_active_stage 方法"""
        self.analyzer.add_active_stage(RECORDSTAGE_TYPES.ORDERFILLED)
        self.assertIn(RECORDSTAGE_TYPES.ORDERFILLED, self.analyzer._active_stage)

    def test_set_record_stage(self):
        """测试 set_record_stage 方法"""
        self.analyzer.set_record_stage(RECORDSTAGE_TYPES.ORDERCANCELED)
        self.assertEqual(self.analyzer._record_stage, RECORDSTAGE_TYPES.ORDERCANCELED)

    def test_add_data(self):
        """测试 add_data 方法"""
        self.analyzer.add_data(100.5)
        self.assertEqual(self.analyzer.get_data(self.now), Decimal("100.5"))

        # 测试相同时间数据的更新
        self.analyzer.add_data(150.75)
        self.assertEqual(self.analyzer.get_data(self.now), Decimal("150.75"))

    def test_get_data(self):
        """测试 get_data 方法"""
        self.analyzer.add_data(100.0)
        result = self.analyzer.get_data(self.now)
        self.assertEqual(result, Decimal("100.0"))

        # 测试不存在的时间
        future_time = self.now + datetime.timedelta(days=1)
        result = self.analyzer.get_data(future_time)
        self.assertIsNone(result)

    def test_add_record(self):
        """测试 add_record 方法是否执行数据库操作"""
        size0 = get_table_size(self.model)
        self.analyzer.set_portfolio_id("test_portfolio")

        # 假设 add_record 会触发数据库操作
        self.analyzer.add_data(100.0)  # 先添加数据
        self.analyzer.add_record()  # 调用 add_record 来插入数据库
        size1 = get_table_size(self.model)
        self.assertEqual(size1 - size0, 1)

    def test_mean_property(self):
        """测试 mean 属性"""
        self.analyzer.on_time_goes_by(datetime.datetime(2024, 1, 1))
        self.analyzer.add_data(100.0)
        self.analyzer.on_time_goes_by(datetime.datetime(2024, 1, 2))
        self.analyzer.add_data(200.0)
        self.assertEqual(self.analyzer.mean, Decimal("150.0"))

    def test_variance_property(self):
        """测试 variance 属性"""
        self.analyzer.on_time_goes_by(datetime.datetime(2024, 1, 1))
        self.analyzer.add_data(100.0)
        self.analyzer.on_time_goes_by(datetime.datetime(2024, 1, 2))
        self.analyzer.add_data(200.0)
        self.assertEqual(self.analyzer.variance, Decimal("5000.0"))

    def test_activate_method(self):
        """测试 activate 方法"""
        with self.assertRaises(NotImplementedError):
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY)

    def test_record_method(self):
        """测试 record 方法"""
        with self.assertRaises(NotImplementedError):
            self.analyzer.record(RECORDSTAGE_TYPES.NEWDAY)
