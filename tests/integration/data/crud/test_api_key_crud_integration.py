"""
ApiKeyCRUD 集成测试

测试 API Key 的创建、查询、更新、删除操作。
ApiKeyCRUD 继承 BaseCRUD，使用 MApiKey 模型，存储在 MySQL 中。

测试范围：
1. 插入操作 - create_api_key 创建 API Key
2. 查询操作 - get_api_key_by_uuid, get_api_keys_by_user, get_all_api_keys
3. 更新操作 - update_api_key 更新 API Key 属性
4. 删除操作 - delete_api_key 软删除 API Key
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.api_key_crud import ApiKeyCRUD
from ginkgo.enums import SOURCE_TYPES


@pytest.fixture
def crud_instance():
    """创建 ApiKeyCRUD 实例"""
    return ApiKeyCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据"""
    yield
    try:
        crud_instance.remove(filters={"name": "test_integration_api_key", "is_del": False})
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestApiKeyCRUDInsert:
    """1. API Key 插入操作测试"""

    def test_create_api_key(self, crud_instance, cleanup):
        """测试创建 API Key"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 创建 API Key")
        print("=" * 60)

        result = crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_integration_key_12345678",
            permissions="read,trade",
            user_id=None,
            description="集成测试用 API Key"
        )
        print(f"-> 创建结果: {result}")

        assert result is not None, "创建 API Key 应返回非 None"
        assert result.name == "test_integration_api_key", "名称应匹配"
        assert result.is_active is True, "新创建的 API Key 应激活"
        assert result.key_prefix is not None, "key_prefix 应生成"
        print("✓ API Key 创建成功")

    def test_create_api_key_with_expiry(self, crud_instance, cleanup):
        """测试创建带过期时间的 API Key"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 创建带过期时间的 API Key")
        print("=" * 60)

        expires_at = datetime.now() + timedelta(days=30)
        result = crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_expiry_key_87654321",
            permissions="read",
            expires_at=expires_at,
            description="带过期时间的测试 Key"
        )
        print(f"-> 创建结果: {result}")

        assert result is not None, "创建 API Key 应返回非 None"
        assert result.expires_at is not None, "过期时间应设置"
        print("✓ 带过期时间的 API Key 创建成功")


@pytest.mark.database
@pytest.mark.integration
class TestApiKeyCRUDQuery:
    """2. API Key 查询操作测试"""

    def test_get_api_key_by_uuid(self, crud_instance, cleanup):
        """测试按 UUID 查询 API Key"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 按 UUID 查询")
        print("=" * 60)

        # 先创建
        created = crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_query_uuid_key",
            permissions="read",
            description="UUID查询测试"
        )
        assert created is not None

        # 按 UUID 查询
        result = crud_instance.get_api_key_by_uuid(created.uuid)
        print(f"-> 查询结果: {result}")

        assert result is not None, "按 UUID 查询应返回结果"
        assert result.uuid == created.uuid, "UUID 应匹配"
        assert result.name == "test_integration_api_key", "名称应匹配"
        print("✓ UUID 查询成功")

    def test_get_all_api_keys(self, crud_instance, cleanup):
        """测试分页查询所有 API Key"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 分页查询所有 API Key")
        print("=" * 60)

        # 创建测试数据
        crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_all_keys_1",
            permissions="read",
            description="分页测试1"
        )
        crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_all_keys_2",
            permissions="read,admin",
            description="分页测试2"
        )

        result = crud_instance.get_all_api_keys(page=1, page_size=10)
        print(f"-> 查询到 {result['total']} 条记录")

        assert "items" in result, "返回结果应包含 items"
        assert "total" in result, "返回结果应包含 total"
        assert isinstance(result["items"], list), "items 应为列表"
        print("✓ 分页查询成功")


@pytest.mark.database
@pytest.mark.integration
class TestApiKeyCRUDUpdate:
    """3. API Key 更新操作测试"""

    def test_update_api_key_permissions(self, crud_instance, cleanup):
        """测试更新 API Key 权限"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 更新权限")
        print("=" * 60)

        # 创建
        created = crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_update_perm_key",
            permissions="read",
            description="更新权限测试"
        )
        assert created is not None

        # 更新权限
        success = crud_instance.update_api_key(
            uuid=created.uuid,
            permissions="read,trade,admin"
        )
        print(f"-> 更新结果: {success}")

        assert success is True, "更新应成功"

        # 验证更新
        updated = crud_instance.get_api_key_by_uuid(created.uuid)
        assert updated is not None
        assert "admin" in updated.permissions, "权限应包含 admin"
        print("✓ 权限更新成功")


@pytest.mark.database
@pytest.mark.integration
class TestApiKeyCRUDDelete:
    """4. API Key 删除操作测试"""

    def test_delete_api_key(self, crud_instance, cleanup):
        """测试软删除 API Key"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 软删除")
        print("=" * 60)

        # 创建
        created = crud_instance.create_api_key(
            name="test_integration_api_key",
            key_value="sk_test_delete_key",
            permissions="read",
            description="删除测试"
        )
        assert created is not None

        # 软删除
        success = crud_instance.delete_api_key(created.uuid)
        print(f"-> 删除结果: {success}")

        assert success is True, "删除应成功"

        # 验证已删除（get_api_key_by_uuid 过滤 is_del=False）
        result = crud_instance.get_api_key_by_uuid(created.uuid)
        assert result is None, "软删除后按 is_del=False 查询应返回 None"
        print("✓ 软删除成功")

    def test_delete_nonexistent_api_key(self, crud_instance):
        """测试删除不存在的 API Key"""
        print("\n" + "=" * 60)
        print("开始测试: ApiKeyCRUD 删除不存在的 Key")
        print("=" * 60)

        success = crud_instance.delete_api_key("nonexistent_uuid_12345678")
        assert success is False, "删除不存在的 Key 应返回 False"
        print("✓ 不存在的 Key 删除返回 False")
