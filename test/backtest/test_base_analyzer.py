import unittest
import pandas as pd
import numpy as np
import time
import tempfile
import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, Mock

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
        # 检查新的内部数据结构
        self.assertTrue(hasattr(analyzer, "_timestamps"))
        self.assertTrue(hasattr(analyzer, "_values"))
        self.assertTrue(hasattr(analyzer, "_index_map"))
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

    # =========================
    # 新增：NumPy+HashMap存储架构测试
    # =========================
    
    def test_numpy_storage_structure(self):
        """测试新的NumPy数组+HashMap存储结构"""
        # 检查初始容量和数据结构
        self.assertEqual(self.analyzer._capacity, 1000)
        self.assertEqual(self.analyzer._size, 0)
        self.assertIsInstance(self.analyzer._timestamps, np.ndarray)
        self.assertIsInstance(self.analyzer._values, np.ndarray)
        self.assertIsInstance(self.analyzer._index_map, dict)
        self.assertEqual(len(self.analyzer._index_map), 0)
    
    def test_o1_add_data_performance(self):
        """测试O(1)数据添加性能"""
        # 添加大量数据测试性能
        start_time = time.perf_counter()
        
        for i in range(100):
            test_time = self.test_time + timedelta(minutes=i)
            self.analyzer.on_time_goes_by(test_time)
            self.analyzer.add_data(100.0 + i)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # 验证数据正确性
        self.assertEqual(self.analyzer._size, 100)
        self.assertEqual(len(self.analyzer._index_map), 100)
        
        # 性能应该是线性的（接近O(1)每次操作）
        avg_time_per_op = duration / 100
        self.assertLess(avg_time_per_op, 0.001)  # 每次操作应小于1ms
    
    def test_o1_get_data_performance(self):
        """测试O(1)数据查询性能"""
        # 准备测试数据
        test_times = []
        for i in range(100):
            test_time = self.test_time + timedelta(minutes=i)
            test_times.append(test_time)
            self.analyzer.on_time_goes_by(test_time)
            self.analyzer.add_data(100.0 + i)
        
        # 测试查询性能
        start_time = time.perf_counter()
        
        for test_time in test_times:
            result = self.analyzer.get_data(test_time)
            self.assertIsNotNone(result)
        
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        # 每次查询应该非常快（O(1)）
        avg_query_time = duration / 100
        self.assertLess(avg_query_time, 0.0001)  # 每次查询应小于0.1ms
    
    def test_data_update_functionality(self):
        """测试数据更新功能"""
        # 添加初始数据
        self.analyzer.add_data(100.0)
        initial_size = self.analyzer._size
        
        # 更新同一时间的数据
        self.analyzer.add_data(200.0)
        
        # 验证大小没有增加（更新而非新增）
        self.assertEqual(self.analyzer._size, initial_size)
        
        # 验证值已更新
        result = self.analyzer.get_data(self.test_time)
        self.assertEqual(result, Decimal("200.0"))
    
    def test_dynamic_resize_functionality(self):
        """测试动态扩容功能"""
        initial_capacity = self.analyzer._capacity
        
        # 添加超过初始容量的数据
        for i in range(initial_capacity + 10):
            test_time = self.test_time + timedelta(minutes=i)
            self.analyzer.on_time_goes_by(test_time)
            self.analyzer.add_data(float(i))
        
        # 验证已扩容
        self.assertGreater(self.analyzer._capacity, initial_capacity)
        self.assertEqual(self.analyzer._size, initial_capacity + 10)
        
        # 验证数据完整性
        for i in range(initial_capacity + 10):
            test_time = self.test_time + timedelta(minutes=i)
            result = self.analyzer.get_data(test_time)
            self.assertEqual(result, Decimal(str(float(i))))
    
    def test_dataframe_backward_compatibility(self):
        """测试DataFrame向后兼容性"""
        # 添加测试数据
        test_data = [(self.test_time + timedelta(minutes=i), 100.0 + i) for i in range(5)]
        
        for test_time, value in test_data:
            self.analyzer.on_time_goes_by(test_time)
            self.analyzer.add_data(value)
        
        # 获取DataFrame
        df = self.analyzer.data
        
        # 验证DataFrame格式
        self.assertIsInstance(df, pd.DataFrame)
        self.assertIn("timestamp", df.columns)
        self.assertIn("value", df.columns)
        self.assertEqual(len(df), 5)
        
        # 验证数据正确性
        for i, (_, row) in enumerate(df.iterrows()):
            expected_value = 100.0 + i
            self.assertAlmostEqual(row["value"], expected_value, places=2)
    
    # =========================
    # 新增：性能监控功能测试
    # =========================
    
    def test_performance_monitoring_activation(self):
        """测试激活操作的性能监控"""
        # 创建可测试的分析器实现
        class TestableAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                time.sleep(0.001)  # 模拟处理时间
                return True
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer = TestableAnalyzer("perf_test")
        analyzer.on_time_goes_by(self.test_time)
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"worth": 10000}
        
        # 执行激活操作
        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证性能统计
        perf_summary = analyzer.performance_summary
        self.assertEqual(perf_summary["activation_count"], 2)
        self.assertGreater(perf_summary["avg_activation_time"], 0)
        self.assertGreater(perf_summary["total_time"], 0)
    
    def test_performance_monitoring_record(self):
        """测试记录操作的性能监控"""
        class TestableAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                time.sleep(0.001)  # 模拟处理时间
                return True
        
        analyzer = TestableAnalyzer("record_perf_test")
        analyzer.on_time_goes_by(self.test_time)
        analyzer.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"worth": 10000}
        
        # 执行记录操作
        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证性能统计
        perf_summary = analyzer.performance_summary
        self.assertEqual(perf_summary["record_count"], 2)
        self.assertGreater(perf_summary["avg_record_time"], 0)
    
    def test_global_performance_report(self):
        """测试全局性能报告"""
        # 清除之前的统计
        BaseAnalyzer._execution_stats.clear()
        BaseAnalyzer._performance_log.clear()
        
        class TestableAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                time.sleep(0.001)
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        # 创建多个分析器实例
        analyzers = [TestableAnalyzer(f"global_test_{i}") for i in range(3)]
        
        for analyzer in analyzers:
            analyzer.on_time_goes_by(self.test_time)
            analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
            
            portfolio_info = {"worth": 10000}
            analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 获取全局报告
        global_report = BaseAnalyzer.get_global_performance_report()
        
        # 验证全局统计
        self.assertGreater(len(global_report), 0)
        for key, stats in global_report.items():
            self.assertIn("call_count", stats)
            self.assertIn("avg_duration", stats)
            self.assertGreater(stats["call_count"], 0)
    
    def test_performance_log_export(self):
        """测试性能日志导出"""
        class TestableAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer = TestableAnalyzer("export_test")
        analyzer.on_time_goes_by(self.test_time)
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        # 执行一些操作生成日志
        portfolio_info = {"worth": 10000}
        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 导出到临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            BaseAnalyzer.export_performance_log(tmp_file.name)
            
            # 验证文件内容
            with open(tmp_file.name, 'r') as f:
                log_data = json.load(f)
                self.assertIsInstance(log_data, list)
    
    # =========================
    # 新增：错误处理功能测试
    # =========================
    
    def test_error_handling_in_activation(self):
        """测试激活过程中的错误处理"""
        class ErrorAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                raise ValueError("Test activation error")
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer = ErrorAnalyzer("error_test")
        analyzer.on_time_goes_by(self.test_time)
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"worth": 10000}
        
        # 验证错误被正确抛出并处理
        with self.assertRaises(ValueError):
            analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证错误统计
        error_summary = analyzer.error_summary
        self.assertEqual(error_summary["total_errors"], 1)
        self.assertIsNotNone(error_summary["last_error"])
        self.assertEqual(len(error_summary["recent_errors"]), 1)
        
        # 验证错误详情
        recent_error = error_summary["recent_errors"][0]
        self.assertEqual(recent_error["method"], "activate")
        self.assertEqual(recent_error["error_type"], "ValueError")
        self.assertIn("Test activation error", recent_error["error_message"])
    
    def test_error_handling_in_record(self):
        """测试记录过程中的错误处理"""
        class ErrorAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                raise RuntimeError("Test record error")
        
        analyzer = ErrorAnalyzer("record_error_test")
        analyzer.on_time_goes_by(self.test_time)
        analyzer.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"worth": 10000}
        
        # 验证错误被正确抛出并处理
        with self.assertRaises(RuntimeError):
            analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证错误统计
        error_summary = analyzer.error_summary
        self.assertEqual(error_summary["total_errors"], 1)
        self.assertIsNotNone(error_summary["last_error"])
    
    def test_error_log_accumulation(self):
        """测试错误日志累积"""
        class MultiErrorAnalyzer(BaseAnalyzer):
            def __init__(self, name):
                super().__init__(name)
                self.error_count = 0
            
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                self.error_count += 1
                raise Exception(f"Error #{self.error_count}")
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass
        
        analyzer = MultiErrorAnalyzer("multi_error_test")
        analyzer.on_time_goes_by(self.test_time)
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        portfolio_info = {"worth": 10000}
        
        # 产生多个错误
        for i in range(3):
            with self.assertRaises(Exception):
                analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        
        # 验证错误累积
        error_summary = analyzer.error_summary
        self.assertEqual(error_summary["total_errors"], 3)
        self.assertEqual(len(error_summary["recent_errors"]), 3)
    
    # =========================
    # 新增：新属性和方法测试
    # =========================
    
    def test_current_value_property(self):
        """测试current_value属性"""
        # 空数据时应返回0
        self.assertEqual(self.analyzer.current_value, 0.0)
        
        # 添加数据后应返回最新值
        self.analyzer.add_data(123.45)
        self.assertEqual(self.analyzer.current_value, 123.45)
        
        # 添加更多数据，应返回最新的
        next_time = self.test_time + timedelta(minutes=1)
        self.analyzer.on_time_goes_by(next_time)
        self.analyzer.add_data(678.90)
        self.assertEqual(self.analyzer.current_value, 678.90)
    
    def test_enhanced_statistical_methods(self):
        """测试增强的统计方法（基于NumPy）"""
        # 添加测试数据
        test_values = [100.0, 110.0, 90.0, 120.0, 80.0]
        
        for i, value in enumerate(test_values):
            test_time = self.test_time + timedelta(minutes=i)
            self.analyzer.on_time_goes_by(test_time)
            self.analyzer.add_data(value)
        
        # 验证均值计算（应基于NumPy）
        expected_mean = np.mean(test_values)
        actual_mean = float(self.analyzer.mean)
        self.assertAlmostEqual(actual_mean, expected_mean, places=6)
        
        # 验证方差计算（样本方差，ddof=1）
        expected_variance = np.var(test_values, ddof=1)
        actual_variance = float(self.analyzer.variance)
        self.assertAlmostEqual(actual_variance, expected_variance, places=6)
    
    def test_stage_filtering_logic(self):
        """测试阶段过滤逻辑的正确性"""
        class CountingAnalyzer(BaseAnalyzer):
            def __init__(self, name):
                super().__init__(name)
                self.activate_calls = 0
                self.record_calls = 0
            
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                self.activate_calls += 1
            
            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                self.record_calls += 1
        
        analyzer = CountingAnalyzer("stage_test")
        analyzer.on_time_goes_by(self.test_time)
        
        # 设置只在SIGNALGENERATION阶段激活
        analyzer.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        # 设置只在ORDERFILLED阶段记录
        analyzer.set_record_stage(RECORDSTAGE_TYPES.ORDERFILLED)
        
        portfolio_info = {"worth": 10000}
        
        # 测试不同阶段的调用
        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)  # 不应激活
        analyzer.activate(RECORDSTAGE_TYPES.SIGNALGENERATION, portfolio_info)  # 应激活
        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)  # 不应记录
        analyzer.record(RECORDSTAGE_TYPES.ORDERFILLED, portfolio_info)  # 应记录
        
        # 验证调用次数
        self.assertEqual(analyzer.activate_calls, 1)
        self.assertEqual(analyzer.record_calls, 1)
    
    @patch('ginkgo.backtest.analysis.analyzers.base_analyzer.container')
    def test_add_record_database_integration(self, mock_container):
        """测试add_record数据库集成"""
        # 设置mock
        mock_crud = Mock()
        mock_container.cruds.analyzer_record.return_value = mock_crud
        
        # 设置分析器属性
        self.analyzer._portfolio_id = "test_portfolio"
        self.analyzer._engine_id = "test_engine"
        self.analyzer._analyzer_id = "test_analyzer"
        
        # 添加数据并调用add_record
        self.analyzer.add_data(100.0)
        self.analyzer.add_record()
        
        # 验证数据库调用
        mock_crud.create.assert_called_once()
        call_args = mock_crud.create.call_args[1]
        self.assertEqual(call_args["portfolio_id"], "test_portfolio")
        self.assertEqual(call_args["engine_id"], "test_engine")
        self.assertEqual(call_args["analyzer_id"], "test_analyzer")
        self.assertEqual(call_args["value"], Decimal("100.0"))
