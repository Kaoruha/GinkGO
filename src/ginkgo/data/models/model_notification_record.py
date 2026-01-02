# Upstream: NotificationRecordCRUD (通知记录CRUD操作)、NotificationService (通知业务逻辑)
# Downstream: MMongoBase (继承提供MongoDB ORM能力)、NOTIFICATION_STATUS_TYPES (通知状态枚举)
# Role: MNotificationRecord通知记录模型继承MMongoBase定义通知记录核心字段(message_id/content/channels/status/channel_results/priority)支持通知记录管理功能


"""
Notification Record Model

通知发送记录模型，用于存储通知发送的历史记录和结果。
支持7天自动清理（TTL索引）。
"""

import uuid
import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator

from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.enums import SOURCE_TYPES, NOTIFICATION_STATUS_TYPES


class MNotificationRecord(MMongoBase):
    """
    通知发送记录模型

    用于存储每次通知发送的记录，包括发送状态、结果等。
    支持7天自动清理（TTL索引）。

    Attributes:
        message_id: 消息唯一标识符（业务ID）
        content: 通知内容
        content_type: 内容类型（text/markdown/embedded）
        channels: 目标渠道列表（email, discord, kafka等）
        status: 发送状态（pending/sent/failed）
        channel_results: 各渠道发送结果（JSON格式）
        priority: 优先级（0=低, 1=普通, 2=高, 3=紧急）
        user_uuid: 关联的用户UUID（可选）
        template_id: 使用的模板ID（可选）
        error_message: 错误信息（发送失败时）
        sent_at: 发送时间
        ttl_days: TTL天数（默认7天）
    """

    # 集合名称
    __collection__ = "notification_records"

    # 核心字段
    message_id: str = Field(
        ...,
        description="消息唯一标识符（业务ID）",
        min_length=1,
        max_length=64
    )

    content: str = Field(
        ...,
        description="通知内容"
    )

    content_type: str = Field(
        default="text",
        description="内容类型 (text/markdown/embedded)"
    )

    channels: List[str] = Field(
        default_factory=list,
        description="目标渠道列表 (email, discord, kafka)"
    )

    status: int = Field(
        default=NOTIFICATION_STATUS_TYPES.PENDING.value,
        description="发送状态枚举值"
    )

    channel_results: str = Field(
        default="{}",
        description="各渠道发送结果（JSON字符串）"
    )

    priority: int = Field(
        default=1,
        ge=0,
        le=3,
        description="优先级 (0=低, 1=普通, 2=高, 3=紧急)"
    )

    user_uuid: Optional[str] = Field(
        default=None,
        description="关联的用户UUID"
    )

    template_id: Optional[str] = Field(
        default=None,
        description="使用的模板ID"
    )

    error_message: Optional[str] = Field(
        default=None,
        description="错误信息（发送失败时）"
    )

    sent_at: Optional[datetime.datetime] = Field(
        default=None,
        description="实际发送时间"
    )

    ttl_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="TTL天数，超过此天数自动删除"
    )

    # Pydantic 配置
    class Config:
        """Pydantic 配置"""
        from_attributes = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "message_id": "msg_20250101_123456",
                "content": "Trade signal alert for AAPL",
                "content_type": "markdown",
                "channels": ["discord", "email"],
                "status": NOTIFICATION_STATUS_TYPES.SENT.value,
                "channel_results": '{"discord": {"success": true, "message_id": "123456"}}',
                "priority": 2,
                "user_uuid": "user123",
                "template_id": "trade_alert",
                "error_message": None,
                "sent_at": "2025-01-01T12:00:00",
                "ttl_days": 7
            }
        }

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """验证状态枚举"""
        if v is None:
            return NOTIFICATION_STATUS_TYPES.PENDING.value
        validated = NOTIFICATION_STATUS_TYPES.validate_input(v)
        if validated is None:
            raise ValueError(f"Invalid status: {v}")
        return validated

    def get_status_enum(self) -> NOTIFICATION_STATUS_TYPES:
        """获取状态枚举"""
        return NOTIFICATION_STATUS_TYPES.from_int(self.status)

    def get_channel_results_dict(self) -> Dict[str, Any]:
        """获取渠道结果字典"""
        import json
        try:
            return json.loads(self.channel_results)
        except json.JSONDecodeError:
            return {}

    def set_channel_results_dict(self, results: Dict[str, Any]) -> None:
        """设置渠道结果字典"""
        import json
        self.channel_results = json.dumps(results, ensure_ascii=False, default=str)

    def add_channel_result(self, channel: str, success: bool, message_id: Optional[str] = None, error: Optional[str] = None) -> None:
        """
        添加单个渠道的发送结果

        Args:
            channel: 渠道名称
            success: 是否成功
            message_id: 消息ID（成功时）
            error: 错误信息（失败时）
        """
        results = self.get_channel_results_dict()
        results[channel] = {
            "success": success,
            "message_id": message_id,
            "error": error,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.set_channel_results_dict(results)

    def mark_as_sent(self) -> None:
        """标记为已发送"""
        self.status = NOTIFICATION_STATUS_TYPES.SENT.value
        self.sent_at = datetime.datetime.now()

    def mark_as_failed(self, error_message: str) -> None:
        """标记为失败"""
        self.status = NOTIFICATION_STATUS_TYPES.FAILED.value
        self.error_message = error_message
        self.sent_at = datetime.datetime.now()

    def is_sent(self) -> bool:
        """是否已发送"""
        return self.status == NOTIFICATION_STATUS_TYPES.SENT.value

    def is_failed(self) -> bool:
        """是否失败"""
        return self.status == NOTIFICATION_STATUS_TYPES.FAILED.value

    def is_pending(self) -> bool:
        """是否待发送"""
        return self.status == NOTIFICATION_STATUS_TYPES.PENDING.value

    def get_ttl_index_config(self) -> Dict[str, Any]:
        """
        获取 TTL 索引配置

        MongoDB TTL 索引配置，用于自动清理过期文档。

        Returns:
            Dict: TTL 索引配置
        """
        return {
            "create_at": 1,  # 在 create_at 字段上创建 TTL 索引
            "expireAfterSeconds": self.ttl_days * 24 * 3600  # 转换为秒
        }

    def model_dump_mongo(self) -> Dict[str, Any]:
        """
        转换为 MongoDB 文档格式

        Returns:
            Dict: MongoDB 文档
        """
        return {
            "uuid": self.uuid,
            "message_id": self.message_id,
            "content": self.content,
            "content_type": self.content_type,
            "channels": self.channels,
            "status": self.status,
            "channel_results": self.channel_results,
            "priority": self.priority,
            "user_uuid": self.user_uuid,
            "template_id": self.template_id,
            "error_message": self.error_message,
            "sent_at": self.sent_at,
            "ttl_days": self.ttl_days,
            "meta": self.meta,
            "desc": self.desc,
            "create_at": self.create_at,
            "update_at": self.update_at,
            "is_del": self.is_del,
            "source": self.source
        }

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "MNotificationRecord":
        """
        从 MongoDB 文档创建模型实例

        Args:
            doc: MongoDB 文档

        Returns:
            MNotificationRecord: 模型实例
        """
        # 处理 datetime
        if "create_at" in doc and isinstance(doc["create_at"], datetime.datetime):
            pass  # 已经是 datetime
        elif "create_at" in doc and doc["create_at"]:
            doc["create_at"] = datetime.datetime.fromisoformat(doc["create_at"])

        if "update_at" in doc and isinstance(doc["update_at"], datetime.datetime):
            pass  # 已经是 datetime
        elif "update_at" in doc and doc["update_at"]:
            doc["update_at"] = datetime.datetime.fromisoformat(doc["update_at"])

        if "sent_at" in doc and doc["sent_at"]:
            if isinstance(doc["sent_at"], str):
                doc["sent_at"] = datetime.datetime.fromisoformat(doc["sent_at"])

        return cls(**doc)

    def __repr__(self) -> str:
        """字符串表示"""
        status_str = self.get_status_enum().name if self.get_status_enum() else "UNKNOWN"
        return (
            f"<MNotificationRecord(uuid={self.uuid[:8]}..., "
            f"message_id={self.message_id}, "
            f"status={status_str}, "
            f"channels={self.channels})>"
        )
