"""
UserContactCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 添加联系方式
- 按用户ID查询联系方式
- 查询启用的联系方式
- 计数、删除操作

测试数据隔离：使用 SOURCE_TYPES.TEST 标记 + 特定 user_id，测试后自动清理
数据库：MySQL (MUserContact 继承 MMysqlBase)
"""

import pytest

from ginkgo.data.crud.user_contact_crud import UserContactCRUD
from ginkgo.enums import SOURCE_TYPES, CONTACT_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 UserContactCRUD 实例"""
    return UserContactCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用 TEST source + 特定 user_id 隔离）"""
    yield
    try:
        crud_instance.remove(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
    except Exception:
        pass


@pytest.fixture
def sample_contact_params():
    """标准测试联系方式参数"""
    return {
        "user_id": "TEST_USER_CONTACT_INTEG",
        "contact_type": CONTACT_TYPES.EMAIL,
        "address": "test_integ@example.com",
        "is_primary": True,
        "is_active": True,
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_contact_batch():
    """批量测试联系方式参数列表"""
    return [
        {
            "user_id": "TEST_USER_CONTACT_INTEG",
            "contact_type": CONTACT_TYPES.EMAIL if i % 2 == 0 else CONTACT_TYPES.DISCORD,
            "address": f"test_contact_{i}@example.com" if i % 2 == 0 else f"https://discord.com/webhook/{i}",
            "is_primary": (i == 0),
            "is_active": True,
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserContactCRUDAdd:
    """UserContactCRUD 添加操作集成测试"""

    def test_add_contact(self, crud_instance, cleanup, sample_contact_params):
        """添加单条联系方式，查回验证"""
        contact = crud_instance.create(**sample_contact_params)

        assert contact is not None
        assert contact.user_id == "TEST_USER_CONTACT_INTEG"
        assert contact.address == "test_integ@example.com"

        # 查回验证
        results = crud_instance.find(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(results) >= 1

    def test_add_batch_contacts(self, crud_instance, cleanup, sample_contact_batch):
        """批量添加联系方式"""
        models = [crud_instance._create_from_params(**p) for p in sample_contact_batch]
        result = crud_instance.add_batch(models)

        assert len(result) == 5

        found = crud_instance.find(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserContactCRUDFind:
    """UserContactCRUD 查询操作集成测试"""

    def test_find_by_user(self, crud_instance, cleanup, sample_contact_batch):
        """按用户ID查询联系方式"""
        models = [crud_instance._create_from_params(**p) for p in sample_contact_batch]
        crud_instance.add_batch(models)

        results = crud_instance.get_by_user("TEST_USER_CONTACT_INTEG")
        assert len(results) == 5

    def test_find_active_contacts(self, crud_instance, cleanup, sample_contact_batch):
        """查询启用的联系方式"""
        models = [crud_instance._create_from_params(**p) for p in sample_contact_batch]
        crud_instance.add_batch(models)

        results = crud_instance.find_active_contacts(user_id="TEST_USER_CONTACT_INTEG")
        assert len(results) == 5

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"user_id": "NONEXISTENT_USER_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserContactCRUDCountAndRemove:
    """UserContactCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_contact_batch):
        """计数操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_contact_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_contact_batch):
        """删除操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_contact_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_before == 5

        crud_instance.remove(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )

        cnt_after = crud_instance.count(
            filters={"user_id": "TEST_USER_CONTACT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_after == 0
