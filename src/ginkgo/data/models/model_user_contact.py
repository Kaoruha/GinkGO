# Upstream: UserService (用户管理业务逻辑)、UserCRUD (用户数据CRUD操作)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、ModelConversion (提供实体转换能力)、CONTACT_TYPES (联系方式类型枚举)
# Role: MUserContact用户联系方式模型继承MMysqlBase定义联系方式核心字段(user_id/contact_type/address/is_primary)支持用户联系方式管理功能


import pandas as pd
import datetime

from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, CONTACT_TYPES
from ginkgo.libs import datetime_normalize


class MUserContact(MMysqlBase, ModelConversion):
    """
    用户联系方式模型

    支持邮箱和Webhook两种联系方式，每个用户可以有多个联系方式，
    其中可以设置一个为主联系方式（is_primary=True）。

    Attributes:
        uuid: 联系方式唯一标识
        user_id: 关联的用户UUID（外键）
        contact_type: 联系方式类型（EMAIL/WEBHOOK）
        address: 联系地址（邮箱地址或Webhook URL）
        is_primary: 是否为主联系方式
        is_active: 是否启用（True则可用，False则禁用）
    """
    __abstract__ = False
    __tablename__ = "user_contacts"

    # 外键和核心字段
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.uuid"), nullable=False, index=True)
    contact_type: Mapped[int] = mapped_column(TINYINT, default=CONTACT_TYPES.EMAIL.value)
    address: Mapped[str] = mapped_column(String(512), default="")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关系映射
    user = relationship("MUser", back_populates="contacts")

    def __init__(
        self,
        user_id: Optional[str] = None,
        contact_type=None,
        address: Optional[str] = None,
        is_primary: Optional[bool] = None,
        is_active: Optional[bool] = None,
        source=None,
        **kwargs
    ):
        """
        初始化用户联系方式模型

        Args:
            user_id: 关联的用户UUID
            contact_type: 联系方式类型（枚举或整数）
            address: 联系地址（邮箱或Webhook）
            is_primary: 是否为主联系方式
            is_active: 是否启用
            source: 数据源
        """
        super().__init__(**kwargs)

        if user_id is None:
            raise ValueError("user_id is required")

        self.user_id = user_id
        self.address = address or ""

        # 处理 contact_type 枚举转换
        if contact_type is not None:
            validated = CONTACT_TYPES.validate_input(contact_type)
            self.contact_type = validated if validated is not None else CONTACT_TYPES.EMAIL.value
        else:
            self.contact_type = CONTACT_TYPES.EMAIL.value

        # 处理 is_primary
        if is_primary is not None:
            self.is_primary = is_primary
        else:
            self.is_primary = False

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
        """更新联系方式信息 - 支持多种参数格式"""
        # 处理仅关键字参数的情况（没有位置参数时）
        if not args and kwargs:
            address = kwargs.get('address')
            contact_type = kwargs.get('contact_type')
            is_primary = kwargs.get('is_primary')
            is_active = kwargs.get('is_active')
            source = kwargs.get('source')

            if address is not None:
                self.address = address

            if contact_type is not None:
                validated = CONTACT_TYPES.validate_input(contact_type)
                self.contact_type = validated if validated is not None else self.contact_type

            if is_primary is not None:
                self.is_primary = is_primary

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
        address: str,
        contact_type=None,
        is_primary: Optional[bool] = None,
        is_active: Optional[bool] = None,
        source=None,
        *args,
        **kwargs
    ) -> None:
        """
        从字符串参数更新联系方式

        Args:
            address: 联系地址
            contact_type: 联系类型（枚举或整数）
            is_primary: 是否为主联系方式
            is_active: 是否启用
            source: 数据源
        """
        self.address = address

        if contact_type is not None:
            validated = CONTACT_TYPES.validate_input(contact_type)
            self.contact_type = validated if validated is not None else self.contact_type

        if is_primary is not None:
            self.is_primary = is_primary

        if is_active is not None:
            self.is_active = is_active

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or self.source

        self.update_at = datetime.datetime.now()

    def _update_from_series(self, df: pd.Series, *args, **kwargs) -> None:
        """
        从 pandas Series 更新联系方式

        Args:
            df: 包含联系信息的 Series
        """
        if 'address' in df.index and pd.notna(df['address']):
            self.address = str(df['address'])

        if 'contact_type' in df.index and pd.notna(df['contact_type']):
            validated = CONTACT_TYPES.validate_input(df['contact_type'])
            if validated is not None:
                self.contact_type = validated

        if 'is_primary' in df.index and pd.notna(df['is_primary']):
            self.is_primary = bool(df['is_primary'])

        if 'is_active' in df.index and pd.notna(df['is_active']):
            self.is_active = bool(df['is_active'])

        if 'source' in df.index and pd.notna(df['source']):
            validated = SOURCE_TYPES.validate_input(df['source'])
            if validated is not None:
                self.source = validated

        self.update_at = datetime.datetime.now()

    def get_contact_type_enum(self) -> CONTACT_TYPES:
        """获取联系方式类型枚举"""
        return CONTACT_TYPES.from_int(self.contact_type)

    def __repr__(self) -> str:
        """字符串表示"""
        type_str = self.get_contact_type_enum().name if self.get_contact_type_enum() else "UNKNOWN"
        status = "Active" if self.is_active else "Disabled"
        primary = "Primary" if self.is_primary else ""
        return f"<MUserContact(uuid={self.uuid[:8]}..., type={type_str}, {status}, {primary})>"
