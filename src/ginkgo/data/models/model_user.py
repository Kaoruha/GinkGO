# Upstream: UserService (用户管理业务逻辑)、UserCRUD (用户数据CRUD操作)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、ModelConversion (提供实体转换能力)、USER_TYPES (用户类型枚举)
# Role: MUser用户模型继承MMysqlBase定义用户核心字段(username/display_name/user_type/is_active)支持用户管理功能


import pandas as pd
import datetime

from typing import Optional, List
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, USER_TYPES
from ginkgo.libs import datetime_normalize


class MUser(MMysqlBase, ModelConversion):
    """
    用户模型 - 支持个人、渠道、组织用户管理

    Attributes:
        uuid: 用户唯一标识
        username: 登录用户名（唯一，用于登录认证）
        display_name: 显示名称（可重复，用于展示）
        email: 邮箱地址
        description: 用户描述
        user_type: 用户类型 (PERSON/CHANNEL/ORGANIZATION)
        is_active: 是否激活
        credential: 登录凭证（一对一关系）
        contacts: 用户联系方式列表（一对多关系）
        group_mappings: 用户组映射列表（一对多关系）
    """
    __abstract__ = False
    __tablename__ = "users"

    # 用户核心字段
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True, comment="登录用户名（唯一）")
    display_name: Mapped[Optional[str]] = mapped_column(String(128), default="", comment="显示名称")
    email: Mapped[Optional[str]] = mapped_column(String(128), default="", comment="邮箱地址")
    description: Mapped[Optional[str]] = mapped_column(String(512), default="")
    user_type: Mapped[int] = mapped_column(TINYINT, default=USER_TYPES.PERSON.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关系映射
    credential = relationship("MUserCredential", back_populates="user", uselist=False, cascade="all, delete-orphan")
    contacts = relationship("MUserContact", back_populates="user", cascade="all, delete-orphan")
    group_mappings = relationship("MUserGroupMapping", back_populates="user", cascade="all, delete-orphan")
    notification_recipients = relationship("MNotificationRecipient", back_populates="user", foreign_keys="MNotificationRecipient.user_id")

    def __init__(
        self,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        description: Optional[str] = None,
        user_type=None,
        is_active: Optional[bool] = None,
        source=None,
        **kwargs
    ):
        """
        初始化用户模型

        Args:
            username: 登录用户名（唯一）
            display_name: 显示名称
            email: 邮箱地址
            description: 用户描述
            user_type: 用户类型（枚举或整数）
            is_active: 是否激活
            source: 数据源
        """
        super().__init__(**kwargs)

        self.username = username or ""
        self.display_name = display_name or username or ""
        self.email = email or ""
        self.description = description or ""

        # 处理 user_type 枚举转换
        if user_type is not None:
            validated = USER_TYPES.validate_input(user_type)
            self.user_type = validated if validated is not None else USER_TYPES.PERSON.value
        else:
            self.user_type = USER_TYPES.PERSON.value

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
        """更新用户信息 - 支持多种参数格式"""
        # 处理仅关键字参数的情况（没有位置参数时）
        if not args and kwargs:
            username = kwargs.get('username')
            display_name = kwargs.get('display_name')
            email = kwargs.get('email')
            description = kwargs.get('description')
            user_type = kwargs.get('user_type')
            is_active = kwargs.get('is_active')
            source = kwargs.get('source')

            if username is not None:
                self.username = username

            if display_name is not None:
                self.display_name = display_name

            if email is not None:
                self.email = email

            if description is not None:
                self.description = description

            if user_type is not None:
                validated = USER_TYPES.validate_input(user_type)
                self.user_type = validated if validated is not None else self.user_type

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
            self._update_from_str(first_arg, *args[1:], **kwargs)
        elif isinstance(first_arg, pd.Series):
            self._update_from_series(first_arg, *args, **kwargs)
        else:
            raise NotImplementedError(f"Unsupported type for update: {type(first_arg)}")

    def _update_from_str(
        self,
        username: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        description: Optional[str] = None,
        user_type=None,
        is_active: Optional[bool] = None,
        source=None,
        *args,
        **kwargs
    ) -> None:
        """
        从字符串参数更新用户信息

        Args:
            username: 登录用户名
            display_name: 显示名称
            email: 邮箱地址
            description: 用户描述
            user_type: 用户类型（枚举或整数）
            is_active: 是否激活
            source: 数据源
        """
        self.username = username

        if display_name is not None:
            self.display_name = display_name

        if email is not None:
            self.email = email

        if description is not None:
            self.description = description

        if user_type is not None:
            validated = USER_TYPES.validate_input(user_type)
            self.user_type = validated if validated is not None else self.user_type

        if is_active is not None:
            self.is_active = is_active

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or self.source

        self.update_at = datetime.datetime.now()

    def _update_from_series(self, df: pd.Series, *args, **kwargs) -> None:
        """
        从 pandas Series 更新用户信息

        Args:
            df: 包含用户信息的 Series
        """
        if 'username' in df.index and pd.notna(df['username']):
            self.username = str(df['username'])

        if 'display_name' in df.index and pd.notna(df['display_name']):
            self.display_name = str(df['display_name'])
        elif 'name' in df.index and pd.notna(df['name']):
            # 兼容旧的 name 字段
            self.display_name = str(df['name'])

        if 'email' in df.index and pd.notna(df['email']):
            self.email = str(df['email'])

        if 'description' in df.index and pd.notna(df['description']):
            self.description = str(df['description'])

        if 'user_type' in df.index and pd.notna(df['user_type']):
            validated = USER_TYPES.validate_input(df['user_type'])
            if validated is not None:
                self.user_type = validated

        if 'is_active' in df.index and pd.notna(df['is_active']):
            self.is_active = bool(df['is_active'])

        if 'source' in df.index and pd.notna(df['source']):
            validated = SOURCE_TYPES.validate_input(df['source'])
            if validated is not None:
                self.source = validated

        self.update_at = datetime.datetime.now()

    def get_user_type_enum(self) -> USER_TYPES:
        """获取用户类型枚举"""
        return USER_TYPES.from_int(self.user_type)

    def __repr__(self) -> str:
        """字符串表示"""
        user_type_str = self.get_user_type_enum().name if self.get_user_type_enum() else "UNKNOWN"
        status = "Active" if self.is_active else "Inactive"
        return f"<MUser(uuid={self.uuid[:8]}..., username={self.username}, display_name={self.display_name}, type={user_type_str}, {status})>"
