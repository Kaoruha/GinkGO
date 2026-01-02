# Upstream: None
# Downstream: None
# Role: MUserContact模型单元测试验证联系方式初始化、枚举处理、is_primary处理和update方法功能


"""
MUserContact Model Unit Tests

测试覆盖:
- 联系方式初始化（默认值、枚举处理）
- contact_type 枚举转换（int ↔ enum）
- is_primary 和 is_active 字段处理
- update() 方法（str 和 pd.Series 参数）
- get_contact_type_enum() 方法
- __repr__() 字符串表示
"""

import pytest
import pandas as pd
from datetime import datetime

from ginkgo.data.models.model_user_contact import MUserContact
from ginkgo.enums import CONTACT_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestMUserContactBasics:
    """MUserContact 基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        user_id = "test_user_uuid_1234567890ab"
        contact = MUserContact(user_id=user_id)

        assert contact.uuid is not None
        assert contact.user_id == user_id
        assert contact.address == ""
        assert contact.contact_type == CONTACT_TYPES.EMAIL.value
        assert contact.is_primary is False
        assert contact.is_active is True
        assert contact.source == SOURCE_TYPES.OTHER.value
        assert contact.is_del is False

    def test_constructor_requires_user_id(self):
        """测试 user_id 是必需的"""
        with pytest.raises(ValueError, match="user_id is required"):
            MUserContact()

    def test_constructor_with_email_type(self):
        """测试邮箱类型联系方式"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.EMAIL,
            address="test@example.com"
        )

        assert contact.contact_type == CONTACT_TYPES.EMAIL.value
        assert contact.address == "test@example.com"

    def test_constructor_with_discord_type(self):
        """测试Discord类型联系方式"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.DISCORD,
            address="https://discord.com/api/webhooks/123/abc"
        )

        assert contact.contact_type == CONTACT_TYPES.DISCORD.value
        assert contact.address == "https://discord.com/api/webhooks/123/abc"

    def test_constructor_with_is_primary_true(self):
        """测试主联系方式"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            address="primary@example.com",
            is_primary=True
        )

        assert contact.is_primary is True

    def test_constructor_with_is_active_false(self):
        """测试禁用状态的联系方式"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            address="disabled@example.com",
            is_active=False
        )

        assert contact.is_active is False

    def test_full_constructor(self):
        """测试完整参数构造"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.DISCORD,
            address="https://discord.com/api/webhooks/123/abc",
            is_primary=True,
            is_active=True,
            source=SOURCE_TYPES.SIM
        )

        assert contact.user_id == user_id
        assert contact.contact_type == CONTACT_TYPES.DISCORD.value
        assert contact.address == "https://discord.com/api/webhooks/123/abc"
        assert contact.is_primary is True
        assert contact.is_active is True
        assert contact.source == SOURCE_TYPES.SIM.value


