# Upstream: NotificationService (通知服务业务逻辑)
# Downstream: WebhookChannel, EmailChannel, KafkaChannel (具体渠道实现)
# Role: INotificationChannel通知渠道接口定义通知渠道的标准接口确保所有渠道实现一致性支持通知系统功能


"""
Notification Channel Base Interface

定义通知渠道的标准接口，所有渠道实现必须继承此接口。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ChannelResult:
    """
    渠道发送结果

    Attributes:
        success: 是否成功
        message_id: 渠道返回的消息 ID（可选）
        error: 错误信息（失败时）
        timestamp: 发送时间戳
    """
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "message_id": self.message_id,
            "error": self.error,
            "timestamp": self.timestamp
        }


class INotificationChannel(ABC):
    """
    通知渠道接口

    定义所有通知渠道必须实现的标准方法。
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """
        获取渠道名称

        Returns:
            str: 渠道名称（如 "discord", "email", "kafka"）
        """
        pass

    @abstractmethod
    def send(
        self,
        content: str,
        title: Optional[str] = None,
        **kwargs
    ) -> ChannelResult:
        """
        发送通知

        Args:
            content: 通知内容
            title: 通知标题（可选）
            **kwargs: 渠道特定的额外参数

        Returns:
            ChannelResult: 发送结果
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证渠道配置是否有效

        Returns:
            bool: 配置是否有效
        """
        pass

    def is_available(self) -> bool:
        """
        检查渠道是否可用

        默认实现基于配置验证，子类可覆盖以添加额外的健康检查。

        Returns:
            bool: 渠道是否可用
        """
        return self.validate_config()

    @abstractmethod
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要（用于调试和日志）

        Returns:
            Dict: 配置摘要（不包含敏感信息）
        """
        pass
