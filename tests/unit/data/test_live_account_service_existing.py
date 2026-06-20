"""
性能: 219MB RSS, 1.93s, 31 tests [PASS]
Unit Tests for LiveAccountService

Tests for live account business logic including:
- Account creation with validation
- Temporary credential validation
- Account status management
- Balance and position queries
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from ginkgo.data.services.live_account_service import LiveAccountService
from ginkgo.data.models.model_live_account import MLiveAccount, ExchangeType, EnvironmentType, AccountStatusType


class TestLiveAccountServiceCreation:
    """测试账号创建相关逻辑"""

    @pytest.fixture
    def mock_crud(self):
        """Mock LiveAccountCRUD"""
        mock = Mock()
        # 默认返回一个模拟账号
        mock_account = Mock(spec=MLiveAccount)
        mock_account.uuid = "test-account-uuid"
        mock_account.name = "测试OKX账号"
        mock_account.exchange = ExchangeType.OKX
        mock_account.environment = EnvironmentType.TESTNET
        mock.add_live_account.return_value = mock_account
        mock.get_live_account_by_user_id.return_value = []
        return mock

    @pytest.fixture
    def live_account_service(self, mock_crud):
        """创建LiveAccountService实例"""
        return LiveAccountService(live_account_crud=mock_crud)

    def test_create_account_success_without_validation(self, live_account_service):
        """测试不验证直接创建账号成功"""
        result = live_account_service.create_account(
            user_id="test-user-123",
            exchange=ExchangeType.OKX,
            name="测试OKX账号",
            api_key="test-api-key",
            api_secret="test-api-secret",
            passphrase="test-passphrase",
            environment="testnet",
            auto_validate=False
        )

        assert result["success"] is True
        assert result["data"]["account_uuid"] == "test-account-uuid"
        assert result["data"]["validation_result"] is None

    def test_create_account_missing_user_id(self, live_account_service):
        """测试缺少user_id参数"""
        result = live_account_service.create_account(
            user_id="",
            exchange=ExchangeType.OKX,
            name="测试账号",
            api_key="key",
            api_secret="secret"
        )

        assert result["success"] is False
        assert "user_id is required" in result["message"]

    def test_create_account_missing_exchange(self, live_account_service):
        """测试缺少exchange参数"""
        result = live_account_service.create_account(
            user_id="test-user",
            exchange="",
            name="测试账号",
            api_key="key",
            api_secret="secret"
        )

        assert result["success"] is False
        assert "exchange is required" in result["message"]

    def test_create_account_unsupported_exchange(self, live_account_service):
        """测试不支持的交易所"""
        result = live_account_service.create_account(
            user_id="test-user",
            exchange="unsupported-exchange",
            name="测试账号",
            api_key="key",
            api_secret="secret"
        )

        assert result["success"] is False
        assert "Unsupported exchange" in result["message"]

    def test_create_account_invalid_environment(self, live_account_service):
        """测试无效的环境"""
        result = live_account_service.create_account(
            user_id="test-user",
            exchange=ExchangeType.OKX,
            name="测试账号",
            api_key="key",
            api_secret="secret",
            environment="invalid-env"
        )

        assert result["success"] is False
        assert "Invalid environment" in result["message"]

    def test_create_account_okx_missing_passphrase(self, live_account_service):
        """测试OKX账号缺少passphrase"""
        result = live_account_service.create_account(
            user_id="test-user",
            exchange=ExchangeType.OKX,
            name="测试OKX账号",
            api_key="key",
            api_secret="secret",
            passphrase=None
        )

        assert result["success"] is False
        assert "passphrase is required for OKX" in result["message"]

    def test_create_account_duplicate_name(self, live_account_service, mock_crud):
        """测试账号名称重复"""
        # Mock返回重复名称的账号
        existing_account = Mock(spec=MLiveAccount)
        existing_account.name = "测试OKX账号"
        mock_crud.get_live_account_by_user_id.return_value = [existing_account]

        result = live_account_service.create_account(
            user_id="test-user",
            exchange=ExchangeType.OKX,
            name="测试OKX账号",  # 重复名称
            api_key="key",
            api_secret="secret",
            passphrase="passphrase"
        )

        assert result["success"] is False
        assert "Account name already exists" in result["message"]

    @patch('ginkgo.data.services.live_account_service.LiveAccountService._validate_credentials_temporarily')
    def test_create_account_with_validation_success(self, mock_validate, live_account_service):
        """测试验证成功后创建账号"""
        # Mock验证成功
        mock_validate.return_value = {
            "success": True,
            "message": "API validation successful"
        }

        result = live_account_service.create_account(
            user_id="test-user",
            exchange=ExchangeType.OKX,
            name="测试OKX账号",
            api_key="key",
            api_secret="secret",
            passphrase="passphrase",
            auto_validate=True
        )

        assert result["success"] is True
        assert result["data"]["account_uuid"] == "test-account-uuid"
        assert result["data"]["validation_result"]["success"] is True
        # 验证validate_account被调用过
        mock_validate.assert_called_once()

    @patch('ginkgo.data.services.live_account_service.LiveAccountService._validate_credentials_temporarily')
    def test_create_account_with_validation_failure_rejects_creation(self, mock_validate, live_account_service, mock_crud):
        """测试验证失败拒绝创建账号（不入库）"""
        # Mock验证失败
        mock_validate.return_value = {
            "success": False,
            "error": "Invalid API credentials"
        }

        result = live_account_service.create_account(
            user_id="test-user",
            exchange=ExchangeType.OKX,
            name="测试OKX账号",
            api_key="invalid-key",
            api_secret="invalid-secret",
            passphrase="passphrase",
            auto_validate=True
        )

        assert result["success"] is False
        assert "API validation failed" in result["message"]
        # 关键：验证add_live_account没有被调用（不入库）
        mock_crud.add_live_account.assert_not_called()


class TestTemporaryCredentialValidation:
    """测试临时凭证验证逻辑"""

    @pytest.fixture
    def live_account_service(self):
        """创建LiveAccountService实例"""
        mock_crud = Mock()
        return LiveAccountService(live_account_crud=mock_crud)

    @patch('ginkgo.data.services.live_account_service.LiveAccountService._temp_validate_okx')
    def test_temporary_validate_okx_success(self, mock_okx_validate, live_account_service):
        """测试OKX临时验证成功"""
        mock_okx_validate.return_value = {
            "success": True,
            "message": "API validation successful",
            "account_info": {"balance": "1000.0"}
        }

        result = live_account_service._validate_credentials_temporarily(
            exchange=ExchangeType.OKX,
            api_key="test-key",
            api_secret="test-secret",
            passphrase="test-passphrase",
            environment="testnet"
        )

        assert result["success"] is True
        assert "balance" in result["account_info"]
        mock_okx_validate.assert_called_once()

    @patch('requests.get')
    def test_temp_validate_binance_success(self, mock_get, live_account_service):
        """#5879: Binance 临时验证应用 HMAC-SHA256 签名调用 /api/v3/account,
        200 返回时判为有效并解析余额。验证连通性契约(端点/签名/APIKey头)。"""
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "balances": [
                {"asset": "BTC", "free": "1.5"},
                {"asset": "USDT", "free": "100"},
            ]
        }
        mock_get.return_value = mock_resp

        result = live_account_service._temp_validate_binance(
            api_key="test-key",
            api_secret="test-secret",
            environment="testnet"
        )

        assert result["success"] is True
        assert result["account_info"]["exchange"] == "binance"
        assert "balance" in result["account_info"]
        # 连通性契约: 命中 testnet 端点
        called_url = mock_get.call_args.args[0]
        assert "testnet.binance.vision" in called_url
        # 带签名与 APIKey 头
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("X-MBX-APIKEY") == "test-key"
        assert "signature" in mock_get.call_args.kwargs.get("params", {})

    @patch('requests.get')
    def test_temp_validate_binance_invalid_key(self, mock_get, live_account_service):
        """#5879: Binance 返回鉴权失败(非 200)时判为无效,返回明确错误。"""
        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"code": -2015, "msg": "Invalid API-key, IP, or permissions"}
        mock_get.return_value = mock_resp

        result = live_account_service._temp_validate_binance(
            api_key="bad-key",
            api_secret="bad-secret",
            environment="production"
        )

        assert result["success"] is False
        assert "Invalid API-key" in result["error"]
        # 生产环境命中正式端点
        assert "api.binance.com" in mock_get.call_args.args[0]

    def test_temporary_validate_unsupported_exchange(self, live_account_service):
        """测试不支持的交易所"""
        result = live_account_service._validate_credentials_temporarily(
            exchange="unsupported",
            api_key="key",
            api_secret="secret",
            passphrase=None,
            environment="testnet"
        )

        assert result["success"] is False
        assert "Unsupported exchange" in result["message"]


