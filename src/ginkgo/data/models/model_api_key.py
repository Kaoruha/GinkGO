# Upstream: ApiKeyService, ApiKeyCrud
# Downstream: MySQL Database (api_keys表)
# Role: API Key 数据模型 - 存储账户的 API Key 凭证信息，支持多 Key 管理


import uuid
import datetime
import hashlib
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Text, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase


class PermissionType(str):
    """权限类型枚举"""
    READ = "read"       # 查询权限
    TRADE = "trade"     # 交易权限
    ADMIN = "admin"     # 管理权限

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证权限类型是否有效"""
        return value in [cls.READ, cls.TRADE, cls.ADMIN]

    @classmethod
    def all_permissions(cls) -> list:
        """获取所有权限类型"""
        return [cls.READ, cls.TRADE, cls.ADMIN]


class Base(DeclarativeBase):
    pass


class MApiKey(MMysqlBase):
    """
    API Key 数据模型

    存储 Ginkgo API 的访问凭证，用于 MCP Server 等外部应用访问。
    每个 Key 有独立的权限控制和过期时间。
    """
    __tablename__ = "api_keys"

    # 关联用户（可选，用于限制 Key 只能操作特定用户或账号的资源）
    user_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    # Key 信息
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Key 名称，如 "Claw MCP Key"
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)  # SHA256 哈希（用于验证）
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)  # 前8位，用于识别
    key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # AES 加密的原始 key（用于查看）

    # 权限控制 (逗号分隔)
    permissions: Mapped[str] = mapped_column(String(50), nullable=False, default="read")  # "read,trade,admin"

    # 状态控制
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)  # 过期时间
    last_used_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)  # 最后使用时间

    # 备注
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 用途说明

    def check_permission(self, required_permission: str) -> bool:
        """
        检查是否有指定权限

        Args:
            required_permission: 需要的权限 (read/trade/admin)

        Returns:
            bool: 是否有权限
        """
        if not self.is_active:
            return False

        if self.expires_at and self.expires_at < datetime.datetime.now():
            return False

        return required_permission in self.get_permissions_list()

    def get_permissions_list(self) -> list:
        """获取权限列表"""
        return [p.strip() for p in self.permissions.split(',') if p.strip()]

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return self.expires_at < datetime.datetime.now()

    @staticmethod
    def hash_key(key_value: str) -> str:
        """
        生成 Key 的 SHA256 哈希

        Args:
            key_value: 原始 API Key

        Returns:
            str: SHA256 哈希值
        """
        return hashlib.sha256(key_value.encode()).hexdigest()

    @staticmethod
    def generate_prefix(key_value: str) -> str:
        """
        生成 Key 前缀（前8位）

        Args:
            key_value: 原始 API Key

        Returns:
            str: 前8位
        """
        return key_value[:8] if len(key_value) >= 8 else key_value
