import unittest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

from ginkgo.libs.core.logger import GinkgoLogger


class CoreLoggerTest(unittest.TestCase):
    """
    单元测试：核心日志模块
    """

    def setUp(self):
        """测试前的准备工作"""
        self.temp_dir = tempfile.mkdtemp()
        self.logger_name = "test_logger"
        self.file_names = ["test.log"]

    def tearDown(self):
        """测试后的清理工作"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_GinkgoLogger_Init(self):
        """测试GinkgoLogger初始化"""
        logger = GinkgoLogger(logger_name=self.logger_name, file_names=self.file_names, console_log=True)
        self.assertIsNotNone(logger)

    def test_GinkgoLogger_CreateLogger(self):
        """测试创建日志器"""
        logger = GinkgoLogger(logger_name=self.logger_name, file_names=self.file_names, console_log=True)
        # 测试logger对象是否被正确创建
        self.assertIsNotNone(logger.logger)
        self.assertEqual(logger.logger.name, self.logger_name)

    def test_GinkgoLogger_LogLevels(self):
        """测试日志级别方法"""
        logger = GinkgoLogger(logger_name=self.logger_name, file_names=self.file_names, console_log=True)

        # 测试各种日志级别方法是否存在
        self.assertTrue(hasattr(logger, "INFO"))
        self.assertTrue(hasattr(logger, "WARN"))
        self.assertTrue(hasattr(logger, "ERROR"))
        self.assertTrue(hasattr(logger, "DEBUG"))
        self.assertTrue(hasattr(logger, "CRITICAL"))

    def test_GinkgoLogger_LogMessage(self):
        """测试日志消息输出"""
        with patch("logging.Logger.info") as mock_info:
            logger = GinkgoLogger(logger_name=self.logger_name, file_names=self.file_names, console_log=True)
            test_message = "Test log message"
            logger.INFO(test_message)

    def test_GinkgoLogger_FileHandlers(self):
        """测试文件处理器配置"""
        logger = GinkgoLogger(logger_name=self.logger_name, file_names=self.file_names, console_log=False)
        # 检查是否有文件处理器
        file_handlers = [h for h in logger.logger.handlers if hasattr(h, "baseFilename")]
        self.assertGreater(len(file_handlers), 0)
