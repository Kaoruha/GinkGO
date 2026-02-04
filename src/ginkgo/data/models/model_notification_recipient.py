# Upstream: NotificationRecipientService (通知接收人业务逻辑)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、RECIPIENT_TYPES (接收人类型枚举)
# Role: MNotificationRecipient全局通知接收人模型引用用户或用户组定义系统级通知接收人核心字段(recipient_type/user_id/user_group_id)支持系统级通知接收人管理功能


"""
Notification Recipient Model

全局通知接收人模型，引用用户或用户组作为系统级通知接收人。
用于存储系统级的通知接收人配置（如风控警报发送给管理员组）。
存储在 MySQL 中，通过引用用户/用户组实现。
"""

import pandas as pd
import datetime

from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES, RECIPIENT_TYPES
from ginkgo.libs import datetime_normalize

# 避免循环导入
if TYPE_CHECKING:
    from ginkgo.data.models.model_user import MUser
    from ginkgo.data.models.model_user_group import MUserGroup


class MNotificationRecipient(MMysqlBase, ModelConversion):
    """
    全局通知接收人模型

    通过引用用户或用户组作为系统级通知接收人。
    当发送通知时，根据类型获取对应的联系方式：
    - USER: 使用该用户的主联系方式
    - USER_GROUP: 使用组内所有用户的主联系方式

    Attributes:
        uuid: 接收人唯一标识
        recipient_type: 接收人类型（USER/USER_GROUP）
        user_id: 关联的用户UUID（当类型为USER时使用）
        user_group_id: 关联的用户组UUID（当类型为USER_GROUP时使用）
        name: 显示名称
        is_default: 是否为默认接收人
        description: 描述信息
    """
    __abstract__ = False
    __tablename__ = "notification_recipients"

    # 接收人类型
    recipient_type: Mapped[int] = mapped_column(
        TINYINT,
        default=RECIPIENT_TYPES.USER.value,
        nullable=False,
        index=True
    )

    # 关联字段（根据类型二选一）
    user_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    user_group_id: Mapped[Optional[str]] = mapped_column(
        String(32),
        ForeignKey("user_groups.uuid", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # 显示名称
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # 是否默认接收人
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # 描述信息
    description: Mapped[Optional[str]] = mapped_column(String(512), default="")

    # 关系映射
    user = relationship("MUser", back_populates="notification_recipients", foreign_keys=[user_id])
    user_group = relationship("MUserGroup", back_populates="notification_recipients", foreign_keys=[user_group_id])

    def __init__(
        self,
        recipient_type=None,
        user_id: Optional[str] = None,
        user_group_id: Optional[str] = None,
        name: Optional[str] = None,
        is_default: Optional[bool] = None,
        description: Optional[str] = None,
        source=None,
        **kwargs
    ):
        """
        初始化全局通知接收人模型

        Args:
            recipient_type: 接收人类型（枚举或整数）
            user_id: 关联的用户UUID
            user_group_id: 关联的用户组UUID
            name: 显示名称
            is_default: 是否为默认接收人
            description: 描述信息
            source: 数据来源
        """
        super().__init__(**kwargs)

        if name is None:
            raise ValueError("name is required")

        self.name = name
        self.description = description or ""

        # 处理 recipient_type 枚举转换
        if recipient_type is not None:
            if isinstance(recipient_type, RECIPIENT_TYPES):
                self.recipient_type = recipient_type.value
            else:
                validated = RECIPIENT_TYPES.from_int(recipient_type)
                self.recipient_type = validated.value if validated else RECIPIENT_TYPES.USER.value
        else:
            # 自动推断类型
            if user_id:
                self.recipient_type = RECIPIENT_TYPES.USER.value
            elif user_group_id:
                self.recipient_type = RECIPIENT_TYPES.USER_GROUP.value
            else:
                raise ValueError("Either user_id or user_group_id must be provided")

        # 根据类型设置关联字段
        if self.recipient_type == RECIPIENT_TYPES.USER.value:
            if user_id is None:
                raise ValueError("user_id is required for USER type")
            self.user_id = user_id
            self.user_group_id = None
        elif self.recipient_type == RECIPIENT_TYPES.USER_GROUP.value:
            if user_group_id is None:
                raise ValueError("user_group_id is required for USER_GROUP type")
            self.user_group_id = user_group_id
            self.user_id = None
        else:
            raise ValueError(f"Invalid recipient_type: {recipient_type}")

        # 处理 is_default
        self.is_default = is_default if is_default is not None else False

    def get_recipient_type_enum(self) -> Optional[RECIPIENT_TYPES]:
        """获取接收人类型枚举"""
        return RECIPIENT_TYPES.from_int(self.recipient_type)

    def to_df(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        return pd.DataFrame([{
            "uuid": self.uuid,
            "recipient_type": self.recipient_type,
            "user_id": self.user_id,
            "user_group_id": self.user_group_id,
            "name": self.name,
            "is_default": self.is_default,
            "description": self.description,
            "meta": self.meta,
            "desc": self.desc,
            "create_at": self.create_at,
            "update_at": self.update_at,
            "is_del": self.is_del,
            "source": self.source
        }])

    def __repr__(self) -> str:
        """字符串表示"""
        type_str = self.get_recipient_type_enum().name if self.get_recipient_type_enum() else "UNKNOWN"
        target = self.user_id[:8] if self.user_id else self.user_group_id[:8]
        default = ", Default" if self.is_default else ""
        return (
            f"<MNotificationRecipient(uuid={self.uuid[:8]}..., "
            f"name={self.name}, "
            f"type={type_str}, "
            f"target={target}...{default})>"
        )
