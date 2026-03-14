"""
Unit Tests for OKXBroker

Tests for OKX exchange integration and order execution.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ginkgo.trading.brokers.okx_broker import OKXBroker
from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
from ginkgo.data.models.model_order import MOrder, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.enums import ORDERSTATUS_TYPES
from ginkgo.data.models.model_broker_instance import BrokerStateType


class TestOKXBroker:
    """OKXBroker单元测试"""

    @pytest.fixture
    def mock_encryption_service(self):
        """Mock加密服务"""
        mock_service = Mock()
        mock_service.decrypt.side_effect = lambda x: x.replace("encrypted-", "")
        return mock_service

    @pytest.fixture
    def okx_broker(self, mock_encryption_service):
        """创建OKXBroker实例"""
        with patch('ginkgo.trading.brokers.okx_broker.get_encryption_service', return_value=mock_encryption_service):
            return OKXBroker(
                broker_uuid="test-broker-uuid",
                portfolio_id="test-portfolio-uuid",
                live_account_id="test-account-uuid",
                api_key="encrypted-api-key",
                api_secret="encrypted-api-secret",
                passphrase="encrypted-passphrase",
                environment="testnet"
            )

    @pytest.fixture
    def mock_order(self):
        """创建模拟订单"""
        order = Mock(spec=MOrder)
        order.uuid = "test-order-uuid"
        order.code = "BTC-USDT"
        order.direction = DIRECTION_TYPES.LONG
        order.volume = 0.01
        order.order_type = ORDER_TYPES.MARKETORDER
        order.price = None  # 市价单
        return order

    def test_okx_broker_initialization(self, okx_broker):
        """测试OKXBroker初始化"""
        assert okx_broker.live_account_id == "test-account-uuid"
        assert okx_broker.portfolio_id == "test-portfolio-uuid"
        assert okx_broker.broker_uuid == "test-broker-uuid"
        assert okx_broker.is_connected() is False

    def test_validate_order_not_connected(self, okx_broker, mock_order):
        """测试未连接时验证订单"""
        result = okx_broker.validate_order(mock_order)
        assert result is False

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_connect_success(self, mock_trade, mock_account, okx_broker):
        """测试连接OKX成功"""
        # Mock account API response
        mock_account_instance = Mock()
        mock_account_instance.get_account_balance.return_value = {'code': '0', 'msg': '', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_instance

        # Mock trade API
        mock_trade_instance = Mock()
        mock_trade.TradeAPI.return_value = mock_trade_instance

        success = okx_broker.connect()

        assert success is True
        assert okx_broker.is_connected() is True

    def test_disconnect(self, okx_broker):
        """测试断开连接"""
        okx_broker.disconnect()
        assert okx_broker.is_connected() is False

    def test_submit_order_not_connected(self, okx_broker, mock_order):
        """测试未连接时提交订单"""
        # 创建mock event
        event = Mock()
        event.order = mock_order

        result = okx_broker.submit_order_event(event)

        assert result.status == ORDERSTATUS_TYPES.REJECTED
        assert "Not connected" in result.error_message

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_submit_order_market_success(self, mock_trade, mock_account, okx_broker, mock_order):
        """测试提交市价单成功"""
        # Setup connection
        mock_account_instance = Mock()
        mock_account_instance.get_account_balance.return_value = {'code': '0', 'msg': '', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_instance

        mock_trade_instance = Mock()
        mock_trade_instance.place_order.return_value = {
            "code": "0",
            "msg": "",
            "data": [{
                "ordId": "12345",
                "sCode": "0"
            }]
        }
        mock_trade.TradeAPI.return_value = mock_trade_instance

        okx_broker.connect()

        # Create event
        event = Mock()
        event.order = mock_order

        result = okx_broker.submit_order_event(event)

        assert isinstance(result, BrokerExecutionResult)
        assert result.status == ORDERSTATUS_TYPES.SUBMITTED
        assert result.broker_order_id == "12345"

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_submit_order_api_error(self, mock_trade, mock_account, okx_broker, mock_order):
        """测试API错误"""
        # Setup
        mock_account_instance = Mock()
        mock_account_instance.get_account_balance.return_value = {'code': '0', 'msg': '', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_instance

        mock_trade_instance = Mock()
        mock_trade_instance.place_order.return_value = {
            "code": "50001",
            "msg": "Insufficient balance",
            "data": []
        }
        mock_trade.TradeAPI.return_value = mock_trade_instance

        okx_broker.connect()

        event = Mock()
        event.order = mock_order

        result = okx_broker.submit_order_event(event)

        assert result.status == ORDERSTATUS_TYPES.REJECTED
        assert "Insufficient balance" in result.error_message

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_cancel_order_success(self, mock_trade, mock_account, okx_broker):
        """测试取消订单成功"""
        # Setup
        mock_account_instance = Mock()
        mock_account_instance.get_account_balance.return_value = {'code': '0', 'msg': '', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_instance

        mock_trade_instance = Mock()
        mock_trade_instance.cancel_order.return_value = {
            "code": "0",
            "msg": "",
            "data": [{
                "ordId": "12345",
                "sCode": "0"
            }]
        }
        mock_trade.TradeAPI.return_value = mock_trade_instance

        okx_broker.connect()

        result = okx_broker.cancel_order("12345")

        assert result.status == ORDERSTATUS_TYPES.CANCELED

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_cancel_order_not_found(self, mock_trade, mock_account, okx_broker):
        """测试取消不存在的订单"""
        # Setup
        mock_account_instance = Mock()
        mock_account_instance.get_account_balance.return_value = {'code': '0', 'msg': '', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_instance

        mock_trade_instance = Mock()
        mock_trade_instance.cancel_order.return_value = {
            "code": "50014",
            "msg": "Order not found",
            "data": []
        }
        mock_trade.TradeAPI.return_value = mock_trade_instance

        okx_broker.connect()

        result = okx_broker.cancel_order("99999")

        assert result.status == ORDERSTATUS_TYPES.REJECTED


class TestBrokerExecutionResult:
    """BrokerExecutionResult测试"""

    def test_success_result(self):
        """测试成功结果"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.SUBMITTED,
            broker_order_id="12345"
        )

        assert result.status == ORDERSTATUS_TYPES.SUBMITTED
        assert result.broker_order_id == "12345"
        assert result.error_message is None

    def test_failure_result(self):
        """测试失败结果"""
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.REJECTED,
            error_message="Insufficient balance"
        )

        assert result.status == ORDERSTATUS_TYPES.REJECTED
        assert result.broker_order_id is None
        assert result.error_message == "Insufficient balance"

    def test_result_with_order(self):
        """测试包含订单的结果"""
        mock_order = Mock()
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.FILLED,
            broker_order_id="12345",
            order=mock_order
        )

        assert result.order is mock_order
