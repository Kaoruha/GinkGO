"""
#3880 模型枚举迁移测试

验证模型文件中的枚举迁移到 ginkgo/enums.py 后:
1. 枚举可从 ginkgo.enums 导入
2. 枚举值和功能保持不变
3. 模型文件仍可 re-export（向后兼容）
"""

import unittest

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


class TestEnvironmentTypeMigration(unittest.TestCase):
    """EnvironmentType 迁移验证"""

    def test_importable_from_enums(self):
        from ginkgo.enums import EnvironmentType
        self.assertIsNotNone(EnvironmentType)

    def test_values_unchanged(self):
        from ginkgo.enums import EnvironmentType
        self.assertEqual(EnvironmentType.PRODUCTION, "production")
        self.assertEqual(EnvironmentType.TESTNET, "testnet")

    def test_from_str_case_insensitive(self):
        from ginkgo.enums import EnvironmentType
        self.assertEqual(EnvironmentType.from_str("production"), EnvironmentType.PRODUCTION)
        self.assertEqual(EnvironmentType.from_str("PRODUCTION"), EnvironmentType.PRODUCTION)
        self.assertEqual(EnvironmentType.from_str("testnet"), EnvironmentType.TESTNET)

    def test_from_str_unknown_raises(self):
        from ginkgo.enums import EnvironmentType
        with self.assertRaises(ValueError):
            EnvironmentType.from_str("staging")

    def test_validate(self):
        from ginkgo.enums import EnvironmentType
        self.assertTrue(EnvironmentType.validate("production"))
        self.assertTrue(EnvironmentType.validate("testnet"))
        self.assertFalse(EnvironmentType.validate("staging"))

    def test_is_str_subclass(self):
        from ginkgo.enums import EnvironmentType
        self.assertIsInstance(EnvironmentType.PRODUCTION, str)


class TestAccountStatusTypeMigration(unittest.TestCase):
    """AccountStatusType 迁移验证"""

    def test_importable_from_enums(self):
        from ginkgo.enums import AccountStatusType
        self.assertIsNotNone(AccountStatusType)

    def test_values_unchanged(self):
        from ginkgo.enums import AccountStatusType
        self.assertEqual(AccountStatusType.ENABLED, "enabled")
        self.assertEqual(AccountStatusType.DISABLED, "disabled")
        self.assertEqual(AccountStatusType.CONNECTING, "connecting")
        self.assertEqual(AccountStatusType.DISCONNECTED, "disconnected")
        self.assertEqual(AccountStatusType.ERROR, "error")

    def test_from_str_case_insensitive(self):
        from ginkgo.enums import AccountStatusType
        self.assertEqual(AccountStatusType.from_str("enabled"), AccountStatusType.ENABLED)
        self.assertEqual(AccountStatusType.from_str("ERROR"), AccountStatusType.ERROR)

    def test_from_str_unknown_raises(self):
        from ginkgo.enums import AccountStatusType
        with self.assertRaises(ValueError):
            AccountStatusType.from_str("unknown")

    def test_validate(self):
        from ginkgo.enums import AccountStatusType
        self.assertTrue(AccountStatusType.validate("enabled"))
        self.assertFalse(AccountStatusType.validate("unknown"))

    def test_is_str_subclass(self):
        from ginkgo.enums import AccountStatusType
        self.assertIsInstance(AccountStatusType.ENABLED, str)


class TestPermissionTypeMigration(unittest.TestCase):
    """PermissionType 迁移验证"""

    def test_importable_from_enums(self):
        from ginkgo.enums import PermissionType
        self.assertIsNotNone(PermissionType)

    def test_values_unchanged(self):
        from ginkgo.enums import PermissionType
        self.assertEqual(PermissionType.READ, "read")
        self.assertEqual(PermissionType.TRADE, "trade")
        self.assertEqual(PermissionType.ADMIN, "admin")

    def test_from_str_case_insensitive(self):
        from ginkgo.enums import PermissionType
        self.assertEqual(PermissionType.from_str("read"), PermissionType.READ)
        self.assertEqual(PermissionType.from_str("ADMIN"), PermissionType.ADMIN)

    def test_from_str_unknown_raises(self):
        from ginkgo.enums import PermissionType
        with self.assertRaises(ValueError):
            PermissionType.from_str("superuser")

    def test_validate(self):
        from ginkgo.enums import PermissionType
        self.assertTrue(PermissionType.validate("read"))
        self.assertFalse(PermissionType.validate("superuser"))

    def test_all_permissions(self):
        from ginkgo.enums import PermissionType
        perms = PermissionType.all_permissions()
        self.assertEqual(len(perms), 3)
        self.assertIn(PermissionType.READ, perms)

    def test_is_str_subclass(self):
        from ginkgo.enums import PermissionType
        self.assertIsInstance(PermissionType.READ, str)


class TestSubscriptionDataTypeMigration(unittest.TestCase):
    """SubscriptionDataType 迁移验证"""

    def test_importable_from_enums(self):
        from ginkgo.enums import SubscriptionDataType
        self.assertIsNotNone(SubscriptionDataType)

    def test_values_unchanged(self):
        from ginkgo.enums import SubscriptionDataType
        self.assertEqual(SubscriptionDataType.TICKER, "ticker")
        self.assertEqual(SubscriptionDataType.CANDLESTICKS, "candlesticks")
        self.assertEqual(SubscriptionDataType.TRADES, "trades")
        self.assertEqual(SubscriptionDataType.ORDERBOOK, "orderbook")

    def test_from_str_case_insensitive(self):
        from ginkgo.enums import SubscriptionDataType
        self.assertEqual(SubscriptionDataType.from_str("ticker"), SubscriptionDataType.TICKER)
        self.assertEqual(SubscriptionDataType.from_str("ORDERBOOK"), SubscriptionDataType.ORDERBOOK)

    def test_from_str_unknown_raises(self):
        from ginkgo.enums import SubscriptionDataType
        with self.assertRaises(ValueError):
            SubscriptionDataType.from_str("depth")

    def test_validate(self):
        from ginkgo.enums import SubscriptionDataType
        self.assertTrue(SubscriptionDataType.validate("ticker"))
        self.assertFalse(SubscriptionDataType.validate("depth"))

    def test_all_types(self):
        from ginkgo.enums import SubscriptionDataType
        types = SubscriptionDataType.all_types()
        self.assertEqual(len(types), 4)

    def test_is_str_subclass(self):
        from ginkgo.enums import SubscriptionDataType
        self.assertIsInstance(SubscriptionDataType.TICKER, str)


