import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.backtest.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import GRAPHY_TYPES, RECORDSTAGE_TYPES


class AnalyzersTest(unittest.TestCase):
    """
    测试分析器模块 - 仅测试BaseAnalyzer
    """

    def setUp(self):
        """初始化测试用的BaseAnalyzer实例"""
        self.analyzer = BaseAnalyzer("test_analyzer")
        self.test_time = datetime(2024, 1, 1, 10, 0, 0)
        self.analyzer.on_time_goes_by(self.test_time)

    def test_BaseAnalyzer_Init(self):
        """测试基础分析器初始化"""
        analyzer = BaseAnalyzer("test_analyzer")
        self.assertIsNotNone(analyzer)

        # 检查基本属性
        self.assertTrue(hasattr(analyzer, "_name"))
        self.assertEqual(analyzer._name, "test_analyzer")
        self.assertEqual(analyzer._active_stage, [])
        self.assertEqual(analyzer._record_stage, RECORDSTAGE_TYPES.NEWDAY)
        self.assertEqual(analyzer._analyzer_id, "")
        self.assertEqual(analyzer._portfolio_id, "")
        self.assertEqual(analyzer._graph_type, GRAPHY_TYPES.OTHER)
        self.assertIsInstance(analyzer.data, pd.DataFrame)

    def test_data_property(self):
        """测试data属性"""
        data = self.analyzer.data
        self.assertIsInstance(data, pd.DataFrame)
        self.assertIn("timestamp", data.columns)
        self.assertIn("value", data.columns)

    def test_set_graph_type(self):
        """测试设置图表类型"""
        self.analyzer.set_graph_type(GRAPHY_TYPES.BAR)
        self.assertEqual(self.analyzer._graph_type, GRAPHY_TYPES.BAR)

    def test_analyzer_id_property(self):
        """测试analyzer_id属性"""
        self.assertEqual(self.analyzer.analyzer_id, "")

        # 测试设置analyzer_id
        new_id = "test_analyzer_001"
        result = self.analyzer.set_analyzer_id(new_id)
        self.assertEqual(self.analyzer.analyzer_id, new_id)
        self.assertEqual(result, new_id)

    def test_portfolio_id_property(self):
        """测试portfolio_id属性"""
        self.assertEqual(self.analyzer.portfolio_id, "")

        # 测试设置portfolio_id
        new_portfolio_id = "test_portfolio_001"
        self.analyzer.set_portfolio_id(new_portfolio_id)
        self.assertEqual(self.analyzer.portfolio_id, new_portfolio_id)

    def test_active_stage_property(self):
        """测试active_stage属性"""
        self.assertEqual(self.analyzer.active_stage, [])

        # 测试添加active_stage
        self.analyzer.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        self.assertIn(RECORDSTAGE_TYPES.SIGNALGENERATION, self.analyzer.active_stage)

        # 测试重复添加不会重复
        self.analyzer.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        self.assertEqual(len(self.analyzer.active_stage), 1)

    def test_record_stage_property(self):
        """测试record_stage属性"""
        self.assertEqual(self.analyzer.record_stage, RECORDSTAGE_TYPES.NEWDAY)

        # 测试设置record_stage
        self.analyzer.set_record_stage(RECORDSTAGE_TYPES.ORDERFILLED)
        self.assertEqual(self.analyzer.record_stage, RECORDSTAGE_TYPES.ORDERFILLED)

    def test_add_data_and_get_data(self):
        """测试添加和获取数据"""
        # 添加数据
        test_value = Decimal("100.5")
        self.analyzer.add_data(test_value)

        # 获取数据
        retrieved_value = self.analyzer.get_data(self.test_time)
        self.assertEqual(retrieved_value, test_value)

        # 测试更新数据
        new_value = Decimal("150.75")
        self.analyzer.add_data(new_value)
        retrieved_value = self.analyzer.get_data(self.test_time)
        self.assertEqual(retrieved_value, new_value)

        # 测试获取不存在的时间数据
        future_time = self.test_time + timedelta(days=1)
        result = self.analyzer.get_data(future_time)
        self.assertIsNone(result)

    def test_mean_property(self):
        """测试mean属性"""
        # 空数据时的均值
        self.assertEqual(self.analyzer.mean, Decimal("0.0"))

        # 添加数据后的均值
        self.analyzer.add_data(100.0)
        self.analyzer.on_time_goes_by(self.test_time + timedelta(days=1))
        self.analyzer.add_data(200.0)

        expected_mean = Decimal("150.0")
        self.assertEqual(self.analyzer.mean, expected_mean)

    def test_variance_property(self):
        """测试variance属性"""
        # 空数据时的方差
        self.assertEqual(self.analyzer.variance, Decimal("0.0"))

        # 添加数据后的方差
        self.analyzer.add_data(100.0)
        self.analyzer.on_time_goes_by(self.test_time + timedelta(days=1))
        self.analyzer.add_data(200.0)

        # 计算期望方差: ((100-150)^2 + (200-150)^2) / 2 = (2500 + 2500) / 2 = 2500
        # 但pandas默认计算样本方差 (n-1), 所以是 5000 / 1 = 5000
        expected_variance = Decimal("5000.0")
        self.assertEqual(self.analyzer.variance, expected_variance)

    def test_activate_not_implemented(self):
        """测试activate方法抛出NotImplementedError"""
        # 添加活跃阶段，使其能进入_do_activate方法
        self.analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"cash": 10000, "positions": {}, "worth": 10000}
        with self.assertRaises(NotImplementedError):
            self.analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

    def test_record_not_implemented(self):
        """测试record方法抛出NotImplementedError"""
        # 设置记录阶段为NEWDAY，使其能进入_do_record方法
        self.analyzer.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"cash": 10000, "positions": {}, "worth": 10000}
        with self.assertRaises(NotImplementedError):
            self.analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
