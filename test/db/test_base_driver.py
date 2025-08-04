import unittest
import threading
import time
from unittest.mock import MagicMock

try:
    from ginkgo.data.drivers.base_driver import DatabaseDriverBase
    from ginkgo.libs import GLOG, GinkgoLogger
except ImportError:
    DatabaseDriverBase = None
    GLOG = None
    GinkgoLogger = None


class MinimalTestDriver(DatabaseDriverBase):
    """最小化测试驱动，只实现必要的抽象方法"""

    def _create_engine(self):
        return "fake_engine"  # 简单字符串，避免复杂的SQLAlchemy依赖

    def _health_check_query(self) -> str:
        return "SELECT 1"

    def _get_uri(self) -> str:
        return "test://localhost:5432/testdb"


class IncompleteDriver(DatabaseDriverBase):
    """不完整的驱动类，用于测试抽象方法的强制实现"""

    # 故意不实现任何抽象方法
    pass


class DatabaseDriverBaseTest(unittest.TestCase):
    """
    数据库驱动基类测试 - 专注于核心逻辑验证
    """

    def setUp(self):
        """准备测试环境"""
        if DatabaseDriverBase is None:
            self.skipTest("DatabaseDriverBase not available")

    def test_abstract_base_class_cannot_be_instantiated(self):
        """测试抽象基类不能直接实例化"""
        with self.assertRaises(TypeError):
            DatabaseDriverBase("test")

    def test_incomplete_subclass_cannot_be_instantiated(self):
        """测试不完整的子类不能实例化"""
        with self.assertRaises(TypeError):
            IncompleteDriver("test")

    def test_basic_initialization(self):
        """测试基本初始化"""
        driver = MinimalTestDriver("TestDriver")

        # 检查基本属性
        self.assertEqual(driver.driver_name, "TestDriver")
        self.assertEqual(driver._db_type, "testdriver")
        self.assertIsNotNone(driver._connection_stats)
        self.assertIsNotNone(driver._lock)
        self.assertIsInstance(driver.loggers, list)

        # 检查连接统计初始化
        stats = driver.get_connection_stats()
        self.assertEqual(stats["connections_created"], 0)
        self.assertEqual(stats["connections_closed"], 0)
        self.assertEqual(stats["active_connections"], 0)
        self.assertEqual(stats["health_check_failures"], 0)
        self.assertEqual(stats["driver_name"], "TestDriver")

    def test_shared_database_logger_singleton(self):
        """测试共享数据库logger的单例行为"""
        # 创建第一个驱动实例
        driver1 = MinimalTestDriver("Driver1")

        # 验证共享logger被创建
        self.assertIsNotNone(DatabaseDriverBase._shared_database_logger)

        # 创建第二个驱动实例
        driver2 = MinimalTestDriver("Driver2")

        # 验证两个实例共享同一个database logger
        shared_logger1 = None
        shared_logger2 = None

        # 通过logger_name属性查找共享的database logger
        for logger in driver1.loggers:
            if hasattr(logger, "logger_name") and logger.logger_name == "ginkgo_database":
                shared_logger1 = logger
                break

        for logger in driver2.loggers:
            if hasattr(logger, "logger_name") and logger.logger_name == "ginkgo_database":
                shared_logger2 = logger
                break

        # 应该是同一个logger实例
        self.assertIsNotNone(shared_logger1, "Shared database logger not found in driver1")
        self.assertIsNotNone(shared_logger2, "Shared database logger not found in driver2")
        self.assertIs(shared_logger1, shared_logger2)
        self.assertIs(shared_logger1, DatabaseDriverBase._shared_database_logger)

        # 验证logger的名称正确
        self.assertEqual(shared_logger1.logger_name, "ginkgo_database")
        self.assertEqual(shared_logger2.logger_name, "ginkgo_database")

    def test_logger_queue_management(self):
        """测试logger队列管理"""
        driver = MinimalTestDriver("TestDriver")

        # 应该至少有两个logger: GLOG和database logger
        self.assertGreaterEqual(len(driver.loggers), 2)

        # 检查GLOG是否在队列中
        self.assertIn(GLOG, driver.loggers)

    def test_add_logger_deduplication(self):
        """测试add_logger的去重功能"""
        driver = MinimalTestDriver("TestDriver")
        initial_count = len(driver.loggers)

        # 添加新的logger
        mock_logger1 = MagicMock()
        mock_logger1.logger_name = "test_logger"
        driver.add_logger(mock_logger1)

        self.assertEqual(len(driver.loggers), initial_count + 1)
        self.assertIn(mock_logger1, driver.loggers)

        # 尝试添加同名的logger，应该被去重
        mock_logger2 = MagicMock()
        mock_logger2.logger_name = "test_logger"  # 同名
        driver.add_logger(mock_logger2)

        # 数量不应该增加，且原logger仍在
        self.assertEqual(len(driver.loggers), initial_count + 1)
        self.assertIn(mock_logger1, driver.loggers)
        self.assertNotIn(mock_logger2, driver.loggers)

        # 添加不同名的logger应该成功
        mock_logger3 = MagicMock()
        mock_logger3.logger_name = "different_logger"
        driver.add_logger(mock_logger3)

        self.assertEqual(len(driver.loggers), initial_count + 2)
        self.assertIn(mock_logger3, driver.loggers)

    def test_log_method_basic_functionality(self):
        """测试log方法的基本功能"""
        driver = MinimalTestDriver("TestDriver")

        # 添加mock logger进行测试
        mock_logger = MagicMock()
        driver.add_logger(mock_logger)

        # 测试日志记录
        driver.log("INFO", "Test message")
        mock_logger.INFO.assert_called_with("[TestDriver] Test message")

        driver.log("ERROR", "Error message")
        mock_logger.ERROR.assert_called_with("[TestDriver] Error message")

    def test_log_method_error_handling(self):
        """测试log方法的错误处理"""
        driver = MinimalTestDriver("TestDriver")

        # 添加一个会抛出异常的logger
        failing_logger = MagicMock()
        failing_logger.INFO.side_effect = Exception("Logger failed")
        driver.add_logger(failing_logger)

        # 即使logger失败，也不应该抛出异常
        try:
            driver.log("INFO", "Test message")
        except Exception:
            self.fail("log method should handle logger exceptions gracefully")

    def test_connection_stats_calculation(self):
        """测试连接统计的计算逻辑"""
        driver = MinimalTestDriver("TestDriver")

        # 模拟一些连接统计
        with driver._lock:
            driver._connection_stats["connections_created"] = 10
            driver._connection_stats["connections_closed"] = 8
            driver._connection_stats["health_check_failures"] = 2

        stats = driver.get_connection_stats()

        # 验证计算逻辑
        self.assertEqual(stats["connections_created"], 10)
        self.assertEqual(stats["connections_closed"], 8)
        self.assertEqual(stats["active_connections"], 0)  # 创建时设置
        self.assertEqual(stats["health_check_failures"], 2)
        self.assertEqual(stats["connection_efficiency"], 0.8)  # 8/10
        self.assertEqual(stats["driver_name"], "TestDriver")
        self.assertIn("uptime", stats)

    def test_thread_safety_basic(self):
        """测试基本的线程安全性"""
        driver = MinimalTestDriver("TestDriver")
        results = []
        errors = []

        def worker():
            try:
                for i in range(5):
                    driver.log("INFO", f"Thread message {i}")
                    stats = driver.get_connection_stats()
                    results.append(stats["driver_name"])
            except Exception as e:
                errors.append(e)

        # 创建3个线程进行测试
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 检查没有错误发生
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 15)  # 3个线程 × 5次调用

        # 所有结果应该都是正确的driver名称
        for result in results:
            self.assertEqual(result, "TestDriver")

    def test_abstract_methods_are_called(self):
        """测试抽象方法被正确调用"""
        driver = MinimalTestDriver("TestDriver")

        # 验证抽象方法返回预期值
        self.assertEqual(driver._create_engine(), "fake_engine")
        self.assertEqual(driver._health_check_query(), "SELECT 1")
        self.assertEqual(driver._get_uri(), "test://localhost:5432/testdb")

    def test_multiple_drivers_independence(self):
        """测试多个驱动实例的独立性"""
        driver1 = MinimalTestDriver("Driver1")
        driver2 = MinimalTestDriver("Driver2")

        # 每个驱动有独立的属性
        self.assertEqual(driver1.driver_name, "Driver1")
        self.assertEqual(driver2.driver_name, "Driver2")

        # 但共享同一个database logger
        shared_logger1 = DatabaseDriverBase._shared_database_logger
        shared_logger2 = DatabaseDriverBase._shared_database_logger
        self.assertIs(shared_logger1, shared_logger2)

        # 连接统计是独立的
        with driver1._lock:
            driver1._connection_stats["connections_created"] = 5

        stats1 = driver1.get_connection_stats()
        stats2 = driver2.get_connection_stats()

        self.assertEqual(stats1["connections_created"], 5)
        self.assertEqual(stats2["connections_created"], 0)

    def test_logger_name_handling_edge_cases(self):
        """测试logger名称处理的边界情况"""
        driver = MinimalTestDriver("TestDriver")

        # 测试没有logger_name属性的logger
        logger_without_name = MagicMock()
        del logger_without_name.logger_name  # 删除属性

        initial_count = len(driver.loggers)
        driver.add_logger(logger_without_name)

        # 应该成功添加（使用str(logger)作为名称）
        self.assertEqual(len(driver.loggers), initial_count + 1)

        # 再次添加相同的logger对象，应该被去重
        driver.add_logger(logger_without_name)
        self.assertEqual(len(driver.loggers), initial_count + 1)

    def test_connection_stats_thread_safety(self):
        """测试连接统计的线程安全性"""
        driver = MinimalTestDriver("TestDriver")

        def increment_stats():
            for _ in range(10):
                with driver._lock:
                    driver._connection_stats["connections_created"] += 1

        # 创建多个线程同时修改统计
        threads = []
        for _ in range(5):
            t = threading.Thread(target=increment_stats)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # 验证最终结果正确
        stats = driver.get_connection_stats()
        self.assertEqual(stats["connections_created"], 50)  # 5个线程 × 10次增加
