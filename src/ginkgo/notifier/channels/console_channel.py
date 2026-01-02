# Upstream: NotificationService (通知服务业务逻辑)、INotificationChannel (渠道接口)
# Downstream: Console (标准输出)
# Role: ConsoleChannel控制台通知渠道实现向标准输出打印通知消息用于测试和调试支持通知系统功能


"""
Console Notification Channel

向控制台输出通知消息，用于测试和开发。
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ginkgo.notifier.channels.base_channel import INotificationChannel, ChannelResult
from ginkgo.libs import GLOG


class ConsoleChannel(INotificationChannel):
    """
    控制台通知渠道

    向标准输出打印通知消息，用于测试和开发环境。
    """

    def __init__(self):
        """初始化控制台渠道"""
        pass

    @property
    def channel_name(self) -> str:
        """获取渠道名称"""
        return "console"

    def send(
        self,
        content: str,
        title: Optional[str] = None,
        **kwargs
    ) -> ChannelResult:
        """
        发送通知到控制台

        Args:
            content: 消息内容
            title: 消息标题（可选）
            **kwargs: 其他参数

        Returns:
            ChannelResult: 发送结果（始终成功）
        """
        try:
            # 打印消息到控制台
            if title:
                print(f"[NOTIFICATION] {title}")
            print(f"[NOTIFICATION] {content}")

            # 记录日志
            GLOG.INFO(f"Console notification sent: {title or ''} - {content[:50]}")

            return ChannelResult(
                success=True,
                message_id=f"console_{datetime.utcnow().timestamp()}",
                timestamp=datetime.utcnow().timestamp()
            )

        except Exception as e:
            GLOG.ERROR(f"Console channel error: {e}")
            return ChannelResult(
                success=False,
                error=str(e),
                timestamp=datetime.utcnow().timestamp()
            )

    def validate_config(self) -> bool:
        """
        验证配置（控制台渠道始终有效）

        Returns:
            bool: 始终返回 True
        """
        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要

        Returns:
            Dict: 配置摘要
        """
        return {
            "channel": self.channel_name,
            "description": "Console output for testing",
            "valid": True
        }