class TestTempValidateOKX:
    """测试OKX临时验证方法"""

    @pytest.fixture
    def live_account_service(self):
        """创建LiveAccountService实例"""
        mock_crud = Mock()
        return LiveAccountService(live_account_crud=mock_crud)

    @patch('okx.Account.AccountAPI')
    def test_temp_validate_okx_success(self, mock_okx_account, live_account_service):
        """测试OKX验证成功"""
        # Mock API响应
        mock_api_instance = Mock()
        mock_api_instance.get_account_balance.return_value = {
            "code": "0",
            "data": [{"totalEq": "1000.50"}]
        }
        mock_okx_account.return_value = mock_api_instance

        result = live_account_service._temp_validate_okx(
            api_key="test-key",
            api_secret="test-secret",
            passphrase="test-passphrase",
            environment="testnet"
        )

        assert result["success"] is True
        assert result["account_info"]["balance"] == "1000.50"
        assert result["account_info"]["exchange"] == "okx"
        assert result["account_info"]["environment"] == "testnet"

    @patch('okx.Account.AccountAPI')
    def test_temp_validate_okx_api_error(self, mock_okx_account, live_account_service):
        """测试OKX API返回错误"""
        mock_api_instance = Mock()
        mock_api_instance.get_account_balance.return_value = {
            "code": "50001",
            "msg": "Invalid API key",
            "data": []
        }
        mock_okx_account.return_value = mock_api_instance

        result = live_account_service._temp_validate_okx(
            api_key="invalid-key",
            api_secret="invalid-secret",
            passphrase="test-passphrase",
            environment="testnet"
        )

        assert result["success"] is False
        # _temp_validate_okx返回的键是"error"不是"message"
        assert "Invalid API key" in result["error"]

    @patch('okx.Account.AccountAPI')
    def test_temp_validate_okx_no_response(self, mock_okx_account, live_account_service):
        """测试OKX API无响应"""
        mock_api_instance = Mock()
        mock_api_instance.get_account_balance.return_value = None
        mock_okx_account.return_value = mock_api_instance

        result = live_account_service._temp_validate_okx(
            api_key="test-key",
            api_secret="test-secret",
            passphrase="test-passphrase",
            environment="testnet"
        )

        assert result["success"] is False

    def test_temp_validate_okx_missing_passphrase(self, live_account_service):
        """测试OKX验证缺少passphrase"""
        result = live_account_service._temp_validate_okx(
            api_key="test-key",
            api_secret="test-secret",
            passphrase=None,  # 缺少passphrase
            environment="testnet"
        )

        assert result["success"] is False
        assert "Passphrase is required" in result["message"]  # _error_result返回的是message


