"""
LiveAccountCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 添加实盘账号（使用 create 方法绕过加密服务）
- 按 UUID、用户ID 查询账号
- 分页查询账号列表
- 删除（软删除）操作

测试数据隔离：使用 SOURCE_TYPES.TEST 标记 + 特定 user_id，测试后自动清理
数据库：MySQL (MLiveAccount 继承 MMysqlBase)
"""

import pytest

from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 LiveAccountCRUD 实例"""
    return LiveAccountCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用 TEST source + 特定 user_id 隔离）"""
    yield
    try:
        crud_instance.remove(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
    except Exception:
        pass


@pytest.fixture
def sample_account_params():
    """标准测试实盘账号参数（使用 SOURCE_TYPES.TEST 绕过加密）"""
    return {
        "user_id": "TEST_USER_ACCT_INTEG",
        "exchange": "okx",
        "environment": "testnet",
        "name": "集成测试OKX账号",
        "api_key": "test_encrypted_key_placeholder",
        "api_secret": "test_encrypted_secret_placeholder",
        "status": "disabled",
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_account_batch():
    """批量测试实盘账号参数列表"""
    return [
        {
            "user_id": "TEST_USER_ACCT_INTEG",
            "exchange": "okx" if i % 2 == 0 else "binance",
            "environment": "testnet",
            "name": f"测试账号_{i}",
            "api_key": "test_encrypted_key_placeholder",
            "api_secret": "test_encrypted_secret_placeholder",
            "status": "disabled",
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestLiveAccountCRUDAdd:
    """LiveAccountCRUD 添加操作集成测试"""

    def test_add_single_account(self, crud_instance, cleanup, sample_account_params):
        """添加单条实盘账号，查回验证"""
        account = crud_instance.create(**sample_account_params)

        assert account is not None
        assert account.user_id == "TEST_USER_ACCT_INTEG"
        assert account.name == "集成测试OKX账号"

        # 查回验证
        results = crud_instance.find(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(results) >= 1

    def test_add_batch_accounts(self, crud_instance, cleanup, sample_account_batch):
        """批量添加实盘账号"""
        models = [crud_instance._create_from_params(**p) for p in sample_account_batch]
        result = crud_instance.add_batch(models)

        assert len(result) == 5

        found = crud_instance.find(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestLiveAccountCRUDFind:
    """LiveAccountCRUD 查询操作集成测试"""

    def test_find_by_uuid(self, crud_instance, cleanup, sample_account_params):
        """通过 UUID 查询实盘账号"""
        account = crud_instance.create(**sample_account_params)
        assert account.uuid is not None

        found = crud_instance.get_live_account_by_uuid(account.uuid)
        assert found is not None
        assert found.name == "集成测试OKX账号"

    def test_find_by_user_id(self, crud_instance, cleanup, sample_account_batch):
        """按用户ID查询实盘账号列表"""
        models = [crud_instance._create_from_params(**p) for p in sample_account_batch]
        crud_instance.add_batch(models)

        results = crud_instance.get_live_account_by_user_id("TEST_USER_ACCT_INTEG")
        assert len(results) >= 1

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"user_id": "NONEXISTENT_USER_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestLiveAccountCRUDCountAndRemove:
    """LiveAccountCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_account_batch):
        """计数操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_account_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_account_batch):
        """删除操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_account_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_before == 5

        crud_instance.remove(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )

        cnt_after = crud_instance.count(
            filters={"user_id": "TEST_USER_ACCT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_after == 0
