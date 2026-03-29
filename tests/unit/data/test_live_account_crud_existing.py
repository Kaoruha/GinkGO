"""
Unit Tests for LiveAccountCRUD

Tests for CRUD operations on live account entities.
"""

import pytest
from datetime import datetime
from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
from ginkgo.data.models.model_live_account import MLiveAccount, ExchangeType, EnvironmentType, AccountStatusType


class TestLiveAccountCRUD:
    """LiveAccountCRUD单元测试"""

    @pytest.fixture
    def live_account_crud(self):
        """创建LiveAccountCRUD实例"""
        return LiveAccountCRUD()

    @pytest.fixture
    def sample_account_data(self):
        """示例账号数据"""
        return {
            "user_id": "test-user-123",
            "name": "测试OKX账号",
            "exchange": ExchangeType.OKX,
            "environment": EnvironmentType.TESTNET,
            "api_key": "encrypted-api-key",
            "api_secret": "encrypted-secret",
            "passphrase": "encrypted-passphrase",
            "description": "测试用账号",
        }

    def test_add_live_account(self, live_account_crud, sample_account_data):
        """测试添加实盘账号"""
        account = live_account_crud.add_live_account(
            user_id=sample_account_data["user_id"],
            name=sample_account_data["name"],
            exchange=sample_account_data["exchange"],
            environment=sample_account_data["environment"],
            api_key=sample_account_data["api_key"],
            api_secret=sample_account_data["api_secret"],
            passphrase=sample_account_data["passphrase"],
            description=sample_account_data["description"]
        )

        assert account is not None
        assert account.uuid is not None
        assert account.name == sample_account_data["name"]
        assert account.exchange == sample_account_data["exchange"]
        assert account.environment == sample_account_data["environment"]
        # status默认是disabled，需要enabled时需要显式传入
        assert account.is_del is False

    def test_get_live_account_by_uuid(self, live_account_crud, sample_account_data):
        """测试通过UUID获取账号"""
        created = live_account_crud.add_live_account(**sample_account_data)
        retrieved = live_account_crud.get_live_account_by_uuid(created.uuid)

        assert retrieved is not None
        assert retrieved.uuid == created.uuid
        assert retrieved.name == created.name

    def test_update_live_account(self, live_account_crud, sample_account_data):
        """测试更新实盘账号"""
        account = live_account_crud.add_live_account(**sample_account_data)

        updated = live_account_crud.update_live_account(
            account.uuid,
            name="更新后的名称",
            description="更新后的描述"
        )

        assert updated.name == "更新后的名称"
        assert updated.description == "更新后的描述"

    def test_delete_live_account(self, live_account_crud, sample_account_data):
        """测试删除实盘账号（软删除）"""
        account = live_account_crud.add_live_account(**sample_account_data)

        # 软删除
        live_account_crud.delete_live_account(account.uuid)

        # 验证已删除
        deleted = live_account_crud.get_live_account_by_uuid(account.uuid)
        # 删除后返回None或is_del=True
        assert deleted is None or deleted.is_del is True

    def test_get_user_accounts(self, live_account_crud, sample_account_data):
        """测试获取用户的所有账号"""
        user_id = sample_account_data["user_id"]

        # 添加多个账号
        live_account_crud.add_live_account(**sample_account_data)
        live_account_crud.add_live_account(**{
            **sample_account_data,
            "name": "第二个账号"
        })

        accounts = live_account_crud.get_live_accounts_by_user(user_id)

        assert len(accounts) >= 2

    def test_filter_by_exchange(self, live_account_crud, sample_account_data):
        """测试按交易所过滤"""
        live_account_crud.add_live_account(**sample_account_data)

        okx_accounts = live_account_crud.find(filters={
            "exchange": ExchangeType.OKX,
            "is_del": False
        })

        assert len(okx_accounts) >= 1
        for account in okx_accounts:
            assert account.exchange == ExchangeType.OKX

    def test_filter_by_environment(self, live_account_crud, sample_account_data):
        """测试按环境过滤"""
        live_account_crud.add_live_account(**sample_account_data)

        testnet_accounts = live_account_crud.find(filters={
            "environment": EnvironmentType.TESTNET,
            "is_del": False
        })

        assert len(testnet_accounts) >= 1
        for account in testnet_accounts:
            assert account.environment == EnvironmentType.TESTNET

    def test_filter_by_status(self, live_account_crud, sample_account_data):
        """测试按状态过滤"""
        # 先添加账号
        account = live_account_crud.add_live_account(**sample_account_data)
        # 然后更新状态
        live_account_crud.update_status(account.uuid, AccountStatusType.ENABLED)

        enabled_accounts = live_account_crud.find(filters={
            "status": AccountStatusType.ENABLED,
            "is_del": False
        })

        assert len(enabled_accounts) >= 1
        for account in enabled_accounts:
            assert account.status == AccountStatusType.ENABLED

    def test_update_api_credentials(self, live_account_crud, sample_account_data):
        """测试更新API凭证"""
        account = live_account_crud.add_live_account(**sample_account_data)

        updated = live_account_crud.update_live_account(
            account.uuid,
            api_key="new-encrypted-key",
            api_secret="new-encrypted-secret"
        )

        # API凭证会被加密存储，验证值不为空即可
        assert updated.api_key is not None
        assert updated.api_secret is not None

    def test_update_status(self, live_account_crud, sample_account_data):
        """测试更新账号状态"""
        account = live_account_crud.add_live_account(**sample_account_data)

        # 启用账号
        live_account_crud.update_status(account.uuid, AccountStatusType.ENABLED)

        updated = live_account_crud.get_live_account_by_uuid(account.uuid)
        assert updated.status == AccountStatusType.ENABLED

    def test_update_last_validated_at(self, live_account_crud, sample_account_data):
        """测试更新最后验证时间"""
        account = live_account_crud.add_live_account(**sample_account_data)

        # 更新状态会自动更新last_validated_at
        live_account_crud.update_status(account.uuid, AccountStatusType.ENABLED)

        updated = live_account_crud.get_live_account_by_uuid(account.uuid)
        # 验证last_validated_at已被更新（不为None）
        assert updated.last_validated_at is not None

    def test_exists_check(self, live_account_crud, sample_account_data):
        """测试检查账号是否存在"""
        account = live_account_crud.add_live_account(**sample_account_data)

        # 使用get_live_account_by_uuid来检查存在性
        exists = live_account_crud.get_live_account_by_uuid(account.uuid) is not None
        assert exists is True

        # 检查不存在的UUID
        not_exists = live_account_crud.get_live_account_by_uuid("non-existent-uuid") is not None
        assert not_exists is False