class TestValidateBinanceAccount:
    """#5879: 测试 Binance 已存账户验证(_validate_binance_account)"""

    @pytest.fixture
    def mock_crud(self):
        return Mock()

    @pytest.fixture
    def live_account_service(self, mock_crud):
        return LiveAccountService(live_account_crud=mock_crud)

    @patch('requests.get')
    def test_validate_binance_account_success_enables(
        self, mock_get, live_account_service, mock_crud
    ):
        """验证成功应落库 ENABLED 并返回 valid=True。"""
        account = Mock(spec=MLiveAccount)
        account.uuid = "binance-uuid"
        account.is_testnet.return_value = True
        account.environment = EnvironmentType.TESTNET

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"balances": [{"asset": "USDT", "free": "500"}]}
        mock_get.return_value = mock_resp

        result = live_account_service._validate_binance_account(
            account, credentials={"api_key": "k", "api_secret": "s"}
        )

        assert result["success"] is True
        assert result["valid"] is True
        assert result["account_info"]["exchange"] == "binance"
        # 成功落库 ENABLED
        mock_crud.update_status.assert_called_once()
        call_args = mock_crud.update_status.call_args
        assert call_args.args[0] == "binance-uuid"
        assert call_args.args[1] == AccountStatusType.ENABLED

    @patch('requests.get')
    def test_validate_binance_account_invalid_marks_error(
        self, mock_get, live_account_service, mock_crud
    ):
        """鉴权失败应落库 ERROR 并返回 valid=False。"""
        account = Mock(spec=MLiveAccount)
        account.uuid = "binance-uuid"
        account.is_testnet.return_value = False
        account.environment = EnvironmentType.PRODUCTION

        mock_resp = Mock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"code": -2015, "msg": "Invalid API-key"}
        mock_get.return_value = mock_resp

        result = live_account_service._validate_binance_account(
            account, credentials={"api_key": "bad", "api_secret": "bad"}
        )

        assert result["success"] is False
        assert result["valid"] is False
        call_args = mock_crud.update_status.call_args
        assert call_args.args[1] == AccountStatusType.ERROR


