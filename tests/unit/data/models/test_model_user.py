# Upstream: None
# Downstream: None
# Role: MUser模型单元测试验证用户初始化、枚举处理、update方法和关系映射功能


"""
MUser Model Unit Tests

测试覆盖:
- 用户初始化（默认值、枚举处理）
- user_type 枚举转换（int ↔ enum）
- is_active 字段处理
- update() 方法（str 和 pd.Series 参数）
- get_user_type_enum() 方法
- __repr__() 字符串表示
"""

import pytest
import pandas as pd
from datetime import datetime

from ginkgo.data.models.model_user import MUser
from ginkgo.enums import USER_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestMUserBasics:
    """MUser 基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        user = MUser()

        assert user.uuid is not None
        assert user.name == ""
        assert user.user_type == USER_TYPES.PERSON.value
        assert user.is_active is True
        assert user.source == SOURCE_TYPES.OTHER.value
        assert user.is_del is False

    def test_constructor_with_name(self):
        """测试带名称的构造"""
        user = MUser(name="Test User")

        assert user.name == "Test User"
        assert user.user_type == USER_TYPES.PERSON.value
        assert user.is_active is True

    def test_constructor_with_user_type_enum(self):
        """测试带枚举类型参数的构造"""
        user = MUser(name="Channel User", user_type=USER_TYPES.CHANNEL)

        assert user.user_type == USER_TYPES.CHANNEL.value
        assert user.get_user_type_enum() == USER_TYPES.CHANNEL

    def test_constructor_with_user_type_int(self):
        """测试带整数类型参数的构造"""
        user = MUser(name="Org User", user_type=USER_TYPES.ORGANIZATION.value)

        assert user.user_type == USER_TYPES.ORGANIZATION.value
        assert user.get_user_type_enum() == USER_TYPES.ORGANIZATION

    def test_constructor_with_is_active_false(self):
        """测试禁用状态的构造"""
        user = MUser(name="Inactive User", is_active=False)

        assert user.is_active is False

    def test_constructor_with_source(self):
        """测试带数据源的构造"""
        user = MUser(name="Sim User", source=SOURCE_TYPES.SIM)

        assert user.source == SOURCE_TYPES.SIM.value

    def test_full_constructor(self):
        """测试完整参数构造"""
        user = MUser(
            name="Full User",
            user_type=USER_TYPES.ORGANIZATION,
            is_active=True,
            source=SOURCE_TYPES.BACKTEST
        )

        assert user.name == "Full User"
        assert user.user_type == USER_TYPES.ORGANIZATION.value
        assert user.is_active is True
        assert user.source == SOURCE_TYPES.BACKTEST.value


@pytest.mark.unit
class TestMUserEnumHandling:
    """MUser 枚举处理测试"""

    def test_user_type_enum_conversion(self):
        """测试 user_type 枚举转换"""
        user = MUser(name="Test", user_type=USER_TYPES.CHANNEL)

        # int → enum
        enum_result = USER_TYPES.from_int(user.user_type)
        assert enum_result == USER_TYPES.CHANNEL

        # 通过方法获取枚举
        assert user.get_user_type_enum() == USER_TYPES.CHANNEL

    def test_user_type_invalid_value(self):
        """测试无效的 user_type 值"""
        # 无效值应回退到默认值 PERSON
        user = MUser(name="Test", user_type=999)

        assert user.user_type == USER_TYPES.PERSON.value

    def test_all_user_types(self):
        """测试所有用户类型"""
        types = [
            (USER_TYPES.PERSON, "Person User"),
            (USER_TYPES.CHANNEL, "Channel User"),
            (USER_TYPES.ORGANIZATION, "Org User"),
        ]

        for user_type, name in types:
            user = MUser(name=name, user_type=user_type)
            assert user.get_user_type_enum() == user_type


@pytest.mark.unit
class TestMUserUpdate:
    """MUser.update() 方法测试"""

    def test_update_with_str_name_only(self):
        """测试只更新名称"""
        user = MUser(name="Original")
        user.update("Updated Name")

        assert user.name == "Updated Name"
        # 其他字段应保持不变
        assert user.user_type == USER_TYPES.PERSON.value
        assert user.is_active is True

    def test_update_with_str_full_params(self):
        """测试完整参数更新"""
        user = MUser(name="Original", user_type=USER_TYPES.PERSON, is_active=True)

        user.update(
            name="Updated",
            user_type=USER_TYPES.CHANNEL,
            is_active=False,
            source=SOURCE_TYPES.LIVE
        )

        assert user.name == "Updated"
        assert user.user_type == USER_TYPES.CHANNEL.value
        assert user.is_active is False
        assert user.source == SOURCE_TYPES.LIVE.value

    def test_update_with_series(self):
        """测试从 Series 更新"""
        user = MUser(name="Original")

        df = pd.Series({
            "name": "Updated from Series",
            "user_type": USER_TYPES.ORGANIZATION.value,
            "is_active": False,
            "source": SOURCE_TYPES.SIM.value
        })

        user.update(df)

        assert user.name == "Updated from Series"
        assert user.user_type == USER_TYPES.ORGANIZATION.value
        assert user.is_active is False
        assert user.source == SOURCE_TYPES.SIM.value

    def test_update_with_series_partial(self):
        """测试从 Series 部分更新"""
        user = MUser(
            name="Original",
            user_type=USER_TYPES.PERSON,
            is_active=True
        )

        # 只更新部分字段
        df = pd.Series({
            "name": "Updated Name",
            "user_type": USER_TYPES.CHANNEL.value
        })

        user.update(df)

        assert user.name == "Updated Name"
        assert user.user_type == USER_TYPES.CHANNEL.value
        # is_active 应保持不变
        assert user.is_active is True

    def test_update_with_series_nan_values(self):
        """测试 Series 中 NaN 值的处理"""
        user = MUser(
            name="Original",
            user_type=USER_TYPES.PERSON,
            is_active=True
        )

        # Series 中包含 NaN
        df = pd.Series({
            "name": "Updated",
            "user_type": None,  # NaN
            "is_active": None   # NaN
        })

        user.update(df)

        assert user.name == "Updated"
        # NaN 值不应更新原值
        assert user.user_type == USER_TYPES.PERSON.value
        assert user.is_active is True

    def test_update_changes_update_at(self):
        """测试 update() 会更新 update_at 字段"""
        user = MUser(name="Original")
        original_time = user.update_at

        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.01)

        user.update("Updated")

        assert user.update_at > original_time


@pytest.mark.unit
class TestMUserMethods:
    """MUser 其他方法测试"""

    def test_get_user_type_enum(self):
        """测试 get_user_type_enum() 方法"""
        user = MUser(name="Test", user_type=USER_TYPES.CHANNEL)

        enum_result = user.get_user_type_enum()

        assert isinstance(enum_result, USER_TYPES)
        assert enum_result == USER_TYPES.CHANNEL

    def test_repr(self):
        """测试 __repr__() 方法"""
        user = MUser(name="Test User", user_type=USER_TYPES.PERSON, is_active=True)

        repr_str = repr(user)

        assert "MUser" in repr_str
        assert "uuid=" in repr_str
        assert "name=Test User" in repr_str
        assert "type=PERSON" in repr_str
        assert "Active" in repr_str

    def test_repr_inactive(self):
        """测试非激活用户的 __repr__()"""
        user = MUser(name="Inactive", user_type=USER_TYPES.CHANNEL, is_active=False)

        repr_str = repr(user)

        assert "Inactive" in repr_str

    def test_soft_delete(self):
        """测试软删除功能（继承自 MMysqlBase）"""
        user = MUser(name="Test")
        assert user.is_del is False

        user.delete()
        assert user.is_del is True

        user.cancel_delete()
        assert user.is_del is False

    def test_set_source(self):
        """测试 set_source 方法（继承自 MMysqlBase）"""
        user = MUser(name="Test")

        # 使用枚举设置
        user.set_source(SOURCE_TYPES.LIVE)
        assert user.source == SOURCE_TYPES.LIVE.value

        # 使用整数设置
        user.set_source(SOURCE_TYPES.BACKTEST.value)
        assert user.source == SOURCE_TYPES.BACKTEST.value
