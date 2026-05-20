"""
OKXBroker 单元测试 — 补充覆盖

覆盖范围：
- RetryConfig 配置
- 网络错误分类 (_classify_network_error)
- 重试判断 (_is_retryable_error)
- 指数退避延迟 (_calculate_delay)
- _execute_with_retry 重试逻辑
- validate_order 订单校验
- 错误统计 (_increment_error_count / get_error_stats)
- WebSocket 消息处理 (_on_order_message)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ginkgo.trading.brokers.okx_broker import OKXBroker, RetryConfig, NetworkErrorType
from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
from ginkgo.data.models.model_order import MOrder, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.enums import ORDERSTATUS_TYPES


# ---- RetryConfig ----

class TestRetryConfig:
    def test_default_values(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        config = RetryConfig(max_retries=5, base_delay=2.0, max_delay=30.0, exponential_base=3.0, jitter=False)
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


# ---- NetworkErrorType classification ----

class TestClassifyNetworkError:
    def test_ssl_handshake_timeout(self):
        err = Exception("SSL handshake timeout")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.SSL_TIMEOUT

    def test_ssl_eof(self):
        err = Exception("SSL unexpected EOF")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.SSL_EOF

    def test_connection_refused(self):
        err = Exception("Connection refused by remote host")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.CONNECTION_REFUSED

    def test_connection_reset(self):
        err = Exception("Connection reset by peer")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.CONNECTION_RESET

    def test_timeout(self):
        err = Exception("Request timeout after 30s")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.TIMEOUT

    def test_unknown_error(self):
        err = Exception("Something unexpected happened")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.UNKNOWN

    def test_case_insensitive(self):
        err = Exception("CONNECTION REFUSED")
        assert OKXBroker._classify_network_error(err) == NetworkErrorType.CONNECTION_REFUSED


# ---- _is_retryable_error ----

class TestIsRetryableError:
    def test_ssl_error_retryable(self):
        assert OKXBroker._is_retryable_error(Exception("SSL error")) is True

    def test_timeout_retryable(self):
        assert OKXBroker._is_retryable_error(Exception("Request timeout")) is True

    def test_connection_error_type_retryable(self):
        assert OKXBroker._is_retryable_error(ConnectionError("lost")) is True

    def test_timeout_error_type_retryable(self):
        assert OKXBroker._is_retryable_error(TimeoutError("timed out")) is True

    def test_non_retryable(self):
        assert OKXBroker._is_retryable_error(Exception("Invalid API key")) is False

    def test_connection_reset_retryable(self):
        assert OKXBroker._is_retryable_error(Exception("Connection reset")) is True


# ---- _calculate_delay ----

class TestCalculateDelay:
    def test_first_attempt_no_jitter(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = OKXBroker._calculate_delay(0, config)
        assert delay == 1.0

    def test_second_attempt_no_jitter(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = OKXBroker._calculate_delay(1, config)
        assert delay == 2.0

    def test_third_attempt_no_jitter(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        delay = OKXBroker._calculate_delay(2, config)
        assert delay == 4.0

    def test_capped_at_max_delay(self):
        config = RetryConfig(base_delay=1.0, exponential_base=10.0, max_delay=5.0, jitter=False)
        delay = OKXBroker._calculate_delay(5, config)
        assert delay == 5.0

    def test_jitter_within_range(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True, max_delay=100.0)
        delays = [OKXBroker._calculate_delay(0, config) for _ in range(100)]
        for d in delays:
            assert 0.8 <= d <= 1.2  # ±20% of 1.0


# ---- _execute_with_retry ----

@pytest.fixture
def mock_encryption_service():
    svc = Mock()
    svc.decrypt.side_effect = lambda x: x.replace("encrypted-", "")
    return svc


@pytest.fixture
def broker(mock_encryption_service):
    with patch('ginkgo.trading.brokers.okx_broker.get_encryption_service', return_value=mock_encryption_service):
        return OKXBroker(
            broker_uuid="test-uuid",
            portfolio_id="test-portfolio",
            live_account_id="test-account",
            api_key="encrypted-key",
            api_secret="encrypted-secret",
            passphrase="encrypted-pass",
            environment="testnet",
        )


class TestExecuteWithRetry:
    @patch('ginkgo.trading.brokers.okx_broker.time.sleep')
    def test_success_first_attempt(self, mock_sleep, broker):
        func = Mock(return_value="ok")
        result = broker._execute_with_retry(func, operation_name="test")
        assert result == "ok"
        assert func.call_count == 1
        mock_sleep.assert_not_called()

    @patch('ginkgo.trading.brokers.okx_broker.time.sleep')
    def test_retries_on_retryable_error(self, mock_sleep, broker):
        func = Mock(side_effect=[Exception("SSL timeout"), "ok"])
        result = broker._execute_with_retry(func, operation_name="test")
        assert result == "ok"
        assert func.call_count == 2

    @patch('ginkgo.trading.brokers.okx_broker.time.sleep')
    def test_raises_non_retryable_immediately(self, mock_sleep, broker):
        func = Mock(side_effect=ValueError("bad input"))
        with pytest.raises(ValueError, match="bad input"):
            broker._execute_with_retry(func, operation_name="test")
        assert func.call_count == 1

    @patch('ginkgo.trading.brokers.okx_broker.time.sleep')
    def test_raises_after_max_retries(self, mock_sleep, broker):
        broker._retry_config = RetryConfig(max_retries=2, jitter=False)
        func = Mock(side_effect=Exception("SSL timeout"))
        with pytest.raises(Exception, match="SSL timeout"):
            broker._execute_with_retry(func, operation_name="test")
        assert func.call_count == 2


# ---- validate_order ----

class TestValidateOrder:
    def test_reject_when_not_connected(self, broker):
        order = Mock(spec=MOrder)
        assert broker.validate_order(order) is False

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_accept_market_order_when_connected(self, mock_trade, mock_account, broker):
        mock_account_inst = Mock()
        mock_account_inst.get_account_balance.return_value = {'code': '0', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_inst
        mock_trade.TradeAPI.return_value = Mock()
        broker.connect()

        order = Mock(spec=MOrder)
        order.code = "BTC-USDT"
        order.direction = DIRECTION_TYPES.LONG
        order.volume = 0.01
        order.order_type = ORDER_TYPES.MARKETORDER
        assert broker.validate_order(order) is True

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_accept_limit_order_with_price(self, mock_trade, mock_account, broker):
        mock_account_inst = Mock()
        mock_account_inst.get_account_balance.return_value = {'code': '0', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_inst
        mock_trade.TradeAPI.return_value = Mock()
        broker.connect()

        order = Mock(spec=MOrder)
        order.code = "BTC-USDT"
        order.direction = DIRECTION_TYPES.LONG
        order.volume = 0.01
        order.order_type = ORDER_TYPES.LIMITORDER
        order.price = 50000.0
        assert broker.validate_order(order) is True

    @patch('ginkgo.trading.brokers.okx_broker.Account')
    @patch('ginkgo.trading.brokers.okx_broker.Trade')
    def test_reject_limit_order_without_price(self, mock_trade, mock_account, broker):
        mock_account_inst = Mock()
        mock_account_inst.get_account_balance.return_value = {'code': '0', 'data': []}
        mock_account.AccountAPI.return_value = mock_account_inst
        mock_trade.TradeAPI.return_value = Mock()
        broker.connect()

        order = Mock(spec=MOrder)
        order.code = "BTC-USDT"
        order.direction = DIRECTION_TYPES.LONG
        order.volume = 0.01
        order.order_type = ORDER_TYPES.LIMITORDER
        order.price = None
        assert broker.validate_order(order) is False


# ---- Error stats ----

class TestErrorStats:
    def test_initial_stats_all_zero(self, broker):
        stats = broker.get_error_stats()
        assert all(v == 0 for v in stats.values())

    def test_increment_counts(self, broker):
        broker._increment_error_count(NetworkErrorType.SSL_TIMEOUT)
        broker._increment_error_count(NetworkErrorType.SSL_TIMEOUT)
        broker._increment_error_count(NetworkErrorType.TIMEOUT)
        stats = broker.get_error_stats()
        assert stats["ssl_timeout"] == 2
        assert stats["timeout"] == 1

    def test_get_error_stats_returns_copy(self, broker):
        broker._increment_error_count(NetworkErrorType.CONNECTION_REFUSED)
        stats1 = broker.get_error_stats()
        stats1["connection_refused"] = 999
        stats2 = broker.get_error_stats()
        assert stats2["connection_refused"] == 1


# ---- WebSocket message handling ----

class TestOnOrderMessage:
    def test_delegates_to_adapt_order(self, broker):
        msg = {"arg": {"channel": "orders"}, "data": [{"ordId": "12345", "state": "filled"}]}
        with patch('ginkgo.livecore.websocket_event_adapter.adapt_order') as mock_adapt:
            mock_adapt.return_value = {"exchange_order_id": "12345", "status": "filled"}
            broker._on_order_message(msg)
            mock_adapt.assert_called_once_with(msg)

    def test_returns_early_on_empty_adapt(self, broker):
        msg = {"arg": {"channel": "orders"}, "data": []}
        with patch('ginkgo.livecore.websocket_event_adapter.adapt_order', return_value=None):
            broker._on_order_message(msg)

    def test_handles_adapt_exception(self, broker):
        msg = {"arg": {"channel": "orders"}, "data": [{}]}
        with patch('ginkgo.livecore.websocket_event_adapter.adapt_order', side_effect=Exception("parse error")):
            broker._on_order_message(msg)
