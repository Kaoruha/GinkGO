# Upstream: UserService (用户管理业务逻辑)、UserCredentialCRUD (凭据数据CRUD操作)
# Downstream: MMysqlBase (继承提供MySQL ORM能力)、ModelConversion (提供实体转换能力)
# Role: MUserCredential用户凭据模型继承MMysqlBase定义凭据核心字段(user_id/password_hash/is_active/is_admin)支持用户认证功能


import datetime

from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ginkgo.data.models.model_mysqlbase import MMysqlBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.enums import SOURCE_TYPES


class MUserCredential(MMysqlBase, ModelConversion):
    """
    用户凭据模型

    存储用户登录凭证（密码哈希等），与 MUser 一对一关系。

    Attributes:
        uuid: 凭据唯一标识
        user_id: 关联的用户UUID（外键）
        password_hash: 密码哈希值
        is_active: 凭据是否启用
        is_admin: 是否管理员
    """
    __abstract__ = False
    __tablename__ = "user_credentials"

    # 外键和核心字段
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.uuid"), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)

    # 关系映射
    user = relationship("MUser", back_populates="credential")

    def __init__(
        self,
        user_id: Optional[str] = None,
        password_hash: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        source=None,
        **kwargs
    ):
        super().__init__(**kwargs)

        if user_id is None:
            raise ValueError("user_id is required")

        self.user_id = user_id
        self.password_hash = password_hash or ""
        self.is_active = is_active if is_active is not None else True
        self.is_admin = is_admin if is_admin is not None else False

        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or SOURCE_TYPES.OTHER.value
        else:
            self.source = SOURCE_TYPES.OTHER.value

    def __repr__(self) -> str:
        status = "Active" if self.is_active else "Disabled"
        role = "Admin" if self.is_admin else "User"
        return f"<MUserCredential(uuid={self.uuid[:8]}..., user_id={self.user_id[:8]}..., {status}, {role})>"
