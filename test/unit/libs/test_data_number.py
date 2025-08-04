import unittest
from decimal import Decimal
import pandas as pd
import numpy as np

from ginkgo.libs.data.number import Number, to_decimal


class DataNumberTest(unittest.TestCase):
    """
    单元测试：数值处理模块
    """

    def test_ToDecimal_FromInt(self):
        """测试从整数转换为Decimal"""
        result = to_decimal(100)
        self.assertEqual(result, Decimal("100"))
        self.assertIsInstance(result, Decimal)

    def test_ToDecimal_FromFloat(self):
        """测试从浮点数转换为Decimal"""
        result = to_decimal(100.55)
        self.assertEqual(result, Decimal("100.55"))
        self.assertIsInstance(result, Decimal)

    def test_ToDecimal_FromString(self):
        """测试从字符串转换为Decimal"""
        result = to_decimal("100.55")
        self.assertEqual(result, Decimal("100.55"))
        self.assertIsInstance(result, Decimal)

    def test_ToDecimal_FromDecimal(self):
        """测试从Decimal转换为Decimal"""
        original = Decimal("100.55")
        result = to_decimal(original)
        self.assertEqual(result, original)
        self.assertIsInstance(result, Decimal)

    def test_ToDecimal_FromNumpy(self):
        """测试从numpy数值转换为Decimal"""
        np_int = np.int64(100)
        result = to_decimal(np_int)
        self.assertEqual(result, Decimal("100"))

        np_float = np.float64(100.55)
        result = to_decimal(np_float)
        self.assertEqual(result, Decimal("100.55"))

    def test_ToDecimal_FromPandasSeries(self):
        """测试从pandas Series转换为Decimal"""
        series = pd.Series([100.55])
        result = to_decimal(series.iloc[0])
        self.assertEqual(result, Decimal("100.55"))

    def test_ToDecimal_InvalidInput(self):
        """测试无效输入处理"""
        with self.assertRaises((ValueError, TypeError)):
            to_decimal("invalid_number")

        with self.assertRaises((ValueError, TypeError)):
            to_decimal(None)

    def test_Number_TypeAlias(self):
        """测试Number类型别名"""
        # Number应该是一个类型联合，包含常用的数值类型
        # 这里主要测试Number的定义是否存在
        self.assertTrue(hasattr(Number, "__args__") or hasattr(Number, "__union__"))
