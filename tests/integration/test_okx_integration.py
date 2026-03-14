"""
Integration Tests for OKX API

Tests for OKX exchange API integration.
These tests require network access and should be run with testnet credentials.
"""

import pytest
import os
from unittest.mock import patch, Mock
from ginkgo.trading.brokers.okx_broker import OKXBroker
from ginkgo.data.services.live_account_service import LiveAccountService
from ginkgo.data.services.encryption_service import EncryptionService


@pytest.mark.integration
class TestOKXAPIIntegration:
    """OKX API集成测试

    注意：这些测试需要：
    1. 网络连接
    2. OKX测试网凭证（环境变量或测试配置）
    3. 可选：使用mock避免实际API调用
    """

    @pytest.fixture
    def test_credentials(self):
        """获取测试凭证"""
        # 优先使用环境变量
        api_key = os.getenv("OKX_TEST_API_KEY")
        api_secret = os.getenv("OKX_TEST_API_SECRET")
        passphrase = os.getenv("OKX_TEST_PASSPHRASE")

        if not all([api_key, api_secret, passphrase]):
            pytest.skip("OKX测试凭证未配置（设置OKX_TEST_API_KEY等环境变量）")

        return {
            "api_key": api_key,
            "api_secret": api_secret,
            "passphrase": passphrase
        }

    @pytest.fixture
    def encryption_service(self):
        """加密服务"""
        return EncryptionService()

    @pytest.fixture
    def live_account_service(self):
        """实盘账号服务"""
        return LiveAccountService()

    @pytest.fixture
    def test_broker(self, test_credentials, encryption_service):
        """创建测试用的Broker实例"""
        # 加密凭证
        encrypted_key = encryption_service.encrypt(test_credentials["api_key"])
        encrypted_secret = encryption_service.encrypt(test_credentials["api_secret"])
        encrypted_pass = encryption_service.encrypt(test_credentials["passphrase"])

        # Mock live account
        with patch('ginkgo.trading.brokers.okx_broker.container.live_account') as mock_crud:
            mock_account = Mock()
            mock_account.exchange = "okx"
            mock_account.environment = "testnet"
            mock_account.api_key_encrypted = encrypted_key
            mock_account.api_secret_encrypted = encrypted_secret
            mock_account.passphrase_encrypted = encrypted_pass

            mock_crud.return_value.get.return_value = mock_account

            broker = OKXBroker(
                live_account_id="test-account",
                portfolio_id="test-portfolio"
            )

            yield broker

    def test_connect_to_okx_testnet(self, test_broker):
        """测试连接到OKX测试网"""
        success = test_broker.connect()

        assert success is True
        assert test_broker._connected is True

    def test_disconnect_from_okx(self, test_broker):
        """测试断开OKX连接"""
        # 先连接
        test_broker.connect()
        assert test_broker._connected is True

        # 断开连接
        test_broker.disconnect()
        assert test_broker._connected is False

    @pytest.mark.skip(reason="需要实际交易权限，可能产生测试费用")
    def test_place_market_order(self, test_broker):
        """测试下市价单（实际API调用）

        注意：此测试会执行真实交易，默认跳过
        """
        from ginkgo.data.models.model_order import Order, DIRECTION_TYPES, ORDER_TYPES

        # 创建小额测试订单
        order = Mock(spec=Order)
        order.uuid = "test-order-123"
        order.code = "BTC-USDT"
        order.direction = DIRECTION_TYPES.LONG
        order.volume = 0.001  # 最小数量
        order.order_type = ORDER_TYPES.MARKET
        order.price = None

        # 连接
        test_broker.connect()

        # 下单
        result = test_broker.submit_order(order)

        assert result.success is True
        assert result.exchange_order_id is not None

        # 清理：取消订单（如果未成交）
        # test_broker.cancel_order(order.uuid, result.exchange_order_id)

    def test_get_account_balance(self, test_broker):
        """测试获取账户余额"""
        test_broker.connect()

        # 调用OKX API获取余额
        balance = test_broker._okx.account.get_balance()

        assert balance is not None
        assert "code" in balance
        assert balance["code"] == "0"  # 成功

    def test_get_positions(self, test_broker):
        """测试获取持仓信息"""
        test_broker.connect()

        # 调用OKX API获取持仓
        positions = test_broker._okx.account.get_positions()

        assert positions is not None
        assert "code" in positions
        assert positions["code"] == "0"

    def test_get_order_history(self, test_broker):
        """测试获取历史订单"""
        test_broker.connect()

        # 调用OKX API获取订单历史
        orders = test_broker._okx.trade.get_orders_history(
            instType="SPOT",
            limit="10"
        )

        assert orders is not None
        assert "code" in orders
        assert orders["code"] == "0"

    @pytest.mark.skip(reason="需要实际交易权限")
    def test_cancel_order(self, test_broker):
        """测试取消订单（实际API调用）"""
        # 此测试需要一个已存在的订单ID
        order_id = "existing-order-id"

        test_broker.connect()
        success = test_broker.cancel_order("test-uuid", order_id)

        assert success is True


