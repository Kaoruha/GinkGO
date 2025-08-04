import unittest
from unittest.mock import MagicMock
import pandas as pd
from enum import Enum

from ginkgo.libs.utils.display import GinkgoColor, chinese_count, pretty_repr, base_repr, fix_string_length


class TestEnum(Enum):
    """测试用的枚举类"""

    VALUE1 = 1
    VALUE2 = 2


class TestObject:
    """测试用的对象类"""

    def __init__(self):
        self.name = "test_object"
        self.value = 42
        self.data = pd.DataFrame({"A": [1, 2, 3]})
        self.portfolios = ["p1", "p2"]
        self.positions = {"pos1": 100, "pos2": 200}
        self.enum_value = TestEnum.VALUE1

    def method_example(self):
        """测试方法，应该被过滤掉"""
        pass


class UtilsDisplayTest(unittest.TestCase):
    """
    单元测试：显示工具模块
    """

    def test_GinkgoColor_Init(self):
        """测试GinkgoColor初始化"""
        color = GinkgoColor()
        self.assertIsNotNone(color)

        # 检查颜色常量
        self.assertTrue(hasattr(color, "HEADER"))
        self.assertTrue(hasattr(color, "OKBLUE"))
        self.assertTrue(hasattr(color, "OKGREEN"))
        self.assertTrue(hasattr(color, "WARNING"))
        self.assertTrue(hasattr(color, "FAIL"))
        self.assertTrue(hasattr(color, "ENDC"))

    def test_GinkgoColor_ColorMethods(self):
        """测试GinkgoColor颜色方法"""
        color = GinkgoColor()
        test_msg = "test message"

        # 测试各种颜色方法
        red_result = color.red(test_msg)
        self.assertIn(test_msg, red_result)
        self.assertIn(color.FAIL, red_result)
        self.assertIn(color.ENDC, red_result)

        green_result = color.green(test_msg)
        self.assertIn(test_msg, green_result)
        self.assertIn(color.OKGREEN, green_result)

        blue_result = color.blue(test_msg)
        self.assertIn(test_msg, blue_result)
        self.assertIn(color.OKBLUE, blue_result)

        yellow_result = color.yellow(test_msg)
        self.assertIn(test_msg, yellow_result)
        self.assertIn(color.WARNING, yellow_result)

        bold_result = color.bold(test_msg)
        self.assertIn(test_msg, bold_result)
        self.assertIn(color.BOLD, bold_result)

    def test_ChineseCount_Basic(self):
        """测试中文字符计数基本功能"""
        # 纯英文
        result = chinese_count("hello world")
        self.assertEqual(result, 0)

        # 纯中文
        result = chinese_count("你好世界")
        self.assertEqual(result, 4)

        # 中英混合
        result = chinese_count("hello 你好 world 世界")
        self.assertEqual(result, 4)

        # 空字符串
        result = chinese_count("")
        self.assertEqual(result, 0)

    def test_ChineseCount_SpecialCharacters(self):
        """测试中文字符计数特殊字符"""
        # 包含数字和符号
        result = chinese_count("测试123!@#")
        self.assertEqual(result, 2)

        # 包含其他Unicode字符
        result = chinese_count("测试😀:party_popper:")
        self.assertEqual(result, 2)

    def test_PrettyRepr_Basic(self):
        """测试格式化输出基本功能"""
        class_name = "TestClass"
        messages = ["Message 1", "Message 2", "测试消息"]

        result = pretty_repr(class_name, messages)

        # 检查基本结构
        self.assertIn(class_name, result)
        self.assertIn("Message 1", result)
        self.assertIn("Message 2", result)
        self.assertIn("测试消息", result)

        # 检查边框字符
        self.assertIn("-", result)
        self.assertIn("|", result)
        self.assertIn("+", result)

    def test_PrettyRepr_WithWidth(self):
        """测试指定宽度的格式化输出"""
        class_name = "Test"
        messages = ["Short", "A much longer message"]
        width = 50

        result = pretty_repr(class_name, messages, width)

        # 检查输出符合指定宽度
        lines = result.split("\n")
        for line in lines:
            if line.strip():  # 跳过空行
                # 移除ANSI转义序列来计算实际长度
                clean_line = line.replace("\033[0m", "").replace("\033[91m", "")
                self.assertLessEqual(len(clean_line), width + 5)  # 允许小的误差

    def test_PrettyRepr_EmptyMessages(self):
        """测试空消息列表"""
        result = pretty_repr("EmptyClass", [])
        self.assertIn("EmptyClass", result)
        self.assertIn("-", result)
        self.assertIn("+", result)

    def test_BaseRepr_BasicObject(self):
        """测试基础对象表示"""
        test_obj = TestObject()
        result = base_repr(test_obj, "TestObject")

        # 检查包含对象属性
        self.assertIn("TestObject", result)
        self.assertIn("NAME", result)
        self.assertIn("test_object", result)
        self.assertIn("VALUE", result)

        # 检查内存地址
        self.assertIn("MEM", result)
        self.assertIn(hex(id(test_obj)), result)

    def test_BaseRepr_SpecialAttributes(self):
        """测试特殊属性处理"""
        test_obj = TestObject()
        result = base_repr(test_obj, "TestObject")

        # DataFrame应该显示shape
        self.assertIn("DATA", result)
        self.assertIn("(3, 1)", result)  # DataFrame shape

        # 列表应该显示长度
        self.assertIn("PORTFOLIOS", result)
        self.assertIn("2", result)  # 列表长度

        # 字典应该显示长度
        self.assertIn("POSITIONS", result)
        self.assertIn("2", result)  # 字典长度

        # 枚举应该显示值
        self.assertIn("ENUM_VALUE", result)
        self.assertIn("1", result)  # 枚举值

    def test_BaseRepr_FilterMethods(self):
        """测试方法过滤"""
        test_obj = TestObject()
        result = base_repr(test_obj, "TestObject")

        # 方法应该被过滤掉
        self.assertNotIn("method_example", result.upper())
        self.assertNotIn("METHOD_EXAMPLE", result)

    def test_FixStringLength_Basic(self):
        """测试字符串长度固定基本功能"""
        # 短字符串应该被填充
        result = fix_string_length("hello", 10)
        self.assertEqual(len(result), 10)
        self.assertTrue(result.startswith("hello"))

        # 长字符串应该被截断
        result = fix_string_length("very long string", 5)
        self.assertEqual(len(result), 5)
        self.assertTrue(result.endswith("..."))

    def test_FixStringLength_ExactLength(self):
        """测试字符串恰好等于目标长度"""
        test_str = "exactly10!"
        result = fix_string_length(test_str, 10)
        self.assertEqual(result, test_str)
        self.assertEqual(len(result), 10)

    def test_FixStringLength_EmptyString(self):
        """测试空字符串处理"""
        result = fix_string_length("", 5)
        self.assertEqual(len(result), 5)
        self.assertEqual(result, "     ")  # 5个空格
