import unittest
import sys
import os
from unittest.mock import patch

# 添加项目路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class LibsIntegrationTest(unittest.TestCase):
    """
    libs模块集成测试
    验证重构后的模块化导入和向后兼容性
    """

    def test_CoreModule_Import(self):
        """测试核心模块导入"""
        try:
            from ginkgo.libs.core import GinkgoConfig, GinkgoLogger, GinkgoThreadManager

            self.assertTrue(True, "核心模块导入成功")
        except ImportError as e:
            self.fail(f"核心模块导入失败: {e}")

    def test_DataModule_Import(self):
        """测试数据处理模块导入"""
        try:
            from ginkgo.libs.data import datetime_normalize, Number, to_decimal, cal_fee

            self.assertTrue(True, "数据处理模块导入成功")
        except ImportError as e:
            self.fail(f"数据处理模块导入失败: {e}")

    def test_UtilsModule_Import(self):
        """测试工具模块导入"""
        try:
            from ginkgo.libs.utils import (
                try_wait_counter,
                pretty_repr,
                GinkgoColor,
                str2bool,
                time_logger,
                RichProgress,
            )

            self.assertTrue(True, "工具模块导入成功")
        except ImportError as e:
            self.fail(f"工具模块导入失败: {e}")

    def test_MainModule_BackwardCompatibility(self):
        """测试主模块向后兼容性"""
        try:
            # 测试向后兼容的导入方式
            from ginkgo.libs import GCONF, GLOG, GTM
            from ginkgo.libs import datetime_normalize, try_wait_counter
            from ginkgo.libs import pretty_repr, chinese_count, GinkgoColor

            # 验证实例类型
            from ginkgo.libs.core.config import GinkgoConfig
            from ginkgo.libs.core.logger import GinkgoLogger
            from ginkgo.libs.core.threading import GinkgoThreadManager

            self.assertIsInstance(GCONF, GinkgoConfig)
            self.assertIsInstance(GLOG, GinkgoLogger)
            self.assertIsInstance(GTM, GinkgoThreadManager)

            self.assertTrue(True, "向后兼容性测试通过")
        except ImportError as e:
            self.fail(f"向后兼容性测试失败: {e}")

    def test_GlobalInstances_Singleton(self):
        """测试全局实例的单例模式"""
        from ginkgo.libs import GCONF, GLOG, GTM
        from ginkgo.libs.core.config import GinkgoConfig
        from ginkgo.libs.core.logger import GinkgoLogger
        from ginkgo.libs.core.threading import GinkgoThreadManager

        # 创建新实例
        new_config = GinkgoConfig()

        # 验证单例模式（至少对于配置类）
        self.assertIs(GCONF, new_config, "配置类应该遵循单例模式")

    def test_FunctionalCompatibility(self):
        """测试功能兼容性"""
        from ginkgo.libs import datetime_normalize, try_wait_counter, chinese_count
        import datetime

        # 测试datetime_normalize功能
        result = datetime_normalize("20240101")
        expected = datetime.datetime(2024, 1, 1, 0, 0, 0)
        self.assertEqual(result, expected)

        # 测试try_wait_counter功能
        result = try_wait_counter(5)
        self.assertIsInstance(result, (int, float))
        self.assertGreater(result, 0)

        # 测试chinese_count功能
        result = chinese_count("测试中文123")
        self.assertEqual(result, 4)

    def test_ModuleStructure_Integrity(self):
        """测试模块结构完整性"""
        import os

        base_path = os.path.join(os.path.dirname(__file__), "..", "..", "src", "ginkgo", "libs")

        # 检查目录结构
        required_dirs = ["core", "data", "utils"]
        for dir_name in required_dirs:
            dir_path = os.path.join(base_path, dir_name)
            self.assertTrue(os.path.isdir(dir_path), f"目录 {dir_name} 应该存在")

            # 检查__init__.py文件
            init_file = os.path.join(dir_path, "__init__.py")
            self.assertTrue(os.path.isfile(init_file), f"{dir_name}/__init__.py 应该存在")

    def test_AllExports_Available(self):
        """测试所有导出项都可用"""
        import ginkgo.libs as libs

        # 从__all__获取导出列表
        expected_exports = getattr(libs, "__all__", [])

        missing_exports = []
        for export_name in expected_exports:
            if not hasattr(libs, export_name):
                missing_exports.append(export_name)

        if missing_exports:
            self.fail(f"缺失的导出项: {missing_exports}")

    def test_NoCircularImports(self):
        """测试无循环导入"""
        try:
            # 尝试导入所有子模块
            from ginkgo.libs import core, data, utils
            from ginkgo.libs.core import config, logger, threading
            from ginkgo.libs.data import normalize, number, math, statistics
            from ginkgo.libs.utils import common, display

            self.assertTrue(True, "无循环导入检测通过")
        except ImportError as e:
            self.fail(f"可能存在循环导入: {e}")

    def test_ErrorHandling_GracefulDegradation(self):
        """测试错误处理和优雅降级"""
        # 测试可选导入的优雅处理
        import ginkgo.libs as libs

        # 这些可能不存在，但不应该导致模块加载失败
        optional_items = ["cn_index", "GinkgoSingleLinkedNode", "find_process_by_keyword"]

        for item in optional_items:
            value = getattr(libs, item, None)
            # 可以是None或者实际的函数/类
            self.assertTrue(value is None or callable(value) or hasattr(value, "__name__"))

    def test_PerformanceBaseline(self):
        """测试性能基线"""
        import time

        # 测试导入性能
        start_time = time.time()
        from ginkgo.libs import GCONF, GLOG, datetime_normalize, try_wait_counter

        import_time = time.time() - start_time

        # 导入应该在合理时间内完成（比如1秒内）
        self.assertLess(import_time, 1.0, "模块导入应该在1秒内完成")

        # 测试函数调用性能
        start_time = time.time()
        for _ in range(100):
            try_wait_counter(5)
        call_time = time.time() - start_time

        # 100次函数调用应该很快
        self.assertLess(call_time, 0.1, "函数调用性能应该足够快")


class LibsTestSuite:
    """libs模块测试套件"""

    @staticmethod
    def get_test_suite():
        """获取完整的测试套件"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # 添加集成测试
        suite.addTests(loader.loadTestsFromTestCase(LibsIntegrationTest))

        return suite

    @staticmethod
    def run_all_tests():
        """运行所有测试"""
        suite = LibsTestSuite.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        return result.wasSuccessful()
