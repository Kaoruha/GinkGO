import unittest
import time
import math
from unittest.mock import patch, MagicMock

from ginkgo.libs.utils.common import (
    try_wait_counter,
    str2bool,
    time_logger,
    format_time_seconds,
    skip_if_ran,
    retry,
    RichProgress,
)


class UtilsCommonTest(unittest.TestCase):
    """
    单元测试：通用工具模块
    """

    def test_TryWaitCounter_BasicLogic(self):
        """测试重试等待计数器基本逻辑"""
        # 测试默认参数
        result = try_wait_counter(1)
        self.assertIsInstance(result, (int, float))
        self.assertGreaterEqual(result, 0.1)  # 最小值

        # 测试递增逻辑
        result1 = try_wait_counter(1)
        result2 = try_wait_counter(2)
        result3 = try_wait_counter(3)

        self.assertLessEqual(result1, result2)
        self.assertLessEqual(result2, result3)

    def test_TryWaitCounter_Bounds(self):
        """测试重试等待计数器边界条件"""
        # 测试最小值
        result = try_wait_counter(1, min=0.5, max=30)
        self.assertGreaterEqual(result, 0.5)

        # 测试最大值
        result = try_wait_counter(100, min=0.1, max=5)
        self.assertLessEqual(result, 5)

        # 测试零和负数
        result = try_wait_counter(0)
        self.assertGreaterEqual(result, 0.1)

    def test_Str2Bool_TrueValues(self):
        """测试字符串转布尔值 - True值"""
        true_values = ["true", "1", "t", "y", "yes", "yeah", "yup", "certainly", "uh-huh"]
        for value in true_values:
            self.assertTrue(str2bool(value))
            self.assertTrue(str2bool(value.upper()))  # 测试大写

        # 测试整数1
        self.assertTrue(str2bool(1))

    def test_Str2Bool_FalseValues(self):
        """测试字符串转布尔值 - False值"""
        false_values = ["false", "0", "f", "n", "no", "nope", "invalid"]
        for value in false_values:
            self.assertFalse(str2bool(value))

        # 测试整数0
        self.assertFalse(str2bool(0))

        # 测试其他整数
        self.assertFalse(str2bool(2))

    def test_TimeLogger_Decorator(self):
        """测试时间记录装饰器"""

        @time_logger
        def sample_function():
            time.sleep(0.01)  # 短暂延时
            return "completed"

        with patch("ginkgo.libs.utils.common.console") as mock_console:
            result = sample_function()
            self.assertEqual(result, "completed")
            # 验证console.print被调用过（记录时间）
            mock_console.print.assert_called()

    def test_FormatTimeSeconds_Basic(self):
        """测试时间格式化基本功能"""
        # 测试小于1分钟
        result = format_time_seconds(30)
        self.assertIn("30", result)
        self.assertIn("s", result)

        # 测试小于1小时
        result = format_time_seconds(90)  # 1分30秒
        self.assertIn("1", result)
        self.assertIn("m", result)

        # 测试超过1小时
        result = format_time_seconds(3661)  # 1小时1分1秒
        self.assertIn("1", result)
        self.assertIn("h", result)

    # def test_SkipIfRan_Decorator(self):
    #     """测试跳过重复运行装饰器"""
    #     call_count = 0

    #     @skip_if_ran
    #     def sample_function():
    #         global call_count
    #         call_count += 1
    #         return "executed"

    #     # 第一次调用应该执行
    #     result1 = sample_function()
    #     self.assertEqual(call_count, 1)
    #     self.assertEqual(result1, "executed")

    #     import pdb

    #     pdb.set_trace()

    #     # 第二次调用应该被跳过
    #     result2 = sample_function()
    #     self.assertEqual(call_count, 1)  # 调用次数不变
    #     self.assertEqual(result2, "executed")  # 返回缓存结果

    def test_Retry_Decorator_Success(self):
        """测试重试装饰器 - 成功情况"""
        call_count = 0

        @retry(max_try=3)
        def sample_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = sample_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 1)

    def test_Retry_Decorator_WithFailure(self):
        """测试重试装饰器 - 失败重试情况"""
        call_count = 0

        @retry(max_try=3)
        def sample_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Test error")
            return "success"

        result = sample_function()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)

    def test_Retry_Decorator_MaxTryExceeded(self):
        """测试重试装饰器 - 超过最大重试次数"""
        call_count = 0

        @retry(max_try=2)
        def sample_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        try:
            with self.assertRaises(ValueError):
                sample_function()
        except Exception as e:
            print(e)
        finally:
            self.assertEqual(call_count, 2)

    def test_RichProgress_Init(self):
        """测试RichProgress初始化"""
        progress = RichProgress()
        self.assertIsNotNone(progress)

    def test_RichProgress_Context_Manager(self):
        """测试RichProgress上下文管理器"""
        with RichProgress() as progress:
            self.assertIsNotNone(progress)
            # 在上下文中应该可以正常使用