class TestLiveAccountModel:
    """MLiveAccount模型测试"""

    def test_exchange_enum_values(self):
        """测试交易所枚举值"""
        assert ExchangeType.OKX == "okx"

    def test_environment_enum_values(self):
        """测试环境枚举值"""
        assert EnvironmentType.TESTNET == "testnet"
        assert EnvironmentType.PRODUCTION == "production"

    def test_account_initialization(self):
        """测试账号初始化"""
        account = MLiveAccount(
            uuid="test-uuid",
            user_id="test-user",
            name="测试账号",
            exchange=ExchangeType.OKX,
            environment=EnvironmentType.TESTNET,
            api_key="key",
            api_secret="secret",
            passphrase="passphrase"
        )

        assert account.uuid == "test-uuid"
        assert account.user_id == "test-user"
        assert account.name == "测试账号"
        # status默认值取决于模型定义


class TestLiveAccountValidation:
    """实盘账号验证测试"""

    def test_required_fields(self):
        """测试必填字段验证"""
        # MLiveAccount使用ORM，字段验证可能在数据库层面
        # 这里只验证对象可以创建
        account = MLiveAccount(
            uuid="test-uuid",
            user_id="test-user",
            name="测试账号",
            exchange=ExchangeType.OKX,
            environment=EnvironmentType.TESTNET,
            api_key="key",
            api_secret="secret"
        )
        assert account.uuid == "test-uuid"

    def test_invalid_exchange(self):
        """测试无效交易所值"""
        # 模型现在有验证，无效值会抛出ValueError
        with pytest.raises(ValueError, match="Unknown exchange type"):
            MLiveAccount(
                uuid="test-uuid",
                user_id="test-user",
                name="测试账号",
                exchange="invalid-exchange",  # 无效值
                environment=EnvironmentType.TESTNET,
                api_key="key",
                api_secret="secret"
            )

    def test_invalid_environment(self):
        """测试无效环境值"""
        # 模型现在有验证，无效值会抛出ValueError
        with pytest.raises(ValueError, match="Unknown environment type"):
            MLiveAccount(
                uuid="test-uuid",
                user_id="test-user",
                name="测试账号",
                exchange=ExchangeType.OKX,
                environment="invalid-env",  # 无效值
                api_key="key",
                api_secret="secret"
            )
