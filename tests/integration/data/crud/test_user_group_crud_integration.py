"""
UserGroupCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 添加用户组
- 按名称模糊查询
- 查询操作
- 计数、删除操作

测试数据隔离：使用 SOURCE_TYPES.TEST 标记 + 特定名称前缀，测试后自动清理
数据库：MySQL (MUserGroup 继承 MMysqlBase)
"""

import pytest

from ginkgo.data.crud.user_group_crud import UserGroupCRUD
from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 UserGroupCRUD 实例"""
    return UserGroupCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用特定名称前缀隔离）"""
    yield
    try:
        # 按名称前缀批量清理
        results = crud_instance.find(filters={"name__like": "TEST_GROUP_INTEG%"})
        for group in results:
            try:
                crud_instance.remove(filters={"uuid": group.uuid})
            except Exception:
                pass
    except Exception:
        pass


@pytest.fixture
def sample_group_params():
    """标准测试用户组参数"""
    return {
        "name": "TEST_GROUP_INTEG_traders",
        "description": "集成测试交易员组",
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_group_batch():
    """批量测试用户组参数列表"""
    return [
        {
            "name": f"TEST_GROUP_INTEG_group_{i}",
            "description": f"集成测试用户组_{i}",
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserGroupCRUDAdd:
    """UserGroupCRUD 添加操作集成测试"""

    def test_add_group(self, crud_instance, cleanup, sample_group_params):
        """添加单条用户组，查回验证"""
        group = crud_instance.create(**sample_group_params)

        assert group is not None
        assert group.name == "TEST_GROUP_INTEG_traders"

        # 查回验证
        results = crud_instance.find(filters={"name": "TEST_GROUP_INTEG_traders"})
        assert len(results) >= 1

    def test_add_batch_groups(self, crud_instance, cleanup, sample_group_batch):
        """批量添加用户组"""
        models = [crud_instance._create_from_params(**p) for p in sample_group_batch]
        result = crud_instance.add_batch(models)

        assert len(result) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserGroupCRUDFind:
    """UserGroupCRUD 查询操作集成测试"""

    def test_find_by_name_pattern(self, crud_instance, cleanup, sample_group_batch):
        """按名称模糊查询用户组"""
        models = [crud_instance._create_from_params(**p) for p in sample_group_batch]
        crud_instance.add_batch(models)

        results = crud_instance.find_by_name_pattern("TEST_GROUP_INTEG%")
        assert len(results) == 5

    def test_find_by_exact_name(self, crud_instance, cleanup, sample_group_params):
        """按精确名称查询用户组"""
        crud_instance.create(**sample_group_params)

        results = crud_instance.find(filters={"name": "TEST_GROUP_INTEG_traders"})
        assert len(results) >= 1
        assert results[0].name == "TEST_GROUP_INTEG_traders"

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"name": "NONEXISTENT_GROUP_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestUserGroupCRUDCountAndRemove:
    """UserGroupCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_group_batch):
        """计数操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_group_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(filters={"name__like": "TEST_GROUP_INTEG%"})
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_group_batch):
        """删除操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_group_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(filters={"name__like": "TEST_GROUP_INTEG%"})
        assert cnt_before == 5

        # 逐条删除
        results = crud_instance.find(filters={"name__like": "TEST_GROUP_INTEG%"})
        for group in results:
            crud_instance.remove(filters={"uuid": group.uuid})

        cnt_after = crud_instance.count(filters={"name__like": "TEST_GROUP_INTEG%"})
        assert cnt_after == 0
