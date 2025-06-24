import unittest
import datetime
import numpy as np

from ginkgo.libs.data.normalize import datetime_normalize


class DataNormalizeTest(unittest.TestCase):
    """
    单元测试：数据标准化模块
    """

    def test_DatetimeNormalize_FromDatetime(self):
        """测试从datetime对象转换"""
        dt = datetime.datetime(2024, 1, 1, 12, 30, 45)
        result = datetime_normalize(dt)
        self.assertEqual(result, dt)

    def test_DatetimeNormalize_FromDate(self):
        """测试从date对象转换"""
        d = datetime.date(2024, 1, 1)
        result = datetime_normalize(d)
        expected = datetime.datetime(2024, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_DatetimeNormalize_FromIntString(self):
        """测试从整数格式字符串转换"""
        date_str = "20240101"
        result = datetime_normalize(date_str)
        expected = datetime.datetime(2024, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_DatetimeNormalize_FromInt(self):
        """测试从整数转换"""
        date_int = 20240101
        result = datetime_normalize(date_int)
        expected = datetime.datetime(2024, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_DatetimeNormalize_FromFormattedString(self):
        """测试从格式化字符串转换"""
        date_str = "2024-01-01"
        result = datetime_normalize(date_str)
        expected = datetime.datetime(2024, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

    def test_DatetimeNormalize_FromDatetimeString(self):
        """测试从完整datetime字符串转换"""
        datetime_str = "2024-01-01 12:30:45"
        result = datetime_normalize(datetime_str)
        expected = datetime.datetime(2024, 1, 1, 12, 30, 45)
        self.assertEqual(result, expected)

    def test_DatetimeNormalize_FromNumpyDatetime64(self):
        """测试从numpy datetime64转换"""
        np_dt = np.datetime64("2024-01-01T14:30:45")
        result = datetime_normalize(np_dt)
        expected = datetime.datetime(2024, 1, 1, 14, 30, 45)
        self.assertEqual(result, expected)

    def test_DatetimeNormalize_FromNone(self):
        """测试None值处理"""
        result = datetime_normalize(None)
        self.assertIsNone(result)

    def test_DatetimeNormalize_InvalidFormat(self):
        """测试无效格式处理"""
        with self.assertRaises(ValueError):
            datetime_normalize("invalid_date_format")
