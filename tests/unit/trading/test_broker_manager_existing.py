"""
Unit Tests for BrokerManager

Tests for Broker lifecycle management and operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ginkgo.trading.brokers.broker_manager import BrokerManager, get_broker_manager
from ginkgo.data.models.model_broker_instance import BrokerStateType
from ginkgo.data.models.model_live_account import AccountStatusType


class TestBrokerManager:
    """BrokerManager单元测试"""

    @pytest.fixture
    def broker_manager(self):
        """创建BrokerManager实例"""
        return BrokerManager()

    @pytest.fixture
    def mock_portfolio(self):
        """模拟Portfolio对象"""
        portfolio = Mock()
        portfolio.uuid = "test-portfolio-uuid"
        portfolio.name = "测试策略"
        return portfolio

    @pytest.fixture
    def mock_live_account(self):
        """模拟实盘账号对象"""
        account = Mock()
        account.uuid = "test-account-uuid"
        account.name = "OKX测试账号"
        account.exchange = "okx"
        account.environment = "testnet"
        account.status = AccountStatusType.ENABLED  # 必须是enabled
        account.api_key = "encrypted-key"
        account.api_secret = "encrypted-secret"
        account.passphrase = "encrypted-pass"
        return account

    def test_get_broker_manager_singleton(self):
        """测试get_broker_manager返回单例"""
        manager1 = get_broker_manager()
        manager2 = get_broker_manager()

        assert manager1 is manager2

    @patch('ginkgo.trading.brokers.broker_manager.container.portfolio_crud')
    @patch('ginkgo.trading.brokers.broker_manager.container.live_account_crud')
    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    @patch('ginkgo.trading.brokers.okx_broker.get_encryption_service')
    def test_create_broker_success(
        self, mock_encryption, mock_broker_crud, mock_live_account_crud, mock_portfolio_crud,
        broker_manager, mock_portfolio, mock_live_account
    ):
        """测试创建Broker成功"""
        # Mock encryption service
        mock_enc_service = Mock()
        mock_enc_service.decrypt.side_effect = lambda x: x.replace("encrypted-", "")
        mock_encryption.return_value = mock_enc_service

        # 设置mock返回值
        mock_portfolio_instance = Mock()
        mock_portfolio_instance.uuid = mock_portfolio.uuid
        mock_portfolio_instance.live_account_id = None  # 初始无live_account
        mock_portfolio_crud.return_value.get.return_value = mock_portfolio_instance

        mock_live_account_crud.return_value.get_live_account_by_uuid.return_value = mock_live_account

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = None  # 不存在
        mock_broker_crud.return_value.add_broker_instance.return_value = Mock(
            uuid="new-broker-uuid"
        )

        success = broker_manager.create_broker(
            portfolio_id=mock_portfolio.uuid,
            live_account_id=mock_live_account.uuid
        )

        assert success is True

    @patch('ginkgo.trading.brokers.broker_manager.container.portfolio_crud')
    @patch('ginkgo.trading.brokers.broker_manager.container.live_account_crud')
    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_create_broker_portfolio_not_found(
        self, mock_broker_crud, mock_live_account_crud, mock_portfolio_crud, broker_manager
    ):
        """测试创建Broker时Portfolio不存在"""
        mock_portfolio_crud.return_value.get.return_value = None

        success = broker_manager.create_broker(
            portfolio_id="non-existent-portfolio",
            live_account_id="test-account"
        )

        assert success is False

    @patch('ginkgo.trading.brokers.broker_manager.container.portfolio_crud')
    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_create_broker_already_exists(
        self, mock_broker_crud, mock_portfolio_crud,
        broker_manager, mock_portfolio
    ):
        """测试创建已存在的Broker"""
        mock_portfolio_instance = Mock()
        mock_portfolio_instance.uuid = mock_portfolio.uuid
        mock_portfolio_crud.return_value.get.return_value = mock_portfolio_instance

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = Mock(
            uuid="existing-broker"
        )

        success = broker_manager.create_broker(
            portfolio_id=mock_portfolio.uuid,
            live_account_id="test-account"
        )

        assert success is False

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    @patch('ginkgo.trading.brokers.okx_broker.OKXBroker')
    @patch('ginkgo.trading.brokers.okx_broker.get_encryption_service')
    @patch('ginkgo.trading.brokers.broker_manager.container.live_account_crud')
    def test_start_broker_success(
        self, mock_live_account_crud, mock_encryption, mock_okx_broker_class, mock_broker_crud, broker_manager
    ):
        """测试启动Broker成功"""
        broker_uuid = "test-broker-uuid"

        # Mock live account
        mock_live_account = Mock()
        mock_live_account.uuid = "test-account"
        mock_live_account.exchange = "okx"
        mock_live_account.environment = "testnet"
        mock_live_account.api_key = "encrypted-key"
        mock_live_account.api_secret = "encrypted-secret"
        mock_live_account.passphrase = "encrypted-pass"
        mock_live_account_crud.return_value.get_live_account_by_uuid.return_value = mock_live_account

        # Mock broker instance
        mock_broker = Mock()
        mock_broker.portfolio_id = "test-portfolio"
        mock_broker.live_account_id = "test-account"
        mock_broker.uuid = broker_uuid
        mock_broker.state = BrokerStateType.UNINITIALIZED

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = mock_broker

        # Mock encryption service
        mock_enc_service = Mock()
        mock_enc_service.decrypt.side_effect = lambda x: x.replace("encrypted-", "")
        mock_encryption.return_value = mock_enc_service

        # Mock OKXBroker
        mock_okx_instance = Mock()
        mock_okx_instance.connect.return_value = True
        mock_okx_instance.is_connected.return_value = True
        mock_okx_broker_class.return_value = mock_okx_instance

        # 手动添加broker到内存中（因为start_broker会检查）
        broker_manager._brokers[broker_uuid] = mock_okx_instance

        success = broker_manager.start_broker(mock_broker.portfolio_id)

        assert success is True

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_stop_broker_success(self, mock_broker_crud, broker_manager):
        """测试停止Broker成功"""
        portfolio_id = "test-portfolio"

        mock_broker = Mock()
        mock_broker.uuid = "test-broker-uuid"
        mock_broker.portfolio_id = portfolio_id
        mock_broker.state = BrokerStateType.RUNNING

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = mock_broker
        mock_broker_crud.return_value.update_broker_instance_status.return_value = True

        success = broker_manager.stop_broker(portfolio_id)

        assert success is True

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_pause_broker_success(self, mock_broker_crud, broker_manager):
        """测试暂停Broker成功"""
        portfolio_id = "test-portfolio"

        mock_broker = Mock()
        mock_broker.portfolio_id = portfolio_id
        mock_broker.uuid = "test-broker-uuid"
        mock_broker.state = BrokerStateType.RUNNING

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = mock_broker
        mock_broker_crud.return_value.update_broker_instance_status.return_value = True

        success = broker_manager.pause_broker(portfolio_id)

        assert success is True

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_resume_broker_success(self, mock_broker_crud, broker_manager):
        """测试恢复Broker成功"""
        portfolio_id = "test-portfolio"

        mock_broker = Mock()
        mock_broker.portfolio_id = portfolio_id
        mock_broker.uuid = "test-broker-uuid"
        mock_broker.state = BrokerStateType.PAUSED

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = mock_broker
        mock_broker_crud.return_value.update_broker_instance_status.return_value = True

        success = broker_manager.resume_broker(portfolio_id)

        assert success is True

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_pause_broker_invalid_state(self, mock_broker_crud, broker_manager):
        """测试暂停非运行状态的Broker"""
        portfolio_id = "test-portfolio"

        mock_broker = Mock()
        mock_broker.portfolio_id = portfolio_id
        mock_broker.uuid = "test-broker-uuid"
        mock_broker.state = BrokerStateType.STOPPED  # 已停止，不能暂停

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = mock_broker

        success = broker_manager.pause_broker(portfolio_id)

        assert success is False

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_emergency_stop_all(self, mock_broker_crud, broker_manager):
        """测试紧急停止所有Broker"""
        brokers = [
            Mock(uuid="broker-1", portfolio_id="portfolio-1", state=BrokerStateType.RUNNING),
            Mock(uuid="broker-2", portfolio_id="portfolio-2", state=BrokerStateType.RUNNING),
            Mock(uuid="broker-3", portfolio_id="portfolio-3", state=BrokerStateType.PAUSED),
        ]

        # emergency_stop_all使用get_active_brokers()
        mock_broker_crud.return_value.get_active_brokers.return_value = [
            b for b in brokers if b.state == BrokerStateType.RUNNING
        ]
        mock_broker_crud.return_value.update_broker_instance_status.return_value = True

        stopped_count = broker_manager.emergency_stop_all()

        assert stopped_count == 2  # 只有RUNNING状态的会被停止

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    @patch('ginkgo.trading.brokers.okx_broker.OKXBroker')
    def test_destroy_broker(self, mock_okx_broker_class, mock_broker_crud, broker_manager):
        """测试销毁Broker"""
        portfolio_id = "test-portfolio"

        mock_broker = Mock()
        mock_broker.portfolio_id = portfolio_id
        mock_broker.uuid = "broker-uuid"

        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = mock_broker
        mock_broker_crud.return_value.delete.return_value = True

        # Mock OKXBroker disconnect
        mock_okx_instance = Mock()
        mock_okx_broker_class.return_value = mock_okx_instance

        success = broker_manager.destroy_broker(portfolio_id)

        assert success is True


class TestBrokerManagerErrorHandling:
    """BrokerManager错误处理测试"""

    @pytest.fixture
    def broker_manager(self):
        return BrokerManager()

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_start_broker_not_found(self, mock_broker_crud, broker_manager):
        """测试启动不存在的Broker"""
        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = None

        success = broker_manager.start_broker("non-existent-portfolio")

        assert success is False

    @patch('ginkgo.trading.brokers.broker_manager.container.broker_instance_crud')
    def test_stop_broker_not_found(self, mock_broker_crud, broker_manager):
        """测试停止不存在的Broker"""
        mock_broker_crud.return_value.get_broker_by_portfolio.return_value = None

        success = broker_manager.stop_broker("non-existent-portfolio")

        assert success is False