@pytest.mark.unit
class TestMUserContactEnumHandling:
    """MUserContact 枚举处理测试"""

    def test_contact_type_enum_conversion(self):
        """测试 contact_type 枚举转换"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.DISCORD
        )

        # int → enum
        enum_result = CONTACT_TYPES.from_int(contact.contact_type)
        assert enum_result == CONTACT_TYPES.DISCORD

        # 通过方法获取枚举
        assert contact.get_contact_type_enum() == CONTACT_TYPES.DISCORD

    def test_contact_type_invalid_value(self):
        """测试无效的 contact_type 值"""
        user_id = "test_user_uuid"
        # 无效值应回退到默认值 EMAIL
        contact = MUserContact(user_id=user_id, contact_type=999)

        assert contact.contact_type == CONTACT_TYPES.EMAIL.value

    def test_all_contact_types(self):
        """测试所有联系方式类型"""
        user_id = "test_user_uuid"
        types = [
            (CONTACT_TYPES.EMAIL, "test@example.com"),
            (CONTACT_TYPES.DISCORD, "https://discord.com/api/webhooks/123/abc"),
        ]

        for contact_type, address in types:
            contact = MUserContact(user_id=user_id, contact_type=contact_type, address=address)
            assert contact.get_contact_type_enum() == contact_type


@pytest.mark.unit
class TestMUserContactUpdate:
    """MUserContact.update() 方法测试"""

    def test_update_with_str_address_only(self):
        """测试只更新地址"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, address="old@example.com")
        contact.update("new@example.com")

        assert contact.address == "new@example.com"
        # 其他字段应保持不变
        assert contact.contact_type == CONTACT_TYPES.EMAIL.value
        assert contact.is_primary is False

    def test_update_with_str_full_params(self):
        """测试完整参数更新"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.EMAIL,
            address="old@example.com",
            is_primary=False,
            is_active=True
        )

        contact.update(
            address="new@example.com",
            contact_type=CONTACT_TYPES.DISCORD,
            is_primary=True,
            is_active=False,
            source=SOURCE_TYPES.LIVE
        )

        assert contact.address == "new@example.com"
        assert contact.contact_type == CONTACT_TYPES.DISCORD.value
        assert contact.is_primary is True
        assert contact.is_active is False
        assert contact.source == SOURCE_TYPES.LIVE.value

    def test_update_with_series(self):
        """测试从 Series 更新"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, address="old@example.com")

        df = pd.Series({
            "address": "updated@example.com",
            "contact_type": CONTACT_TYPES.DISCORD.value,
            "is_primary": True,
            "is_active": False,
            "source": SOURCE_TYPES.SIM.value
        })

        contact.update(df)

        assert contact.address == "updated@example.com"
        assert contact.contact_type == CONTACT_TYPES.DISCORD.value
        assert contact.is_primary is True
        assert contact.is_active is False
        assert contact.source == SOURCE_TYPES.SIM.value

    def test_update_with_series_partial(self):
        """测试从 Series 部分更新"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            address="old@example.com",
            is_primary=False,
            is_active=True
        )

        # 只更新部分字段
        df = pd.Series({
            "address": "new@example.com",
            "is_primary": True
        })

        contact.update(df)

        assert contact.address == "new@example.com"
        assert contact.is_primary is True
        # 其他字段应保持不变
        assert contact.is_active is True

    def test_update_with_series_nan_values(self):
        """测试 Series 中 NaN 值的处理"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            address="old@example.com",
            is_primary=False,
            is_active=True
        )

        # Series 中包含 NaN
        df = pd.Series({
            "address": "new@example.com",
            "contact_type": None,  # NaN
            "is_primary": None,    # NaN
            "is_active": None      # NaN
        })

        contact.update(df)

        assert contact.address == "new@example.com"
        # NaN 值不应更新原值
        assert contact.contact_type == CONTACT_TYPES.EMAIL.value
        assert contact.is_primary is False
        assert contact.is_active is True

    def test_update_changes_update_at(self):
        """测试 update() 会更新 update_at 字段"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, address="test@example.com")
        original_time = contact.update_at

        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.01)

        contact.update("updated@example.com")

        assert contact.update_at > original_time


@pytest.mark.unit
class TestMUserContactMethods:
    """MUserContact 其他方法测试"""

    def test_get_contact_type_enum(self):
        """测试 get_contact_type_enum() 方法"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, contact_type=CONTACT_TYPES.DISCORD)

        enum_result = contact.get_contact_type_enum()

        assert isinstance(enum_result, CONTACT_TYPES)
        assert enum_result == CONTACT_TYPES.DISCORD

    def test_repr_email(self):
        """测试邮箱联系方式的 __repr__()"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.EMAIL,
            address="test@example.com",
            is_active=True
        )

        repr_str = repr(contact)

        assert "MUserContact" in repr_str
        assert "uuid=" in repr_str
        assert "type=EMAIL" in repr_str
        assert "Active" in repr_str

    def test_repr_discord_primary(self):
        """测试Discord主联系方式的 __repr__()"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.DISCORD,
            is_primary=True,
            is_active=True
        )

        repr_str = repr(contact)

        assert "type=DISCORD" in repr_str
        assert "Active" in repr_str
        assert "Primary" in repr_str

    def test_repr_disabled(self):
        """测试禁用联系方式的 __repr__()"""
        user_id = "test_user_uuid"
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.EMAIL,
            is_active=False
        )

        repr_str = repr(contact)

        assert "Disabled" in repr_str

    def test_soft_delete(self):
        """测试软删除功能（继承自 MMysqlBase）"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, address="test@example.com")
        assert contact.is_del is False

        contact.delete()
        assert contact.is_del is True

        contact.cancel_delete()
        assert contact.is_del is False

    def test_set_source(self):
        """测试 set_source 方法（继承自 MMysqlBase）"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, address="test@example.com")

        # 使用枚举设置
        contact.set_source(SOURCE_TYPES.LIVE)
        assert contact.source == SOURCE_TYPES.LIVE.value

        # 使用整数设置
        contact.set_source(SOURCE_TYPES.BACKTEST.value)
        assert contact.source == SOURCE_TYPES.BACKTEST.value


@pytest.mark.unit
class TestMUserContactValidation:
    """MUserContact 验证逻辑测试"""

    def test_email_address_format(self):
        """测试邮箱地址格式（仅存储，不验证格式）"""
        user_id = "test_user_uuid"
        # 模型不验证格式，只存储
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.EMAIL,
            address="invalid-email-format"
        )

        assert contact.address == "invalid-email-format"

    def test_discord_webhook_format(self):
        """测试Discord Webhook格式（仅存储，不验证格式）"""
        user_id = "test_user_uuid"
        # 模型不验证格式，只存储
        contact = MUserContact(
            user_id=user_id,
            contact_type=CONTACT_TYPES.DISCORD,
            address="not-a-webhook-url"
        )

        assert contact.address == "not-a-webhook-url"

    def test_empty_address_allowed(self):
        """测试空地址是允许的"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id, address="")

        assert contact.address == ""

    def test_long_address(self):
        """测试长地址（512字符限制）"""
        user_id = "test_user_uuid"
        long_address = "a" * 512
        contact = MUserContact(user_id=user_id, address=long_address)

        assert contact.address == long_address

    def test_is_primary_defaults_to_false(self):
        """测试 is_primary 默认为 False"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id)

        assert contact.is_primary is False

    def test_is_active_defaults_to_true(self):
        """测试 is_active 默认为 True"""
        user_id = "test_user_uuid"
        contact = MUserContact(user_id=user_id)

        assert contact.is_active is True