class TestAccountStatusManagement:
    """测试账号状态管理"""

    @pytest.fixture
    def mock_crud(self):
        """Mock LiveAccountCRUD"""
        mock = Mock()
        mock_account = Mock(spec=MLiveAccount)
        mock_account.uuid = "test-uuid"
        mock_account.status = AccountStatusType.DISABLED
        mock.get_live_account_by_uuid.return_value = mock_account

        updated_account = Mock(spec=MLiveAccount)
        updated_account.uuid = "test-uuid"
        updated_account.status = AccountStatusType.ENABLED
        mock.update_status.return_value = updated_account
        return mock

    @pytest.fixture
    def live_account_service(self, mock_crud):
        """创建LiveAccountService实例"""
        return LiveAccountService(live_account_crud=mock_crud)

    def test_update_account_status_to_enabled(self, live_account_service):
        """测试启用账号"""
        result = live_account_service.update_account_status(
            account_uuid="test-uuid",
            status=AccountStatusType.ENABLED
        )

        assert result["success"] is True
        assert result["data"]["status"] == AccountStatusType.ENABLED

    def test_update_account_status_to_disabled(self, live_account_service):
        """测试禁用账号"""
        result = live_account_service.update_account_status(
            account_uuid="test-uuid",
            status=AccountStatusType.DISABLED
        )

        assert result["success"] is True

    def test_update_account_status_invalid_status(self, live_account_service):
        """测试无效状态"""
        result = live_account_service.update_account_status(
            account_uuid="test-uuid",
            status="invalid-status"
        )

        assert result["success"] is False
        assert "Invalid status" in result["message"]

    def test_update_account_status_not_found(self, live_account_service, mock_crud):
        """测试账号不存在"""
        mock_crud.get_live_account_by_uuid.return_value = None

        result = live_account_service.update_account_status(
            account_uuid="non-existent-uuid",
            status=AccountStatusType.ENABLED
        )

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_record_validation_failure_persists_via_crud(self, live_account_service, mock_crud):
        """#5782: 超时/异常时记录验证失败,必须下发 CRUD 带 validation_message,
        使 validation_status 与 last_validated_at 落库(不再恒 None)。"""
        result = live_account_service.record_validation_failure(
            account_uuid="test-uuid", message="Validation timed out"
        )

        assert result["success"] is True
        # 关键: 下发 ERROR 状态 + 失败消息(驱动两字段落库)
        mock_crud.update_status.assert_called_once_with(
            "test-uuid", AccountStatusType.ERROR, validation_message="Validation timed out"
        )

    def test_record_validation_failure_account_not_found(self, live_account_service, mock_crud):
        """#5782: 账号不存在时记录失败应返回不成功,且不抛异常。"""
        mock_crud.update_status.return_value = None

        result = live_account_service.record_validation_failure(
            account_uuid="non-existent", message="timed out"
        )

        assert result["success"] is False


