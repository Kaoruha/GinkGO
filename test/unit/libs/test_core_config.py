import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from ginkgo.libs.core.config import GinkgoConfig


class CoreConfigTest(unittest.TestCase):
    """
    单元测试：核心配置模块
    """

    def setUp(self):
        """测试前的准备工作"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_ginkgo_dir = os.environ.get("GINKGO_DIR")

    def tearDown(self):
        """测试后的清理工作"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.original_ginkgo_dir:
            os.environ["GINKGO_DIR"] = self.original_ginkgo_dir
        elif "GINKGO_DIR" in os.environ:
            del os.environ["GINKGO_DIR"]

    def test_GinkgoConfig_Init(self):
        """测试GinkgoConfig初始化"""
        config = GinkgoConfig()
        self.assertIsNotNone(config)

    def test_GinkgoConfig_Singleton(self):
        """测试GinkgoConfig单例模式"""
        config1 = GinkgoConfig()
        config2 = GinkgoConfig()
        self.assertIs(config1, config2)

    def test_GinkgoConfig_SettingPath(self):
        """测试配置文件路径"""
        os.environ["GINKGO_DIR"] = self.temp_dir
        config = GinkgoConfig()
        expected_path = os.path.join(self.temp_dir, "config.yml")
        self.assertEqual(config.setting_path, expected_path)

    def test_GinkgoConfig_SecurePath(self):
        """测试安全配置文件路径"""
        os.environ["GINKGO_DIR"] = self.temp_dir
        config = GinkgoConfig()
        expected_path = os.path.join(self.temp_dir, "secure.yml")
        self.assertEqual(config.secure_path, expected_path)
