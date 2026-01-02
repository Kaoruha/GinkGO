# Upstream: UserGroupService (用户组管理业务逻辑)、UserGroupMappingCRUD (用户组映射数据CRUD操作)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、ModelConversion (提供实体转换能力)
# Role: MUserGroupMapping用户组映射模型继承MMysqlBase定义用户与组的多对多关系字段(user_uuid/group_uuid)支持用户组成员管理功能


import pandas as pd
import datetime

from typing import Optional
from sqlalchemy import String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES


class MUserGroupMapping(MMysqlBase, ModelConversion):
    """
    用户组映射模型 - 用户与组的多对多关系

    支持将用户添加到多个组，或一个组包含多个用户。

    Attributes:
        uuid: 映射记录唯一标识
        user_uuid: 用户UUID（外键）
        group_uuid: 用户组UUID（外键）
    """
    __abstract__ = False
    __tablename__ = "user_group_mappings"

    # 外键字段
    user_uuid: Mapped[str] = mapped_column(String(32), ForeignKey("users.uuid"), nullable=False, index=True)
    group_uuid: Mapped[str] = mapped_column(String(32), ForeignKey("user_groups.uuid"), nullable=False, index=True)

    # 唯一约束：一个用户在一个组中只能有一条记录
    __table_args__ = (
        UniqueConstraint('user_uuid', 'group_uuid', name='uq_user_group'),
    )

    # 关系映射
    user = relationship("MUser", back_populates="group_mappings")
    group = relationship("MUserGroup", back_populates="mappings")

    def __init__(
        self,
        user_uuid: Optional[str] = None,
        group_uuid: Optional[str] = None,
        source=None,
        **kwargs
    ):
        """
        初始化用户组映射模型

        Args:
            user_uuid: 用户UUID
            group_uuid: 用户组UUID
            source: 数据源
        """
        super().__init__(**kwargs)

        if user_uuid is None:
            raise ValueError("user_uuid is required")
        if group_uuid is None:
            raise ValueError("group_uuid is required")

        self.user_uuid = user_uuid
        self.group_uuid = group_uuid

        # 处理 source
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.OTHER.value
        else:
            self.source = SOURCE_TYPES.OTHER.value

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<MUserGroupMapping(uuid={self.uuid[:8]}..., user={self.user_uuid[:8]}..., group={self.group_uuid[:8]}...)>"
