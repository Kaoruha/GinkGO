"""
CRUD Utils单元测试 - 不使用Mock版本

遵循项目测试设计原则：
- 不使用mock对象，完全使用真实逻辑
- 专注于验证核心逻辑
- 测试抽象方法强制执行和类属性行为
- 验证错误处理和边缘情况
- 确保线程安全性

测试get_crud工厂函数的功能，该函数取代了原来的CrudManager。
"""

import unittest
import sys
import os
import threading
import time
from typing import Any, List

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    from ginkgo.data.utils import get_crud, get_available_crud_names, clear_crud_cache, _camel_to_snake
    from ginkgo.data.crud.base_crud import BaseCRUD
except ImportError as e:
    print(f"Import error: {e}")
    get_crud = None
    get_available_crud_names = None
    clear_crud_cache = None
    _camel_to_snake = None
    BaseCRUD = None


class CrudUtilsBasicTest(unittest.TestCase):
    """CRUD工具函数基本功能测试"""

    @classmethod
    def setUpClass(cls):
        if get_crud is None:
            raise AssertionError("get_crud function not available")

    def setUp(self):
        """每个测试前清理缓存"""
        clear_crud_cache()

    def test_get_crud_basic_functionality(self):
        """测试get_crud基本功能"""
        # 测试获取一个标准CRUD
        bar_crud = get_crud('bar')
        self.assertIsNotNone(bar_crud)
        self.assertTrue(isinstance(bar_crud, BaseCRUD))
        
        # 测试获取另一个CRUD
        signal_crud = get_crud('signal')
        self.assertIsNotNone(signal_crud)
        self.assertTrue(isinstance(signal_crud, BaseCRUD))
        
        # 验证不同的CRUD是不同的实例
        self.assertIsNot(bar_crud, signal_crud)

    def test_crud_caching_mechanism(self):
        """测试CRUD实例缓存机制"""
        # 第一次获取
        bar_crud1 = get_crud('bar')
        
        # 第二次获取应该返回同一个实例
        bar_crud2 = get_crud('bar')
        
        # 验证是同一个对象
        self.assertIs(bar_crud1, bar_crud2)
        
        # 测试多个不同CRUD的缓存
        signal_crud1 = get_crud('signal')
        signal_crud2 = get_crud('signal')
        
        self.assertIs(signal_crud1, signal_crud2)
        self.assertIsNot(bar_crud1, signal_crud1)

    def test_invalid_crud_name_error(self):
        """测试无效CRUD名称的错误处理"""
        with self.assertRaises(AttributeError) as context:
            get_crud('nonexistent_crud')
            
        error_message = str(context.exception)
        
        # 验证错误消息包含有用信息
        self.assertIn("not found in the ginkgo.data.crud module", error_message)
        self.assertIn("Available CRUDs:", error_message)

    def test_get_available_crud_names(self):
        """测试获取可用CRUD列表"""
        available_cruds = get_available_crud_names()
        
        # 验证返回的是列表
        self.assertIsInstance(available_cruds, list)
        
        # 验证列表不为空
        self.assertGreater(len(available_cruds), 0)
        
        # 验证包含一些预期的CRUD
        expected_cruds = ['bar', 'signal', 'order', 'engine', 'portfolio']
        for expected_crud in expected_cruds:
            self.assertIn(expected_crud, available_cruds, 
                         f"Expected CRUD '{expected_crud}' should be in available list")
        
        # 验证列表是排序的
        self.assertEqual(available_cruds, sorted(available_cruds))

    def test_clear_crud_cache(self):
        """测试清理CRUD缓存功能"""
        # 创建一些CRUD实例
        bar_crud1 = get_crud('bar')
        signal_crud1 = get_crud('signal')
        
        # 清理缓存
        clear_crud_cache()
        
        # 重新获取应该创建新实例
        bar_crud2 = get_crud('bar')
        signal_crud2 = get_crud('signal')
        
        # 验证是不同的实例（缓存已清理）
        self.assertIsNot(bar_crud1, bar_crud2)
        self.assertIsNot(signal_crud1, signal_crud2)


