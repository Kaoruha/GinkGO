"""
UserCRUD 集成测试

测试用户的创建、查询、更新和级联软删除操作。
UserCRUD 继承 BaseCRUD，使用 MUser 模型，存储在 MySQL 中。
支持级联软删除（自动清理联系方式和用户组映射）。

测试范围：
1. 插入操作 - create 创建用户
2. 查询操作 - find_by_name, find_active_users, fuzzy_search
3. 更新操作 - modify 更新用户属性
4. 删除操作 - delete 级联软删除
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.crud.user_crud import UserCRUD
from ginkgo.data.models.model_user import MUser
from ginkgo.enums import SOURCE_TYPES, USER_TYPES


# 测试用用户名
TEST_USERNAME = "test_integration_user"


@pytest.fixture
def crud_instance():
    """创建 UserCRUD 实例"""
    return UserCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（软删除）"""
    yield
    try:
        crud_instance.delete(filters={"username": TEST_USERNAME})
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestUserCRUDInsert:
    """1. 用户插入操作测试"""

    def test_create_user(self, crud_instance, cleanup):
        """测试创建用户"""
        print("\n" + "=" * 60)
        print("开始测试: UserCRUD 创建用户")
        print("=" * 60)

        user = crud_instance.create(
            username=TEST_USERNAME,
            display_name="集成测试用户",
            email="test_integration@example.com",
            user_type=USER_TYPES.PERSON,
            source=SOURCE_TYPES.TEST
        )
        print(f"-> 创建用户: {user.username}, uuid={user.uuid[:8]}...")

        assert user is not None, "创建用户应返回非 None"
        assert user.username == TEST_USERNAME, "用户名应匹配"
        assert user.is_active is True, "新用户应默认激活"
        print("✓ 用户创建成功")

    def test_create_channel_user(self, crud_instance, cleanup):
        """测试创建渠道用户"""
        print("\n" + "=" * 60)
        print("开始测试: UserCRUD 创建渠道用户")
        print("=" * 60)

        user = crud_instance.create(
            username=TEST_USERNAME,
            display_name="测试渠道",
            user_type=USER_TYPES.CHANNEL,
            source=SOURCE_TYPES.TEST
        )
        print(f"-> 创建渠道用户: type={user.user_type}")

        assert user is not None
        user_type_enum = user.get_user_type_enum()
        assert user_type_enum == USER_TYPES.CHANNEL, "用户类型应为 CHANNEL"
        print("✓ 渠道用户创建成功")


@pytest.mark.database
@pytest.mark.integration
class TestUserCRUDQuery:
    """2. 用户查询操作测试"""

    def test_find_by_name(self, crud_instance, cleanup):
        """测试按用户名查询"""
        print("\n" + "=" * 60)
        print("开始测试: UserCRUD 按用户名查询")
        print("=" * 60)

        # 先创建
        crud_instance.create(
            username=TEST_USERNAME,
            display_name="查询测试用户",
            source=SOURCE_TYPES.TEST
        )

        # 按名称查询
        results = crud_instance.find_by_name(TEST_USERNAME)
        print(f"-> 查询到 {len(results)} 个用户")

        assert len(results) >= 1, "应查询到用户"
        assert results[0].username == TEST_USERNAME, "用户名应匹配"
        print("✓ 按名称查询成功")

    def test_find_active_users(self, crud_instance, cleanup):
        """测试查询所有激活用户"""
        print("\n" + "=" * 60)
        print("开始测试: UserCRUD 查询激活用户")
        print("=" * 60)

        # 创建激活用户
        crud_instance.create(
            username=TEST_USERNAME,
            display_name="活跃用户",
            is_active=True,
            source=SOURCE_TYPES.TEST
        )

        # 查询
        results = crud_instance.find_active_users()
        print(f"-> 查询到 {len(results)} 个激活用户")

        assert isinstance(results, list)
        assert len(results) >= 1, "应至少有1个激活用户"
        # 验证结果中都是激活状态
        for u in results:
            assert u.is_active is True, f"用户 {u.username} 应为激活状态"
        print("✓ 查询激活用户成功")

    def test_find_by_user_type(self, crud_instance, cleanup):
        """测试按用户类型查询"""
        print("\n" + "=" * 60)
        print("开始测试: UserCRUD 按用户类型查询")
        print("=" * 60)

        crud_instance.create(
            username=TEST_USERNAME,
            user_type=USER_TYPES.PERSON,
            source=SOURCE_TYPES.TEST
        )

        results = crud_instance.find_by_user_type(USER_TYPES.PERSON)
        print(f"-> PERSON类型用户: {len(results)} 个")

        assert isinstance(results, list)
        assert len(results) >= 1, "应至少有1个PERSON类型用户"
        print("✓ 按用户类型查询成功")


@pytest.mark.database
@pytest.mark.integration
class TestUserCRUDDelete:
    """3. 用户删除操作测试"""

    def test_delete_user_cascade(self, crud_instance, cleanup):
        """测试级联软删除用户"""
        print("\n" + "=" * 60)
        print("开始测试: UserCRUD 级联软删除")
        print("=" * 60)

        # 创建用户
        user = crud_instance.create(
            username=TEST_USERNAME,
            display_name="待删除用户",
            source=SOURCE_TYPES.TEST
        )
        assert user is not None

        # 确认存在
        results = crud_instance.find_by_name(TEST_USERNAME)
        assert len(results) >= 1, "删除前用户应存在"

        # 级联软删除
        count = crud_instance.delete(filters={"username": TEST_USERNAME})
        print(f"-> 软删除 {count} 个用户")

        assert count >= 1, "应删除至少1个用户"

        # 验证已删除
        results = crud_instance.find_by_name(TEST_USERNAME)
        # find 不自动过滤 is_del，但 delete 设置了 is_del=True
        # 通过 find 过滤 is_del=False 验证
        results_active = crud_instance.find(
            filters={"username": TEST_USERNAME, "is_del": False}
        )
        assert len(results_active) == 0, "软删除后 is_del=False 查询应为空"
        print("✓ 级联软删除成功")
