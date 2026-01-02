# Upstream: UserGroupService (用户组管理业务逻辑)、UserGroupCRUD (用户组数据CRUD操作)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、ModelConversion (提供实体转换能力)
# Role: MUserGroup用户组模型继承MMysqlBase定义用户组核心字段(name/description/is_active)支持用户组管理功能


import pandas as pd
import datetime

from typing import Optional
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import datetime_normalize


class MUserGroup(MMysqlBase, ModelConversion):
    """
    用户组模型 - 支持用户分组管理

    用于将用户分组，方便批量发送通知等操作。

    Attributes:
        uuid: 用户组唯一标识
        name: 组名称（唯一，作为业务标识）
        description: 组描述
        is_active: 是否激活
    """
    __abstract__ = False
    __tablename__ = "user_groups"

    # 用户组核心字段
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(512), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关系映射
    mappings = relationship("MUserGroupMapping", back_populates="group", cascade="all, delete-orphan")

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        source=None,
        **kwargs
    ):
        """
        初始化用户组模型

        Args:
            name: 组名称（业务唯一标识）
            description: 组描述
            is_active: 是否激活
            source: 数据源
        """
        super().__init__(**kwargs)

        if name is None:
            raise ValueError("name is required")

        self.name = name
        self.description = description or ""

        # 处理 is_active
        if is_active is not None:
            self.is_active = is_active
        else:
            self.is_active = True

        # 处理 source
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.OTHER.value
        else:
            self.source = SOURCE_TYPES.OTHER.value

    def update(self, *args, **kwargs) -> None:
        """更新用户组信息 - 支持多种参数格式"""
        # 处理仅关键字参数的情况（没有位置参数时）
        if not args and kwargs:
            name = kwargs.get('name')
            description = kwargs.get('description')
            is_active = kwargs.get('is_active')
            source = kwargs.get('source')

            if name is not None:
                self.name = name

            if description is not None:
                self.description = description

            if is_active is not None:
                self.is_active = is_active

            if source is not None:
                self.source = SOURCE_TYPES.validate_input(source) or self.source

            self.update_at = datetime.datetime.now()
        elif args:
            # 有位置参数，使用单派发方法
            self._update_dispatch(args[0], *args[1:], **kwargs)
        else:
            raise NotImplementedError("Unsupported type for update")

    def _update_dispatch(self, first_arg, *args, **kwargs) -> None:
        """内部派发方法 - 根据第一个参数类型分发"""
        if isinstance(first_arg, str):
            self._update_from_str(first_arg, *args, **kwargs)
        elif isinstance(first_arg, pd.Series):
            self._update_from_series(first_arg, *args, **kwargs)
        else:
            raise NotImplementedError(f"Unsupported type for update: {type(first_arg)}")

    def _update_from_str(
        self,
        name: str,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        source=None,
        *args,
        **kwargs
    ) -> None:
        """
        从字符串参数更新用户组

        Args:
            name: 组名称
            description: 组描述
            is_active: 是否激活
            source: 数据源
        """
        self.name = name

        if description is not None:
            self.description = description

        if is_active is not None:
            self.is_active = is_active

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or self.source

        self.update_at = datetime.datetime.now()

    def _update_from_series(self, df: pd.Series, *args, **kwargs) -> None:
        """
        从 pandas Series 更新用户组

        Args:
            df: 包含用户组信息的 Series
        """
        if 'name' in df.index and pd.notna(df['name']):
            self.name = str(df['name'])

        if 'description' in df.index and pd.notna(df['description']):
            self.description = str(df['description'])

        if 'is_active' in df.index and pd.notna(df['is_active']):
            self.is_active = bool(df['is_active'])

        if 'source' in df.index and pd.notna(df['source']):
            validated = SOURCE_TYPES.validate_input(df['source'])
            if validated is not None:
                self.source = validated

        self.update_at = datetime.datetime.now()

    def __repr__(self) -> str:
        """字符串表示"""
        status = "Active" if self.is_active else "Inactive"
        return f"<MUserGroup(uuid={self.uuid[:8]}..., name={self.name}, {status})>"
