# Upstream: LiveAccountService, BrokerManager (实盘账号管理)
# Downstream: MySQL Database (live_accounts表)
# Role: 实盘账号数据模型 - 存储加密的API凭证和账号配置信息


import uuid
import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Text, Enum as SQLEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase


class ExchangeType(str):
    """交易所类型枚举"""
    OKX = "okx"
    BINANCE = "binance"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "okx":
            return cls.OKX
        elif value == "binance":
            return cls.BINANCE
        else:
            raise ValueError(f"Unknown exchange type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证交易所类型是否有效"""
        return value in [cls.OKX, cls.BINANCE]


class EnvironmentType(str):
    """环境类型枚举"""
    PRODUCTION = "production"
    TESTNET = "testnet"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "production":
            return cls.PRODUCTION
        elif value == "testnet":
            return cls.TESTNET
        else:
            raise ValueError(f"Unknown environment type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证环境类型是否有效"""
        return value in [cls.PRODUCTION, cls.TESTNET]


class AccountStatusType(str):
    """账号状态类型枚举"""
    ENABLED = "enabled"
    DISABLED = "disabled"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "enabled":
            return cls.ENABLED
        elif value == "disabled":
            return cls.DISABLED
        elif value == "connecting":
            return cls.CONNECTING
        elif value == "disconnected":
            return cls.DISCONNECTED
        elif value == "error":
            return cls.ERROR
        else:
            raise ValueError(f"Unknown account status type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证账号状态是否有效"""
        return value in [cls.ENABLED, cls.DISABLED, cls.CONNECTING, cls.DISCONNECTED, cls.ERROR]


class Base(DeclarativeBase):
    pass


class MLiveAccount(MMysqlBase):
    """
    实盘账号数据模型

    存储交易所API凭证（加密后）和账号配置信息。
    支持OKX、Binance等交易所。

    Attributes:
        uuid: 账号唯一标识
        user_id: 所属用户ID
        exchange: 交易所类型 (okx/binance)
        environment: 环境类型 (production/testnet)
        name: 账号名称
        description: 账号描述
        api_key: 加密的API Key
        api_secret: 加密的API Secret
        passphrase: 加密的Passphrase (OKX需要)
        status: 账号状态 (enabled/disabled/connecting/disconnected/error)
        last_validated_at: 上次验证时间
        validation_status: 验证状态消息
        is_del: 软删除标记
        create_at: 创建时间
        update_at: 更新时间
    """
    __tablename__ = "live_accounts"

    # 基础ID字段 (继承自MMysqlBase)
    uuid: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: str(uuid.uuid4().hex))

    # 用户关联
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="所属用户ID")

    # 交易所配置
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, comment="交易所类型 (okx/binance)")
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default="testnet", comment="环境 (production/testnet)")

    # 账号信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="账号名称")
    description: Mapped[Optional[str]] = mapped_column(Text, comment="账号描述")

    # 加密的API凭证
    api_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="加密的API Key")
    api_secret: Mapped[str] = mapped_column(String(500), nullable=False, comment="加密的API Secret")
    passphrase: Mapped[Optional[str]] = mapped_column(String(500), comment="加密的Passphrase (OKX需要)")

    # 状态字段
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="enabled", comment="账号状态")
    last_validated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), comment="上次验证时间")
    validation_status: Mapped[Optional[str]] = mapped_column(String(100), comment="验证状态消息")

    def __init__(self, **kwargs):
        """初始化MLiveAccount实例"""
        super().__init__(**kwargs)
        # 处理枚举字段转换
        if 'exchange' in kwargs:
            self.exchange = ExchangeType.from_str(kwargs['exchange'])
        if 'environment' in kwargs:
            self.environment = EnvironmentType.from_str(kwargs['environment'])
        if 'status' in kwargs:
            self.status = AccountStatusType.from_str(kwargs['status'])

    def set_exchange(self, exchange: str) -> None:
        """设置交易所类型"""
        self.exchange = ExchangeType.from_str(exchange)

    def set_environment(self, environment: str) -> None:
        """设置环境类型"""
        self.environment = EnvironmentType.from_str(environment)

    def set_status(self, status: str) -> None:
        """设置账号状态"""
        self.status = AccountStatusType.from_str(status)

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == EnvironmentType.PRODUCTION

    def is_testnet(self) -> bool:
        """是否为测试网环境"""
        return self.environment == EnvironmentType.TESTNET

    def is_enabled(self) -> bool:
        """是否启用"""
        return self.status == AccountStatusType.ENABLED

    def is_okx(self) -> bool:
        """是否为OKX交易所"""
        return self.exchange == ExchangeType.OKX

    def is_binance(self) -> bool:
        """是否为Binance交易所"""
        return self.exchange == ExchangeType.BINANCE

    def requires_passphrase(self) -> bool:
        """是否需要Passphrase (OKX需要)"""
        return self.is_okx()

    def update_validation(self, success: bool, message: str = "") -> None:
        """
        更新验证状态

        Args:
            success: 验证是否成功
            message: 验证消息
        """
        self.last_validated_at = datetime.datetime.now()
        self.validation_status = "success" if success else f"failed: {message}"
        if success:
            self.status = AccountStatusType.ENABLED
        else:
            self.status = AccountStatusType.ERROR

    def to_dict(self) -> dict:
        """
        转换为字典（隐藏敏感信息）

        Returns:
            dict: 包含非敏感字段的信息字典
        """
        return {
            "uuid": self.uuid,
            "user_id": self.user_id,
            "exchange": self.exchange,
            "environment": self.environment,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "last_validated_at": self.last_validated_at.isoformat() if self.last_validated_at else None,
            "validation_status": self.validation_status,
            "is_del": self.is_del,
            "create_at": self.create_at.isoformat() if self.create_at else None,
            "update_at": self.update_at.isoformat() if self.update_at else None,
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<MLiveAccount(uuid={self.uuid}, name={self.name}, exchange={self.exchange}, environment={self.environment}, status={self.status})>"
