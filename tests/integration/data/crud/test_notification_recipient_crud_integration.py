"""
NotificationRecipientCRUD 集成测试

测试通知接收人的创建、查询、更新和删除操作。
NotificationRecipientCRUD 继承 BaseCRUD，使用 MNotificationRecipient 模型，存储在 MySQL 中。

注意：MNotificationRecipient 需要 user_id 或 user_group_id 作为外键关联，
集成测试中需要先创建对应用户或用户组，或使用 mock 方式处理。
此处使用直接构造模型方式测试 CRUD 层操作。

测试范围：
1. 插入操作 - add 通知接收人
2. 查询操作 - get_by_name, get_active_recipients, get_by_type
3. 更新操作 - update_by_uuid
4. 删除操作 - remove 清理
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.notification_recipient_crud import NotificationRecipientCRUD
from ginkgo.data.models.model_notification_recipient import MNotificationRecipient
from ginkgo.enums import SOURCE_TYPES, RECIPIENT_TYPES


# 测试用名称标识，用于清理
TEST_RECIPIENT_NAME = "test_integration_recipient"


@pytest.fixture
def crud_instance():
    """创建 NotificationRecipientCRUD 实例"""
    return NotificationRecipientCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据"""
    yield
    try:
        crud_instance.remove(filters={"name": TEST_RECIPIENT_NAME})
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestNotificationRecipientCRUDInsert:
    """1. 通知接收人插入操作测试"""

    def test_add_recipient(self, crud_instance, cleanup):
        """测试添加通知接收人（USER类型，直接构造模型跳过外键约束）"""
        print("\n" + "=" * 60)
        print("开始测试: NotificationRecipientCRUD 添加接收人")
        print("=" * 60)

        # 直接构造模型并添加，user_id 使用占位值
        recipient = MNotificationRecipient(
            name=TEST_RECIPIENT_NAME,
            recipient_type=RECIPIENT_TYPES.USER,
            user_id="00000000000000000000000000000000",  # 占位 UUID
            description="集成测试用接收人",
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(recipient)
        print(f"-> 添加接收人: {recipient.uuid[:8]}...")

        # 验证
        result = crud_instance.get_by_name(TEST_RECIPIENT_NAME)
        assert result is not None, "应查询到添加的接收人"
        assert result.name == TEST_RECIPIENT_NAME
        print("✓ 接收人添加成功")

    def test_add_default_recipient(self, crud_instance, cleanup):
        """测试添加默认通知接收人"""
        print("\n" + "=" * 60)
        print("开始测试: NotificationRecipientCRUD 添加默认接收人")
        print("=" * 60)

        recipient = MNotificationRecipient(
            name=TEST_RECIPIENT_NAME,
            recipient_type=RECIPIENT_TYPES.USER_GROUP,
            user_group_id="00000000000000000000000000000000",  # 占位 UUID
            is_default=True,
            description="默认接收人测试",
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(recipient)
        print(f"-> 添加默认接收人: is_default={recipient.is_default}")

        # 验证默认接收人查询
        defaults = crud_instance.get_default_recipients()
        # 过滤出测试数据
        test_defaults = [r for r in defaults if r.name == TEST_RECIPIENT_NAME]
        assert len(test_defaults) >= 1, "应查询到默认接收人"
        print("✓ 默认接收人添加成功")


@pytest.mark.database
@pytest.mark.integration
class TestNotificationRecipientCRUDQuery:
    """2. 通知接收人查询操作测试"""

    def test_get_by_name(self, crud_instance, cleanup):
        """测试按名称查询接收人"""
        print("\n" + "=" * 60)
        print("开始测试: NotificationRecipientCRUD 按名称查询")
        print("=" * 60)

        # 插入
        recipient = MNotificationRecipient(
            name=TEST_RECIPIENT_NAME,
            recipient_type=RECIPIENT_TYPES.USER,
            user_id="00000000000000000000000000000000",
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(recipient)

        # 查询
        result = crud_instance.get_by_name(TEST_RECIPIENT_NAME)
        print(f"-> 查询结果: {result}")

        assert result is not None, "按名称查询应返回结果"
        assert result.name == TEST_RECIPIENT_NAME
        print("✓ 按名称查询成功")

    def test_get_active_recipients(self, crud_instance, cleanup):
        """测试查询所有启用的接收人"""
        print("\n" + "=" * 60)
        print("开始测试: NotificationRecipientCRUD 查询启用接收人")
        print("=" * 60)

        # 插入
        recipient = MNotificationRecipient(
            name=TEST_RECIPIENT_NAME,
            recipient_type=RECIPIENT_TYPES.USER,
            user_id="00000000000000000000000000000000",
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(recipient)

        # 查询
        results = crud_instance.get_active_recipients()
        print(f"-> 查询到 {len(results)} 条启用接收人")

        assert isinstance(results, list), "应返回列表"
        assert len(results) >= 1, "应至少有1条启用接收人"
        print("✓ 查询启用接收人成功")

    def test_get_by_type(self, crud_instance, cleanup):
        """测试按类型查询接收人"""
        print("\n" + "=" * 60)
        print("开始测试: NotificationRecipientCRUD 按类型查询")
        print("=" * 60)

        # 插入 USER 类型
        recipient = MNotificationRecipient(
            name=TEST_RECIPIENT_NAME,
            recipient_type=RECIPIENT_TYPES.USER,
            user_id="00000000000000000000000000000000",
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(recipient)

        # 按类型查询
        results = crud_instance.get_by_type(RECIPIENT_TYPES.USER)
        print(f"-> USER类型接收人: {len(results)} 条")

        assert isinstance(results, list)
        assert len(results) >= 1, "应至少有1条USER类型接收人"
        print("✓ 按类型查询成功")


@pytest.mark.database
@pytest.mark.integration
class TestNotificationRecipientCRUDDelete:
    """3. 通知接收人删除操作测试"""

    def test_remove_recipient(self, crud_instance, cleanup):
        """测试删除通知接收人"""
        print("\n" + "=" * 60)
        print("开始测试: NotificationRecipientCRUD 删除接收人")
        print("=" * 60)

        # 插入
        recipient = MNotificationRecipient(
            name=TEST_RECIPIENT_NAME,
            recipient_type=RECIPIENT_TYPES.USER,
            user_id="00000000000000000000000000000000",
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(recipient)

        # 确认插入
        result = crud_instance.get_by_name(TEST_RECIPIENT_NAME)
        assert result is not None, "删除前应存在"

        # 删除
        crud_instance.remove(filters={"name": TEST_RECIPIENT_NAME})
        print("-> 删除完成")

        # 验证
        result = crud_instance.get_by_name(TEST_RECIPIENT_NAME)
        assert result is None, "删除后不应查询到"
        print("✓ 删除成功")