class TestBrokerStateTypeMigration(unittest.TestCase):
    """BrokerStateType 迁移验证（含状态机方法）"""

    def test_importable_from_enums(self):
        from ginkgo.enums import BrokerStateType
        self.assertIsNotNone(BrokerStateType)

    def test_values_unchanged(self):
        from ginkgo.enums import BrokerStateType
        self.assertEqual(BrokerStateType.UNINITIALIZED, "uninitialized")
        self.assertEqual(BrokerStateType.INITIALIZING, "initializing")
        self.assertEqual(BrokerStateType.RUNNING, "running")
        self.assertEqual(BrokerStateType.PAUSED, "paused")
        self.assertEqual(BrokerStateType.STOPPED, "stopped")
        self.assertEqual(BrokerStateType.ERROR, "error")
        self.assertEqual(BrokerStateType.RECOVERING, "recovering")

    def test_from_str_case_insensitive(self):
        from ginkgo.enums import BrokerStateType
        self.assertEqual(BrokerStateType.from_str("running"), BrokerStateType.RUNNING)
        self.assertEqual(BrokerStateType.from_str("RUNNING"), BrokerStateType.RUNNING)

    def test_from_str_unknown_raises(self):
        from ginkgo.enums import BrokerStateType
        with self.assertRaises(ValueError) as ctx:
            BrokerStateType.from_str("unknown")
        self.assertIn("broker state type", str(ctx.exception).lower())

    def test_validate(self):
        from ginkgo.enums import BrokerStateType
        self.assertTrue(BrokerStateType.validate("running"))
        self.assertFalse(BrokerStateType.validate("unknown"))

    def test_is_terminal(self):
        from ginkgo.enums import BrokerStateType
        self.assertTrue(BrokerStateType.is_terminal(BrokerStateType.STOPPED))
        self.assertTrue(BrokerStateType.is_terminal(BrokerStateType.ERROR))
        self.assertFalse(BrokerStateType.is_terminal(BrokerStateType.RUNNING))
        self.assertFalse(BrokerStateType.is_terminal(BrokerStateType.PAUSED))

    def test_is_active(self):
        from ginkgo.enums import BrokerStateType
        self.assertTrue(BrokerStateType.is_active(BrokerStateType.RUNNING))
        self.assertFalse(BrokerStateType.is_active(BrokerStateType.PAUSED))
        self.assertFalse(BrokerStateType.is_active(BrokerStateType.STOPPED))

    def test_can_transition_valid(self):
        from ginkgo.enums import BrokerStateType
        self.assertTrue(BrokerStateType.can_transition(
            BrokerStateType.UNINITIALIZED, BrokerStateType.INITIALIZING))
        self.assertTrue(BrokerStateType.can_transition(
            BrokerStateType.INITIALIZING, BrokerStateType.RUNNING))
        self.assertTrue(BrokerStateType.can_transition(
            BrokerStateType.RUNNING, BrokerStateType.PAUSED))
        self.assertTrue(BrokerStateType.can_transition(
            BrokerStateType.ERROR, BrokerStateType.RECOVERING))

    def test_can_transition_invalid(self):
        from ginkgo.enums import BrokerStateType
        self.assertFalse(BrokerStateType.can_transition(
            BrokerStateType.UNINITIALIZED, BrokerStateType.RUNNING))
        self.assertFalse(BrokerStateType.can_transition(
            BrokerStateType.STOPPED, BrokerStateType.RUNNING))

    def test_is_str_subclass(self):
        from ginkgo.enums import BrokerStateType
        self.assertIsInstance(BrokerStateType.RUNNING, str)


class TestDeploymentStatusMigration(unittest.TestCase):
    """DEPLOYMENT_STATUS 迁移验证"""

    def test_importable_from_enums(self):
        from ginkgo.enums import DEPLOYMENT_STATUS
        self.assertIsNotNone(DEPLOYMENT_STATUS)

    def test_values_unchanged(self):
        from ginkgo.enums import DEPLOYMENT_STATUS
        self.assertEqual(DEPLOYMENT_STATUS.PENDING, 0)
        self.assertEqual(DEPLOYMENT_STATUS.DEPLOYED, 1)
        self.assertEqual(DEPLOYMENT_STATUS.FAILED, 2)
        self.assertEqual(DEPLOYMENT_STATUS.STOPPED, 3)


class TestValidationStatusMigration(unittest.TestCase):
    """VALIDATION_STATUS 迁移验证"""

    def test_importable_from_enums(self):
        from ginkgo.enums import VALIDATION_STATUS
        self.assertIsNotNone(VALIDATION_STATUS)

    def test_values_unchanged(self):
        from ginkgo.enums import VALIDATION_STATUS
        self.assertEqual(VALIDATION_STATUS.RUNNING, 0)
        self.assertEqual(VALIDATION_STATUS.COMPLETED, 1)
        self.assertEqual(VALIDATION_STATUS.FAILED, 2)


if __name__ == "__main__":
    unittest.main()
