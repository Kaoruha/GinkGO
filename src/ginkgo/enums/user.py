"""用户与通知域枚举：用户/联系/联系方式状态/通知状态/收件人/模板（US2 用户管理系统）。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


class USER_TYPES(EnumBase):
    """用户类型枚举 - 支持用户管理系统"""

    VOID = -1
    OTHER = 0
    PERSON = 1           # 个人用户
    CHANNEL = 2          # 渠道用户（如第三方平台）
    ORGANIZATION = 3     # 组织用户


class CONTACT_TYPES(EnumBase):
    """联系方式类型枚举 - 支持多种通知渠道"""

    VOID = -1
    OTHER = 0
    EMAIL = 1            # 邮箱联系方式
    WEBHOOK = 2          # Webhook联系方式（如钉钉、企业微信等）
    DISCORD = 3          # Discord联系方式


class CONTACT_METHOD_STATUS_TYPES(EnumBase):
    """联系方式状态枚举 - 用于管理用户联系方式的激活状态"""

    VOID = -1
    INACTIVE = 0         # 未激活
    ACTIVE = 1           # 已激活
    DISABLED = 2         # 已禁用
    EXPIRED = 3          # 已过期


class NOTIFICATION_STATUS_TYPES(EnumBase):
    """通知状态枚举 - 用于跟踪通知发送状态"""

    PENDING = 0          # 待发送
    SENT = 1             # 已发送
    FAILED = 2           # 发送失败
    RETRYING = 3         # 重试中


class RECIPIENT_TYPES(EnumBase):
    """通知接收人类型枚举 - 用于区分接收人来源"""

    VOID = -1
    USER = 1             # 单个用户
    USER_GROUP = 2       # 用户组


class TEMPLATE_TYPES(EnumBase):
    """通知模板类型枚举 - 支持多种格式"""

    VOID = -1
    OTHER = 0
    TEXT = 1             # 纯文本模板
    MARKDOWN = 2         # Markdown格式模板
    EMBEDDED = 3         # 嵌入式模板（Discord Embed）


__all__ = ['USER_TYPES', 'CONTACT_TYPES', 'CONTACT_METHOD_STATUS_TYPES', 'NOTIFICATION_STATUS_TYPES', 'RECIPIENT_TYPES', 'TEMPLATE_TYPES']
