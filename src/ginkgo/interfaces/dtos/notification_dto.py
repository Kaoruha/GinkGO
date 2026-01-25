# Upstream: GinkgoNotifier (通知发送)
# Downstream: NotificationWorker (通知消费和处理)
# Role: 通知消息数据传输对象

from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field


class NotificationDTO(BaseModel):
    """
    通知消息数据传输对象

    GinkgoNotifier通过Kafka发送通知消息到NotificationWorker，
    用于各种通知类型的处理（beep、beep_coin等）。
    """

    # 通知类型
    type: str = Field(..., description="通知类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="通知时间戳")

    # 通知参数
    params: Dict[str, Any] = Field(default_factory=dict, description="通知参数")

    # 来源标识
    source: Optional[str] = Field(default="notifier", description="通知来源")

    # 预定义通知类型
    class Types:
        """预定义通知类型常量"""
        BEEP = "beep"
        BEEP_COIN = "beep_coin"

    def is_beep(self) -> bool:
        """是否为beep通知"""
        return self.type == self.Types.BEEP

    def is_beep_coin(self) -> bool:
        """是否为beep_coin通知"""
        return self.type == self.Types.BEEP_COIN
