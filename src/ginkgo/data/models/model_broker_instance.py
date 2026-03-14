# Upstream: BrokerManager, LiveEngine (Broker实例管理)
# Downstream: MySQL Database (broker_instances表)
# Role: Broker实例数据模型 - 跟踪每个Portfolio的Broker运行状态

import uuid
import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Text, Integer, Float as SQLFloat
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase


class BrokerStateType(str):
    """Broker状态机枚举"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        valid_states = {
            "uninitialized": cls.UNINITIALIZED,
            "initializing": cls.INITIALIZING,
            "running": cls.RUNNING,
            "paused": cls.PAUSED,
            "stopped": cls.STOPPED,
            "error": cls.ERROR,
            "recovering": cls.RECOVERING,
        }
        if value in valid_states:
            return valid_states[value]
        else:
            raise ValueError(f"Unknown broker state: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证Broker状态是否有效"""
        return value in [
            cls.UNINITIALIZED,
            cls.INITIALIZING,
            cls.RUNNING,
            cls.PAUSED,
            cls.STOPPED,
            cls.ERROR,
            cls.RECOVERING,
        ]

    @classmethod
    def is_terminal(cls, state: str) -> bool:
        """检查状态是否为终止状态"""
        return state in [cls.STOPPED, cls.ERROR]

    @classmethod
    def is_active(cls, state: str) -> bool:
        """检查状态是否为活跃状态（可接收订单）"""
        return state in [cls.RUNNING]

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        """检查状态转换是否合法"""
        valid_transitions = {
            cls.UNINITIALIZED: [cls.INITIALIZING, cls.STOPPED],
            cls.INITIALIZING: [cls.RUNNING, cls.ERROR, cls.STOPPED],
            cls.RUNNING: [cls.PAUSED, cls.STOPPED, cls.ERROR, cls.RECOVERING],
            cls.PAUSED: [cls.RUNNING, cls.STOPPED, cls.ERROR],
            cls.STOPPED: [cls.INITIALIZING, cls.RECOVERING],
            cls.ERROR: [cls.RECOVERING, cls.STOPPED],
            cls.RECOVERING: [cls.RUNNING, cls.ERROR, cls.STOPPED],
        }
        return to_state in valid_transitions.get(from_state, [])


class Base(DeclarativeBase):
    pass


class MBrokerInstance(MMysqlBase):
    """
    Broker实例数据模型

    跟踪每个Portfolio的Broker实例状态和统计信息。
    一个Portfolio对应一个Broker实例，Broker负责与交易所API通信。

    Attributes:
        uuid: Broker实例唯一标识
        portfolio_id: 关联的Portfolio ID
        live_account_id: 关联的实盘账号ID
        state: Broker状态 (uninitialized/initializing/running/paused/stopped/error/recovering)
        process_id: Broker进程ID (如果是独立进程)
        heartbeat_at: 最后心跳时间
        error_message: 错误消息
        error_count: 累计错误次数
        total_submitted: 累计提交订单数
        total_filled: 累计成交订单数
        total_cancelled: 累计撤销订单数
        total_rejected: 累计拒绝订单数
        last_order_at: 最后订单时间
        is_del: 软删除标记
        create_at: 创建时间
        update_at: 更新时间
    """
    __tablename__ = "broker_instances"

    # 基础ID字段
    uuid: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: str(uuid.uuid4().hex))

    # 关联关系
    portfolio_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, comment="关联的Portfolio ID")
    live_account_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="关联的实盘账号ID")

    # 状态字段
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="uninitialized", comment="Broker状态")
    process_id: Mapped[Optional[int]] = mapped_column(Integer, comment="Broker进程ID")
    heartbeat_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), comment="最后心跳时间")

    # 错误处理
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="错误消息")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="累计错误次数")

    # 订单统计
    total_submitted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="累计提交订单数")
    total_filled: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="累计成交订单数")
    total_cancelled: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="累计撤销订单数")
    total_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="累计拒绝订单数")
    last_order_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), comment="最后订单时间")

    def __init__(self, **kwargs):
        """初始化MBrokerInstance实例"""
        super().__init__(**kwargs)
        # 处理状态枚举转换
        if 'state' in kwargs:
            self.state = BrokerStateType.from_str(kwargs['state'])

    def set_state(self, state: str) -> None:
        """设置Broker状态（带状态转换验证）"""
        new_state = BrokerStateType.from_str(state)
        if not BrokerStateType.can_transition(self.state, new_state):
            raise ValueError(f"Invalid state transition: {self.state} -> {new_state}")
        self.state = new_state

    def get_state(self) -> str:
        """获取当前Broker状态"""
        return self.state

    def is_active(self) -> bool:
        """检查Broker是否处于活跃状态（可接收订单）"""
        return BrokerStateType.is_active(self.state)

    def is_terminal(self) -> bool:
        """检查Broker是否处于终止状态"""
        return BrokerStateType.is_terminal(self.state)

    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.heartbeat_at = datetime.datetime.now(datetime.timezone.utc)

    def increment_error(self, error_message: str) -> None:
        """增加错误计数"""
        self.error_count += 1
        self.error_message = error_message

    def record_order_submitted(self) -> None:
        """记录订单提交"""
        self.total_submitted += 1
        self.last_order_at = datetime.datetime.now(datetime.timezone.utc)

    def record_order_filled(self) -> None:
        """记录订单成交"""
        self.total_filled += 1

    def record_order_cancelled(self) -> None:
        """记录订单撤销"""
        self.total_cancelled += 1

    def record_order_rejected(self) -> None:
        """记录订单拒绝"""
        self.total_rejected += 1

    @property
    def fill_rate(self) -> float:
        """计算成交率（成交数/提交数）"""
        if self.total_submitted == 0:
            return 0.0
        return round(self.total_filled / self.total_submitted, 4)

    @property
    def is_heartbeat_timeout(self, timeout_seconds: int = 30) -> bool:
        """检查心跳是否超时"""
        if self.heartbeat_at is None:
            return True
        elapsed = (datetime.datetime.now(datetime.timezone.utc) - self.heartbeat_at).total_seconds()
        return elapsed > timeout_seconds

    def __repr__(self) -> str:
        return (
            f"<MBrokerInstance(uuid={self.uuid}, "
            f"portfolio_id={self.portfolio_id}, "
            f"state={self.state}, "
            f"total_submitted={self.total_submitted}, "
            f"total_filled={self.total_filled})>"
        )
