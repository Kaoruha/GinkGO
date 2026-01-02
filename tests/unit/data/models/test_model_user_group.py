# Upstream: None
# Downstream: None
# Role: MUserGroup和MUserGroupMapping模型单元测试验证用户组和映射关系功能


"""
MUserGroup and MUserGroupMapping Model Unit Tests

测试覆盖:
- MUserGroup 初始化和字段
- MUserGroupMapping 初始化和外键约束
- 唯一约束（user_uuid + group_uuid）
- 关系映射
"""

import pytest
import pandas as pd

from ginkgo.data.models.model_user_group import MUserGroup
from ginkgo.data.models.model_user_group_mapping import MUserGroupMapping
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.unit
class TestMUserGroupBasics:
    """MUserGroup 基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        group = MUserGroup(name="test_group")

        assert group.uuid is not None
        assert group.name == "test_group"
        assert group.description == ""
        assert group.source == SOURCE_TYPES.OTHER.value
        assert group.is_del is False

    def test_constructor_requires_group_id(self):
        """测试 name 是必需的"""
        with pytest.raises(ValueError, match="name is required"):
            MUserGroup()

    def test_constructor_with_name(self):
        """测试带名称的构造"""
        group = MUserGroup(name="Administrators")

        assert group.name == "Administrators"

    def test_constructor_with_description(self):
        """测试带描述的构造"""
        group = MUserGroup(
            name="Traders",
            description="Active trading users"
        )

        assert group.name == "Traders"
        assert group.description == "Active trading users"

    def test_constructor_with_source(self):
        """测试带数据源的构造"""
        group = MUserGroup(
            name="test_group",
            source=SOURCE_TYPES.SIM
        )

        assert group.source == SOURCE_TYPES.SIM.value

    def test_update_with_str(self):
        """测试从字符串更新"""
        group = MUserGroup(name="Original")

        group.update("Updated Name", "Updated description")

        assert group.name == "Updated Name"
        assert group.description == "Updated description"

    def test_update_with_series(self):
        """测试从 Series 更新"""
        group = MUserGroup(name="Original")

        df = pd.Series({
            "name": "Updated",
            "description": "Updated description"
        })

        group.update(df)

        assert group.name == "Updated"
        assert group.description == "Updated description"

    def test_repr(self):
        """测试 __repr__()"""
        group = MUserGroup(name="Test Group")

        repr_str = repr(group)

        assert "MUserGroup" in repr_str
        assert "name=Test Group" in repr_str


@pytest.mark.unit
class TestMUserGroupMappingBasics:
    """MUserGroupMapping 基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        user_uuid = "user_uuid_1234567890ab"
        group_uuid = "group_uuid_1234567890ab"

        mapping = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )

        assert mapping.uuid is not None
        assert mapping.user_uuid == user_uuid
        assert mapping.group_uuid == group_uuid
        assert mapping.source == SOURCE_TYPES.OTHER.value
        assert mapping.is_del is False

    def test_constructor_requires_user_uuid(self):
        """测试 user_uuid 是必需的"""
        group_uuid = "group_uuid_1234567890ab"

        with pytest.raises(ValueError, match="user_uuid is required"):
            MUserGroupMapping(group_uuid=group_uuid)

    def test_constructor_requires_group_uuid(self):
        """测试 group_uuid 是必需的"""
        user_uuid = "user_uuid_1234567890ab"

        with pytest.raises(ValueError, match="group_uuid is required"):
            MUserGroupMapping(user_uuid=user_uuid)

    def test_constructor_with_source(self):
        """测试带数据源的构造"""
        user_uuid = "user_uuid_1234567890ab"
        group_uuid = "group_uuid_1234567890ab"

        mapping = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid,
            source=SOURCE_TYPES.LIVE
        )

        assert mapping.source == SOURCE_TYPES.LIVE.value

    def test_repr(self):
        """测试 __repr__()"""
        user_uuid = "user_uuid_1234567890ab"
        group_uuid = "group_uuid_1234567890ab"

        mapping = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )

        repr_str = repr(mapping)

        assert "MUserGroupMapping" in repr_str
        assert "user=" in repr_str
        assert "group=" in repr_str


@pytest.mark.unit
class TestMUserGroupMappingConstraints:
    """MUserGroupMapping 约束测试"""

    def test_unique_constraint_design(self):
        """测试唯一约束设计（user_uuid + group_uuid）"""
        # 模型定义了 UniqueConstraint('user_uuid', 'group_uuid')
        # 这确保同一个用户在同一个组中只能有一条记录

        user_uuid = "user_uuid_1234567890ab"
        group_uuid = "group_uuid_1234567890ab"

        mapping1 = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )

        # 同样的用户和组可以创建另一个对象
        # 但在实际数据库中会因唯一约束而失败
        mapping2 = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )

        assert mapping1.user_uuid == mapping2.user_uuid
        assert mapping1.group_uuid == mapping2.group_uuid

    def test_different_users_same_group(self):
        """测试不同用户可以加入同一个组"""
        user1_uuid = "user1_uuid_1234567890ab"
        user2_uuid = "user2_uuid_1234567890ab"
        group_uuid = "group_uuid_1234567890ab"

        mapping1 = MUserGroupMapping(
            user_uuid=user1_uuid,
            group_uuid=group_uuid
        )

        mapping2 = MUserGroupMapping(
            user_uuid=user2_uuid,
            group_uuid=group_uuid
        )

        # 不同用户加入同一组是允许的
        assert mapping1.group_uuid == mapping2.group_uuid
        assert mapping1.user_uuid != mapping2.user_uuid

    def test_same_user_different_groups(self):
        """测试同一用户可以加入多个组"""
        user_uuid = "user_uuid_1234567890ab"
        group1_uuid = "group1_uuid_1234567890ab"
        group2_uuid = "group2_uuid_1234567890ab"

        mapping1 = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group1_uuid
        )

        mapping2 = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group2_uuid
        )

        # 同一用户加入不同组是允许的
        assert mapping1.user_uuid == mapping2.user_uuid
        assert mapping1.group_uuid != mapping2.group_uuid


@pytest.mark.unit
class TestMUserGroupSoftDelete:
    """MUserGroup 软删除测试"""

    def test_soft_delete(self):
        """测试软删除功能"""
        group = MUserGroup(name="test_group")
        assert group.is_del is False

        group.delete()
        assert group.is_del is True

        group.cancel_delete()
        assert group.is_del is False


@pytest.mark.unit
class TestMUserGroupMappingSoftDelete:
    """MUserGroupMapping 软删除测试"""

    def test_soft_delete(self):
        """测试软删除功能"""
        user_uuid = "user_uuid_1234567890ab"
        group_uuid = "group_uuid_1234567890ab"

        mapping = MUserGroupMapping(
            user_uuid=user_uuid,
            group_uuid=group_uuid
        )

        assert mapping.is_del is False

        mapping.delete()
        assert mapping.is_del is True

        mapping.cancel_delete()
        assert mapping.is_del is False
