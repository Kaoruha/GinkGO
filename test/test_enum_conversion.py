import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from ginkgo.enums import (
    DIRECTION_TYPES, TICKDIRECTION_TYPES, ORDER_TYPES, 
    ORDERSTATUS_TYPES, SOURCE_TYPES, FILE_TYPES, 
    FREQUENCY_TYPES, CURRENCY_TYPES
)


class EnumConversionTest(unittest.TestCase):
    """
    测试枚举转换功能
    验证 EnumBase 的 from_int(), to_int(), validate_input() 方法
    """

    def test_enum_from_int_conversion(self):
        """测试从整数转换为枚举"""
        # 测试有效的整数转换
        self.assertEqual(DIRECTION_TYPES.from_int(1), DIRECTION_TYPES.LONG)
        self.assertEqual(DIRECTION_TYPES.from_int(-1), DIRECTION_TYPES.SHORT)
        self.assertEqual(TICKDIRECTION_TYPES.from_int(1), TICKDIRECTION_TYPES.ACTIVEBUY)
        self.assertEqual(SOURCE_TYPES.from_int(7), SOURCE_TYPES.TUSHARE)
        
        # 测试无效的整数转换
        self.assertIsNone(DIRECTION_TYPES.from_int(999))
        self.assertIsNone(DIRECTION_TYPES.from_int("invalid"))
        
        # 测试None处理
        self.assertIsNone(DIRECTION_TYPES.from_int(None))
        
        # 测试已经是枚举的情况
        self.assertEqual(DIRECTION_TYPES.from_int(DIRECTION_TYPES.LONG), DIRECTION_TYPES.LONG)

    def test_enum_to_int_conversion(self):
        """测试从枚举转换为整数"""
        self.assertEqual(DIRECTION_TYPES.LONG.to_int(), 1)
        self.assertEqual(DIRECTION_TYPES.SHORT.to_int(), -1)
        self.assertEqual(TICKDIRECTION_TYPES.ACTIVEBUY.to_int(), 1)
        self.assertEqual(TICKDIRECTION_TYPES.ACTIVESELL.to_int(), 2)
        self.assertEqual(SOURCE_TYPES.TUSHARE.to_int(), 7)
        self.assertEqual(SOURCE_TYPES.VOID.to_int(), -1)

    def test_enum_validate_input(self):
        """测试输入验证和转换"""
        # 测试枚举输入 - 应该返回枚举的值
        self.assertEqual(DIRECTION_TYPES.validate_input(DIRECTION_TYPES.LONG), 1)
        self.assertEqual(DIRECTION_TYPES.validate_input(DIRECTION_TYPES.SHORT), -1)
        
        # 测试有效整数输入 - 应该返回整数本身
        self.assertEqual(DIRECTION_TYPES.validate_input(1), 1)
        self.assertEqual(DIRECTION_TYPES.validate_input(-1), -1)
        
        # 测试无效整数输入 - 应该返回None
        self.assertIsNone(DIRECTION_TYPES.validate_input(999))
        self.assertIsNone(DIRECTION_TYPES.validate_input(-999))
        
        # 测试None输入
        self.assertIsNone(DIRECTION_TYPES.validate_input(None))
        
        # 测试其他无效类型
        self.assertIsNone(DIRECTION_TYPES.validate_input("invalid"))
        self.assertIsNone(DIRECTION_TYPES.validate_input([1, 2, 3]))

    def test_all_enum_types_have_void_value(self):
        """测试所有枚举类型都有VOID = -1值"""
        enum_classes = [
            DIRECTION_TYPES, TICKDIRECTION_TYPES, ORDER_TYPES,
            ORDERSTATUS_TYPES, SOURCE_TYPES, FILE_TYPES,
            FREQUENCY_TYPES, CURRENCY_TYPES
        ]
        
        for enum_class in enum_classes:
            with self.subTest(enum_class=enum_class.__name__):
                self.assertTrue(hasattr(enum_class, 'VOID'), 
                               f"{enum_class.__name__} should have VOID value")
                self.assertEqual(enum_class.VOID.value, -1,
                               f"{enum_class.__name__}.VOID should equal -1")

    def test_database_storage_pattern(self):
        """测试数据库存储模式 - 枚举输入转换为整数存储"""
        # 模拟数据库存储逻辑
        def simulate_db_store(enum_value):
            return DIRECTION_TYPES.validate_input(enum_value) or -1
        
        # 测试枚举输入
        stored_value = simulate_db_store(DIRECTION_TYPES.LONG)
        self.assertEqual(stored_value, 1)
        
        # 测试整数输入
        stored_value = simulate_db_store(1)
        self.assertEqual(stored_value, 1)
        
        # 测试无效输入的fallback
        stored_value = simulate_db_store("invalid")
        self.assertEqual(stored_value, -1)

    def test_business_layer_retrieval_pattern(self):
        """测试业务层检索模式 - 整数转换回枚举"""
        # 模拟从数据库获取整数值，转换为枚举给业务层
        db_stored_values = [1, -1, 0, 999]  # 包括无效值
        
        for db_value in db_stored_values:
            with self.subTest(db_value=db_value):
                business_enum = DIRECTION_TYPES.from_int(db_value)
                if db_value in [1, -1, 0]:
                    self.assertIsNotNone(business_enum)
                    self.assertIsInstance(business_enum, DIRECTION_TYPES)
                else:
                    self.assertIsNone(business_enum)


if __name__ == "__main__":
    unittest.main()