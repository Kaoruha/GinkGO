"""
UserGroupMappingCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 添加用户组映射关系
- 按用户ID查询所属组
- 检查映射是否存在
- 移除用户与组的映射

测试数据隔离：使用 SOURCE_TYPES.TEST 标记 + 特定 user_uuid 前缀，测试后自动清理
数据库：MySQL (MUserGroupMapping 继承 MMysqlBase)
"""

import pytest

from ginkgo.data.crud.user_group_mapping_crud import UserGroupMappingCRUD
from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 UserGroupMappingCRUD 实例"""
    return UserGroupMappingCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用特定 user_uuid 前缀隔离）"""
    yield
    try:
        crud_instance.remove(filters={"user_uuid__like": "TEST_USER_MAP_INTEG%"})
    except Exception:
        pass


@pytest.fixture
def sample_mapping_params():
    """标准测试用户组映射参数"""
    return {
        "user_uuid": "TEST_USER_MAP_INTEG_001",
        "group_uuid": "TEST_GROUP_MAP_INTEG_001",
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_mapping_batch():
    """批量测试用户组映射参数列表"""
    return [
        {
            "user_uuid": f"TEST_USER_MAP_INTEG_{i:03d}",
            "group_uuid": "TEST_GROUP_MAP_INTEG_001",
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserGroupMappingCRUDAdd:
    """UserGroupMappingCRUD 添加操作集成测试"""

    def test_add_mapping(self, crud_instance, cleanup, sample_mapping_params):
        """添加单条用户组映射，查回验证"""
        mapping = crud_instance.create(**sample_mapping_params)

        assert mapping is not None
        assert mapping.user_uuid == "TEST_USER_MAP_INTEG_001"
        assert mapping.group_uuid == "TEST_GROUP_MAP_INTEG_001"

        # 查回验证
        results = crud_instance.find(
            filters={"user_uuid": "TEST_USER_MAP_INTEG_001", "group_uuid": "TEST_GROUP_MAP_INTEG_001"}
        )
        assert len(results) >= 1

    def test_add_batch_mappings(self, crud_instance, cleanup, sample_mapping_batch):
        """批量添加用户组映射"""
        models = [crud_instance._create_from_params(**p) for p in sample_mapping_batch]
        result = crud_instance.add_batch(models)

        assert len(result) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserGroupMappingCRUDFind:
    """UserGroupMappingCRUD 查询操作集成测试"""

    def test_find_by_user(self, crud_instance, cleanup, sample_mapping_batch):
        """按用户ID查询所属组"""
        models = [crud_instance._create_from_params(**p) for p in sample_mapping_batch]
        crud_instance.add_batch(models)

        results = crud_instance.find_by_user("TEST_USER_MAP_INTEG_000")
        assert len(results) == 1

    def test_check_mapping_exists(self, crud_instance, cleanup, sample_mapping_params):
        """检查映射是否存在"""
        crud_instance.create(**sample_mapping_params)

        exists = crud_instance.check_mapping_exists(
            "TEST_USER_MAP_INTEG_001", "TEST_GROUP_MAP_INTEG_001"
        )
        assert exists is True

        # 检查不存在的映射
        not_exists = crud_instance.check_mapping_exists(
            "NONEXISTENT_USER", "NONEXISTENT_GROUP"
        )
        assert not_exists is False

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"user_uuid": "NONEXISTENT_USER_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserGroupMappingCRUDCountAndRemove:
    """UserGroupMappingCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_mapping_batch):
        """计数操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_mapping_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(filters={"group_uuid": "TEST_GROUP_MAP_INTEG_001"})
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_mapping_batch):
        """删除操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_mapping_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(filters={"user_uuid__like": "TEST_USER_MAP_INTEG%"})
        assert cnt_before == 5

        crud_instance.remove(filters={"user_uuid__like": "TEST_USER_MAP_INTEG%"})

        cnt_after = crud_instance.count(filters={"user_uuid__like": "TEST_USER_MAP_INTEG%"})
        assert cnt_after == 0

    def test_remove_user_from_group(self, crud_instance, cleanup, sample_mapping_params):
        """移除用户与组的映射"""
        crud_instance.create(**sample_mapping_params)

        removed = crud_instance.remove_user_from_group(
            "TEST_USER_MAP_INTEG_001", "TEST_GROUP_MAP_INTEG_001"
        )
        assert removed == 1

        # 验证已删除
        exists = crud_instance.check_mapping_exists(
            "TEST_USER_MAP_INTEG_001", "TEST_GROUP_MAP_INTEG_001"
        )
        assert exists is False