class CrudUtilsThreadSafetyTest(unittest.TestCase):
    """CRUD工具函数线程安全测试"""

    def setUp(self):
        """每个测试前清理缓存"""
        clear_crud_cache()

    def test_thread_safety(self):
        """测试多线程环境下的线程安全性"""
        instances = {}
        errors = []

        def create_crud_instance(crud_name, thread_id):
            try:
                instance = get_crud(crud_name)
                instances[thread_id] = instance
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时获取同一个CRUD
        threads = []
        thread_count = 10
        
        for i in range(thread_count):
            thread = threading.Thread(
                target=create_crud_instance, 
                args=('bar', i)
            )
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # 验证所有线程获得了同一个实例
        first_instance = instances[0]
        for thread_id, instance in instances.items():
            self.assertIs(instance, first_instance, 
                         f"Thread {thread_id} got different instance")

    def test_concurrent_different_cruds(self):
        """测试并发访问不同CRUD的线程安全性"""
        instances = {}
        errors = []
        crud_names = ['bar', 'signal', 'order', 'engine']

        def create_crud_instance(crud_name, thread_id):
            try:
                instance = get_crud(crud_name)
                instances[f"{crud_name}_{thread_id}"] = instance
            except Exception as e:
                errors.append(e)

        threads = []
        
        # 为每种CRUD类型创建多个线程
        for crud_name in crud_names:
            for i in range(3):
                thread = threading.Thread(
                    target=create_crud_instance, 
                    args=(crud_name, i)
                )
                threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证没有错误
        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        
        # 验证每种CRUD类型的所有实例都相同
        for crud_name in crud_names:
            crud_instances = [v for k, v in instances.items() if k.startswith(crud_name)]
            first_instance = crud_instances[0]
            for instance in crud_instances[1:]:
                self.assertIs(instance, first_instance, 
                             f"Different instances for {crud_name}")


class CrudUtilsHelperMethodsTest(unittest.TestCase):
    """CRUD工具函数辅助方法测试"""

    def test_camel_to_snake_conversion(self):
        """测试驼峰命名到下划线命名的转换"""
        test_cases = [
            ('Bar', 'bar'),
            ('BarCrud', 'bar_crud'),
            ('OrderRecord', 'order_record'),
            ('EnginePortfolioMapping', 'engine_portfolio_mapping'),
            ('StockInfo', 'stock_info'),
            ('TickSummary', 'tick_summary'),
            ('AdjustFactor', 'adjust_factor'),
        ]
        
        for camel_case, expected_snake_case in test_cases:
            with self.subTest(camel_case=camel_case):
                result = _camel_to_snake(camel_case)
                self.assertEqual(result, expected_snake_case, 
                               f"Failed to convert {camel_case} to {expected_snake_case}, got {result}")

    def test_crud_name_to_class_name_mapping(self):
        """测试CRUD名称到类名的映射逻辑"""
        test_cases = [
            ('bar', 'BarCRUD'),
            ('signal', 'SignalCRUD'),
            ('order_record', 'OrderRecordCRUD'),
            ('engine_portfolio_mapping', 'EnginePortfolioMappingCRUD'),
            ('stock_info', 'StockInfoCRUD'),
            ('tick_summary', 'TickSummaryCRUD'),
        ]
        
        for crud_name, expected_class_name in test_cases:
            with self.subTest(crud_name=crud_name):
                # 模拟get_crud内部的类名生成逻辑
                class_name = f"{''.join([s.capitalize() for s in crud_name.split('_')])}CRUD"
                self.assertEqual(class_name, expected_class_name,
                               f"Failed to map {crud_name} to {expected_class_name}, got {class_name}")


class CrudUtilsErrorHandlingTest(unittest.TestCase):
    """CRUD工具函数错误处理测试"""

    def setUp(self):
        """每个测试前清理缓存"""
        clear_crud_cache()

    def test_attribute_error_message_quality(self):
        """测试属性错误消息质量"""
        with self.assertRaises(AttributeError) as context:
            get_crud('nonexistent_attribute')
            
        error_message = str(context.exception)
        
        # 验证错误消息包含有用信息
        self.assertIn("not found in the ginkgo.data.crud module", error_message)
        self.assertIn("Available CRUDs:", error_message)
        
        # 应该列出一些可用的CRUD
        available_cruds = get_available_crud_names()
        for crud_name in available_cruds[:3]:  # 检查前几个
            self.assertIn(crud_name, error_message, 
                         f"Available CRUD '{crud_name}' should be mentioned in error message")

    def test_empty_crud_name_handling(self):
        """测试空CRUD名称的处理"""
        with self.assertRaises(AttributeError):
            get_crud('')

    def test_invalid_characters_in_crud_name(self):
        """测试CRUD名称中包含无效字符的处理"""
        invalid_names = ['bar-crud', 'bar.crud', 'bar crud', 'bar/crud']
        
        for invalid_name in invalid_names:
            with self.subTest(invalid_name=invalid_name):
                with self.assertRaises(AttributeError):
                    get_crud(invalid_name)


if __name__ == '__main__':
    # 设置测试运行器
    unittest.main(verbosity=2)