@pytest.mark.integration
class TestLiveAccountServiceIntegration:
    """LiveAccountService集成测试"""

    @pytest.fixture
    def live_account_service(self):
        return LiveAccountService()

    @pytest.fixture
    def encryption_service(self):
        return EncryptionService()

    @pytest.fixture
    def sample_account_data(self):
        import time
        return {
            "user_id": "integration-test-user",
            "name": f"集成测试账号-{int(time.time())}",
            "exchange": "okx",
            "environment": "testnet",
            "api_key": "test-api-key",
            "api_secret": "test-api-secret",
            "passphrase": "test-passphrase",
            "description": "用于集成测试"
        }

    def test_create_and_validate_account_flow(
        self, live_account_service, encryption_service, sample_account_data
    ):
        """测试创建和验证账号的完整流程"""
        # 注意：此测试会实际创建数据库记录
        # 需要确保测试环境已正确配置

        # 1. 创建账号
        result = live_account_service.create_account(**sample_account_data)

        assert result["success"] is True
        account_uuid = result["data"]["account_uuid"]

        # 2. 获取账号
        result = live_account_service.get_account_by_uuid(account_uuid)
        assert result["success"] is True

        # 3. 清理：删除测试账号
        result = live_account_service.delete_account(account_uuid)
        assert result["success"] is True


@pytest.mark.integration
class TestOKXWebsocketIntegration:
    """OKX WebSocket集成测试"""

    @pytest.fixture
    def test_credentials(self):
        """获取测试凭证"""
        api_key = os.getenv("OKX_TEST_API_KEY")
        api_secret = os.getenv("OKX_TEST_API_SECRET")
        passphrase = os.getenv("OKX_TEST_PASSPHRASE")

        if not all([api_key, api_secret, passphrase]):
            pytest.skip("OKX测试凭证未配置")

        return {
            "api_key": api_key,
            "api_secret": api_secret,
            "passphrase": passphrase
        }

    @pytest.mark.skip(reason="WebSocket连接需要长时间运行")
    def test_websocket_connection(self, test_credentials):
        """测试WebSocket连接

        注意：此测试会建立长时间运行的连接，默认跳过
        """
        import time
        from okx import OkxAPI, PublicData

        # 创建公共数据WebSocket客户端
        public_ws = PublicData.PublicDataAPI(
            domain="https://www.okx.com",  # 测试网URL
            debug=False
        )

        # 订阅ticker
        public_ws.subscribe("tickers", "BTC-USDT")

        # 等待消息
        time.sleep(5)

        # 验证连接
        assert True  # 如果没有抛出异常，说明连接成功

        # 取消订阅
        public_ws.unsubscribe("tickers", "BTC-USDT")


@pytest.mark.integration
class TestEncryptionServiceIntegration:
    """加密服务集成测试"""

    @pytest.fixture
    def encryption_service(self):
        return EncryptionService()

    def test_encrypt_decrypt_credentials(self, encryption_service):
        """测试加密解密API凭证"""
        credentials = {
            "api_key": "my-api-key-12345",
            "api_secret": "my-secret-key-67890",
            "passphrase": "my-passphrase-abcde"
        }

        # 加密
        encrypted_key = encryption_service.encrypt(credentials["api_key"])
        encrypted_secret = encryption_service.encrypt(credentials["api_secret"])
        encrypted_pass = encryption_service.encrypt(credentials["passphrase"])

        # 验证加密结果
        assert encrypted_key != credentials["api_key"]
        assert encrypted_secret != credentials["api_secret"]
        assert encrypted_pass != credentials["passphrase"]

        # 解密
        decrypted_key = encryption_service.decrypt(encrypted_key)
        decrypted_secret = encryption_service.decrypt(encrypted_secret)
        decrypted_pass = encryption_service.decrypt(encrypted_pass)

        # 验证解密结果
        assert decrypted_key == credentials["api_key"]
        assert decrypted_secret == credentials["api_secret"]
        assert decrypted_pass == credentials["passphrase"]

    def test_persistence_key(self):
        """测试持久化密钥"""
        from ginkgo.data.services.encryption_service import get_encryption_service

        service = get_encryption_service()

        # 测试加密解密
        plaintext = "persistent-test"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        assert decrypted == plaintext


# Pytest配置和标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (may require network/credentials)"
    )


if __name__ == "__main__":
    # 运行集成测试
    pytest.main([__file__, "-v", "-m", "integration"])
