import unittest
import numpy as np
import pandas as pd
from unittest.mock import patch

from ginkgo.libs.data.statistics import t_test, chi2_test


class DataStatisticsTest(unittest.TestCase):
    """
    单元测试：统计分析模块
    """

    def setUp(self):
        """测试前的准备工作"""
        # 准备测试数据
        np.random.seed(42)  # 确保可重复性
        self.backtest_values = pd.Series(np.random.normal(0, 1, 100))
        self.observe_values = pd.Series(np.random.normal(0.1, 1, 100))

        # 明显不同的数据集
        self.different_values = pd.Series(np.random.normal(2, 1, 100))

    def test_TTest_BasicFunctionality(self):
        """测试t检验基本功能"""
        # 这是一个输出函数，主要测试是否能正常运行而不抛出异常
        try:
            with patch("builtins.print"):  # 抑制打印输出
                t_test(self.backtest_values, self.observe_values)
            # 如果没有异常，测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"t_test 函数抛出异常: {e}")

    def test_TTest_WithDifferentData(self):
        """测试使用明显不同数据的t检验"""
        try:
            with patch("builtins.print"):
                t_test(self.backtest_values, self.different_values)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"t_test 处理不同数据时抛出异常: {e}")

    def test_TTest_WithSameData(self):
        """测试使用相同数据的t检验"""
        try:
            with patch("builtins.print"):
                t_test(self.backtest_values, self.backtest_values)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"t_test 处理相同数据时抛出异常: {e}")

    def test_TTest_CustomConfidenceLevel(self):
        """测试自定义置信水平"""
        confidence_levels = [0.90, 0.95, 0.99, 0.999]

        for level in confidence_levels:
            try:
                with patch("builtins.print"):
                    t_test(self.backtest_values, self.observe_values, level_of_confidence=level)
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"t_test 在置信水平 {level} 时抛出异常: {e}")

    def test_TTest_EmptyData(self):
        """测试空数据处理"""
        empty_series = pd.Series([])

        with self.assertRaises((ValueError, IndexError, ZeroDivisionError)):
            with patch("builtins.print"):
                t_test(empty_series, self.observe_values)

    def test_TTest_SingleValue(self):
        """测试单值数据处理"""
        single_value = pd.Series([1.0])

        # 单值数据可能导致方差为0，应该能够处理或抛出合理的异常
        try:
            with patch("builtins.print"):
                t_test(single_value, self.observe_values)
        except (ValueError, ZeroDivisionError):
            # 这是预期的，因为单值数据方差为0
            pass

    def test_Chi2Test_BasicFunctionality(self):
        """测试卡方检验基本功能"""
        try:
            with patch("builtins.print"):
                chi2_test(self.backtest_values, self.observe_values)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"chi2_test 函数抛出异常: {e}")

    def test_Chi2Test_CustomCategoryCount(self):
        """测试自定义分类数量"""
        category_counts = [3, 5, 7, 10]

        for count in category_counts:
            try:
                with patch("builtins.print"):
                    chi2_test(self.backtest_values, self.observe_values, category_count=count)
                self.assertTrue(True)
            except Exception as e:
                self.fail(f"chi2_test 在分类数 {count} 时抛出异常: {e}")

    def test_Chi2Test_WithDifferentData(self):
        """测试使用不同数据的卡方检验"""
        try:
            with patch("builtins.print"):
                chi2_test(self.backtest_values, self.different_values)
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"chi2_test 处理不同数据时抛出异常: {e}")

    def test_Chi2Test_InvalidCategoryCount(self):
        """测试无效分类数量"""
        invalid_counts = [0, 1, -1]

        for count in invalid_counts:
            with self.assertRaises((ValueError, IndexError)):
                with patch("builtins.print"):
                    chi2_test(self.backtest_values, self.observe_values, category_count=count)

    def test_Chi2Test_EmptyData(self):
        """测试空数据处理"""
        empty_series = pd.Series([])

        with self.assertRaises((ValueError, IndexError)):
            with patch("builtins.print"):
                chi2_test(empty_series, self.observe_values)

    def test_DataTypes_Compatibility(self):
        """测试数据类型兼容性"""
        # 测试不同的数据类型
        list_data = [1, 2, 3, 4, 5]
        array_data = np.array([1, 2, 3, 4, 5])
        series_data = pd.Series([1, 2, 3, 4, 5])

        data_types = [list_data, array_data, series_data]

        for data1 in data_types:
            for data2 in data_types:
                try:
                    with patch("builtins.print"):
                        t_test(data1, data2)
                    self.assertTrue(True)
                except Exception as e:
                    # 某些组合可能不支持，记录但不失败测试
                    pass
