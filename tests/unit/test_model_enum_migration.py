"""
#3880 模型枚举迁移测试

验证模型文件中的枚举迁移到 ginkgo/enums.py 后:
1. 枚举可从 ginkgo.enums 导入
2. 枚举值和功能保持不变
3. 模型文件仍可 re-export（向后兼容）
"""

import unittest
import sys
import os

_path = os.path.join(os.path.dirname(__file__), '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)


class TestExchangeTypeMigration(unittest.TestCase):
    """ExchangeType 迁移验证"""

    def test_importable_from_enums(self):
        """ExchangeType 可从 ginkgo.enums 导入"""
        from ginkgo.enums import ExchangeType
        self.assertIsNotNone(ExchangeType)

    def test_values_unchanged(self):
        """ExchangeType 值与原始定义一致"""
        from ginkgo.enums import ExchangeType
        self.assertEqual(ExchangeType.OKX, "okx")
        self.assertEqual(ExchangeType.BINANCE, "binance")

    def test_from_str_method(self):
        """ExchangeType.from_str() 功能不变"""
        from ginkgo.enums import ExchangeType
        self.assertEqual(ExchangeType.from_str("okx"), ExchangeType.OKX)
        self.assertEqual(ExchangeType.from_str("OKX"), ExchangeType.OKX)
        self.assertEqual(ExchangeType.from_str("binance"), ExchangeType.BINANCE)

    def test_from_str_unknown_raises(self):
        """ExchangeType.from_str() 未知值抛 ValueError"""
        from ginkgo.enums import ExchangeType
        with self.assertRaises(ValueError):
            ExchangeType.from_str("unknown")

    def test_validate_method(self):
        """ExchangeType.validate() 功能不变"""
        from ginkgo.enums import ExchangeType
        self.assertTrue(ExchangeType.validate("okx"))
        self.assertTrue(ExchangeType.validate("binance"))
        self.assertFalse(ExchangeType.validate("unknown"))

    def test_backward_compat_model_import(self):
        """从模型文件仍可导入 ExchangeType（re-export 向后兼容）"""
        # 直接导入模型文件，不触发 models/__init__.py 的完整加载
        import importlib
        mod = importlib.import_module("ginkgo.data.models.model_live_account")
        from ginkgo.enums import ExchangeType
        self.assertIs(mod.ExchangeType, ExchangeType)

    def test_is_str_subclass(self):
        """ExchangeType 仍继承自 str"""
        from ginkgo.enums import ExchangeType
        self.assertIsInstance(ExchangeType.OKX, str)


if __name__ == "__main__":
    unittest.main()