class TestGetUserAccounts:
    """测试获取用户账号列表"""

    @pytest.fixture
    def mock_crud(self):
        """Mock LiveAccountCRUD"""
        mock = Mock()
        mock_accounts = [
            Mock(uuid="uuid1", name="账号1", exchange=ExchangeType.OKX),
            Mock(uuid="uuid2", name="账号2", exchange=ExchangeType.BINANCE)
        ]
        mock.get_live_accounts_by_user.return_value = {
            "accounts": mock_accounts,
            "total": 2,
            "page": 1,
            "page_size": 20,
            "total_pages": 1
        }
        return mock

    @pytest.fixture
    def live_account_service(self, mock_crud):
        """创建LiveAccountService实例"""
        return LiveAccountService(live_account_crud=mock_crud)

    def test_get_user_accounts_success(self, live_account_service):
        """测试获取用户账号列表成功"""
        result = live_account_service.get_user_accounts(
            user_id="test-user-123",
            page=1,
            page_size=20
        )

        assert result["success"] is True
        assert len(result["data"]["accounts"]) == 2
        assert result["data"]["total"] == 2

    def test_get_user_accounts_with_exchange_filter(self, live_account_service, mock_crud):
        """测试按交易所过滤"""
        live_account_service.get_user_accounts(
            user_id="test-user-123",
            exchange=ExchangeType.OKX
        )

        # 验证传递了exchange参数
        mock_crud.get_live_accounts_by_user.assert_called_once()
        call_kwargs = mock_crud.get_live_accounts_by_user.call_args[1]
        assert call_kwargs["exchange"] == ExchangeType.OKX

    def test_get_user_accounts_with_environment_filter(self, live_account_service, mock_crud):
        """测试按环境过滤"""
        live_account_service.get_user_accounts(
            user_id="test-user-123",
            environment="testnet"
        )

        call_kwargs = mock_crud.get_live_accounts_by_user.call_args[1]
        assert call_kwargs["environment"] == "testnet"

    def test_get_user_accounts_with_status_filter(self, live_account_service, mock_crud):
        """测试按状态过滤"""
        live_account_service.get_user_accounts(
            user_id="test-user-123",
            status=AccountStatusType.ENABLED
        )

        call_kwargs = mock_crud.get_live_accounts_by_user.call_args[1]
        assert call_kwargs["status"] == AccountStatusType.ENABLED


class TestDeleteAccount:
    """测试删除账号"""

    @pytest.fixture
    def mock_crud(self):
        """Mock LiveAccountCRUD"""
        mock = Mock()
        mock.delete_live_account.return_value = True
        return mock

    @pytest.fixture
    def live_account_service(self, mock_crud):
        """创建LiveAccountService实例"""
        return LiveAccountService(live_account_crud=mock_crud)

    def test_delete_account_success(self, live_account_service):
        """测试删除账号成功"""
        result = live_account_service.delete_account(
            account_uuid="test-uuid"
        )

        assert result["success"] is True
        assert "deleted successfully" in result["message"]

    def test_delete_account_not_found(self, live_account_service, mock_crud):
        """测试删除不存在的账号"""
        mock_crud.delete_live_account.return_value = False

        result = live_account_service.delete_account(
            account_uuid="non-existent-uuid"
        )

        assert result["success"] is False
        assert "not found" in result["message"]


class TestGetAccountByUUID:
    """测试通过UUID获取账号"""

    @pytest.fixture
    def mock_crud(self):
        """Mock LiveAccountCRUD"""
        mock = Mock()
        mock_account = Mock(spec=MLiveAccount)
        mock_account.uuid = "test-uuid"
        mock_account.name = "测试账号"
        mock_account.to_dict.return_value = {
            "uuid": "test-uuid",
            "name": "测试账号",
            "exchange": "okx"
        }
        mock.get_live_account_by_uuid.return_value = mock_account
        return mock

    @pytest.fixture
    def live_account_service(self, mock_crud):
        """创建LiveAccountService实例"""
        return LiveAccountService(live_account_crud=mock_crud)

    def test_get_account_by_uuid_success(self, live_account_service):
        """测试获取账号成功"""
        result = live_account_service.get_account_by_uuid(
            account_uuid="test-uuid"
        )

        assert result["success"] is True
        assert result["data"]["uuid"] == "test-uuid"
        assert result["data"]["name"] == "测试账号"

    def test_get_account_by_uuid_not_found(self, live_account_service, mock_crud):
        """测试获取不存在的账号"""
        mock_crud.get_live_account_by_uuid.return_value = None

        result = live_account_service.get_account_by_uuid(
            account_uuid="non-existent-uuid"
        )

        assert result["success"] is False
        assert "not found" in result["message"]


class TestUpdateAccount:
    """测试更新账号信息"""

    @pytest.fixture
    def mock_crud(self):
        """Mock LiveAccountCRUD"""
        mock = Mock()
        mock_account = Mock(spec=MLiveAccount)
        mock_account.uuid = "test-uuid"
        mock_account.name = "更新后的名称"
        mock_account.to_dict.return_value = {
            "uuid": "test-uuid",
            "name": "更新后的名称"
        }
        mock.update_live_account.return_value = mock_account
        return mock

    @pytest.fixture
    def live_account_service(self, mock_crud):
        """创建LiveAccountService实例"""
        return LiveAccountService(live_account_crud=mock_crud)

    def test_update_account_name(self, live_account_service):
        """测试更新账号名称"""
        result = live_account_service.update_account(
            account_uuid="test-uuid",
            name="更新后的名称"
        )

        assert result["success"] is True
        assert result["data"]["name"] == "更新后的名称"

    def test_update_account_not_found(self, live_account_service, mock_crud):
        """测试更新不存在的账号"""
        mock_crud.update_live_account.return_value = None

        result = live_account_service.update_account(
            account_uuid="non-existent-uuid",
            name="新名称"
        )

        assert result["success"] is False
        assert "not found" in result["message"]

    def test_update_account_applies_status(self, live_account_service, mock_crud):
        """#5789: update_account 接收的 status 应实际更新账户状态，而非静默丢弃。

        表象: PUT /accounts/{id} 传 status 返回成功但状态未变。
        根因: handler 遗漏透传 + service 无 status 参数。
        行为契约: status 必须下发给 CRUD 实际生效。
        """
        result = live_account_service.update_account(
            account_uuid="test-uuid",
            status=AccountStatusType.ENABLED,
        )

        assert result["success"] is True
        # status 必须下发给 CRUD（实际生效），证明未被静默丢弃
        mock_crud.update_status.assert_called_once_with(
            "test-uuid", AccountStatusType.ENABLED
        )


class TestErrorResultHelper:
    """测试错误结果辅助方法"""

    @pytest.fixture
    def live_account_service(self):
        """创建LiveAccountService实例"""
        mock_crud = Mock()
        return LiveAccountService(live_account_crud=mock_crud)

    def test_error_result_format(self, live_account_service):
        """测试错误结果格式"""
        result = live_account_service._error_result("Test error message")

        assert result["success"] is False
        assert result["message"] == "Test error message"
        assert result["data"] is None
